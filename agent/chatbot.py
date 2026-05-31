import os
import glob
from typing import Annotated, TypedDict, List, Dict
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, AIMessage, ToolMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.tools import tool
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langsmith import traceable

class AgentState(TypedDict):
    """
    Represents the operational state of the Customer Service Agent.
    
    Attributes:
        messages: The accumulated chat history including user messages, tool outputs, and assistant responses.
        user_prompt: The latest query input by the user.
        is_safe: Flag determined by input guardrail to filter out malicious or unrelated queries.
        emotion_signals: Extracted signals containing vibration/vibe, intent, and reasoning.
        enhanced_prompt: System instructions and preloaded context merged with emotional cues.
        response: The current candidate response text.
        audit_logs: Historical log entries of all validation audits run across loops.
        failed_checks: List of specific violations identified during the current iteration.
        iteration_count: Counter tracking the loops run inside the self-correction cycle.
    """
    messages: Annotated[List[BaseMessage], add_messages]
    user_prompt: str
    is_safe: bool
    emotion_signals: Dict[str, str]
    enhanced_prompt: str
    response: str
    audit_logs: List[str]
    failed_checks: List[str]
    iteration_count: int

class CustomerServiceAgent:
    """
    A multi-stage agentic customer support chatbot built using LangGraph.
    
    Handles incoming support requests for Nuit Fragrances with safety guardrails,
    emotional intelligence analysis, dynamic document retrieval tools, and
    audited self-correction iteration loops.
    """
    def __init__(self, docs_dir="agent/docs", prompt_path="agent/prompts/system_prompt.md", model_name="gemini-2.5-flash"):
        """
        Initializes the Customer Service Agent.
        
        Args:
            docs_dir: Directory containing knowledge files (FAQ, policies, specs).
            prompt_path: File path to the core concierge system instructions.
            model_name: The target LLM model name used for analysis and generation nodes.
        """
        self.docs_dir = docs_dir
        self.prompt_path = prompt_path
        self.model_name = model_name
        
        # Parse documents and build registry + descriptions
        self.doc_registry = {}
        self.doc_descriptions = []
        self.permanent_context = ""
        self._load_and_parse_documents()
        
        # Load modular prompt files
        self._load_all_prompts()
        
        # Initialize LangChain Google GenAI Model
        self.model = ChatGoogleGenerativeAI(model=self.model_name)
        
        # Initialize memory checkpointer
        self.memory = MemorySaver()
        self.config = {"configurable": {"thread_id": "default-thread"}}
        
        # Compile State Graph
        self.agent = self._compile_graph()

    def _parse_doc(self, filepath):
        """
        Parses metadata headers and text body from a markdown document.
        
        Args:
            filepath: Absolute path to the markdown document.
            
        Returns:
            A tuple of (metadata_dict, body_text_string).
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                frontmatter_raw = parts[1]
                body = parts[2].strip()
                metadata = {}
                for line in frontmatter_raw.splitlines():
                    if ":" in line:
                        k, v = line.split(":", 1)
                        metadata[k.strip()] = v.strip()
                return metadata, body
        return {}, content.strip()

    def _load_and_parse_documents(self):
        """
        Scans docs_dir, preloading static files into memory and registering 
        dynamic files for retrieval tools.
        """
        md_files = glob.glob(os.path.join(self.docs_dir, "*.md"))
        for filepath in md_files:
            filename = os.path.basename(filepath)
            if filename in ["brand_identity.md", "customer_service_sop.md"]:
                _, body = self._parse_doc(filepath)
                self.permanent_context += f"\n--- {filename} ---\n{body}\n"
            else:
                meta, body = self._parse_doc(filepath)
                name = meta.get("name", filename.replace(".md", ""))
                description = meta.get("description", "No description provided.")
                self.doc_registry[name.lower()] = body
                self.doc_descriptions.append(f"- '{name}': {description}")

    def _load_prompt_file(self, filename):
        """
        Loads a prompt template string from a file.
        
        Args:
            filename: Name of the prompt file in agent/prompts/
            
        Returns:
            The loaded template content as a string.
            
        Raises:
            FileNotFoundError if the requested prompt file is missing.
        """
        path = os.path.join("agent/prompts", filename)
        if not os.path.exists(path):
            raise FileNotFoundError(f"Required prompt file not found: {path}")
        with open(path, 'r', encoding='utf-8') as f:
            return f.read().strip()

    def _load_system_prompt(self):
        """
        Attempts to load the main system prompt from self.prompt_path or common defaults.
        
        Returns:
            The loaded system prompt content as a string.
            
        Raises:
            FileNotFoundError if the system prompt is missing in all common paths.
        """
        possible_paths = [
            self.prompt_path,
            "agent/prompts/system_prompt.txt",
            "agent/prompts/system_prompt.md"
        ]
        for path in possible_paths:
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    return f.read().strip()
        raise FileNotFoundError(f"Required system prompt file not found in paths: {possible_paths}")

    def _load_all_prompts(self):
        """
        Preloads all modular prompt configurations from their respective markdown files.
        """
        self.input_guardrail_prompt = self._load_prompt_file("input_guardrail.md")
        self.emotion_analysis_prompt = self._load_prompt_file("emotion_analysis.md")
        self.brand_audit_prompt = self._load_prompt_file("brand_audit.md")
        self.fact_audit_prompt = self._load_prompt_file("fact_audit.md")
        self.emotional_audit_prompt_template = self._load_prompt_file("emotional_audit.md")
        self.output_guardrail_prompt = self._load_prompt_file("output_guardrail.md")

    def _input_guardrail(self, state: AgentState) -> Dict:
        """
        Evaluates safety and relevance of the customer query.
        
        Args:
            state: The current operational state.
            
        Returns:
            State updates containing the 'is_safe' status and refusal payload if safety fails.
        """
        user_prompt = state["user_prompt"]
        res = self.model.invoke([
            SystemMessage(content=self.input_guardrail_prompt),
            HumanMessage(content=user_prompt)
        ]).content.strip().upper()
        
        if "UNSAFE" in res:
            refusal = "I want to ensure you receive completely accurate details on that matter. Let me verify our specific inventory files or connect you directly with a specialist from our care team. May I please have your phone number to look up your order profile?"
            return {
                "is_safe": False,
                "response": refusal,
                "messages": [HumanMessage(content=user_prompt), AIMessage(content=refusal)]
            }
        
        return {"is_safe": True}

    def _analyze_emotion_intent(self, state: AgentState) -> Dict:
        """
        Extracts customer sentiment patterns and intent level from conversation history.
        
        Args:
            state: The current operational state.
            
        Returns:
            State updates containing structured emotion signals.
        """
        if not state.get("is_safe", True):
            return {}
            
        user_prompt = state["user_prompt"]
        history = state.get("messages", [])
        history_text = "\n".join([f"{m.type}: {m.content}" for m in history[-5:]])
        
        prompt = f"Chat History:\n{history_text}\n\nUser Prompt: {user_prompt}"
        res = self.model.invoke([
            SystemMessage(content=self.emotion_analysis_prompt),
            HumanMessage(content=prompt)
        ]).content.strip()
        
        signals = {"vibe": "calm", "intent": "browsing", "reason": ""}
        for line in res.splitlines():
            if line.startswith("EMOTION:"):
                signals["vibe"] = line.replace("EMOTION:", "").strip().lower()
            elif line.startswith("INTENT:"):
                signals["intent"] = line.replace("INTENT:", "").strip().lower()
            elif line.startswith("REASON:"):
                signals["reason"] = line.replace("REASON:", "").strip()
                
        return {"emotion_signals": signals}

    def _enhance_prompt(self, state: AgentState) -> Dict:
        """
        Assembles contextual metadata and preloaded brand guidelines into a single instruction set.
        
        Args:
            state: The current operational state.
            
        Returns:
            State updates with the consolidated 'enhanced_prompt' string.
        """
        if not state.get("is_safe", True):
            return {}
            
        system_prompt = self._load_system_prompt()
        doc_list_str = "\n".join(self.doc_descriptions)
        
        signals = state.get("emotion_signals", {})
        emotion = signals.get("vibe", "calm")
        intent = signals.get("intent", "browsing")
        reason = signals.get("reason", "")
        
        enhanced_prompt = (
            f"{system_prompt}\n\n"
            f"=== PERMANENT CONTEXT ===\n{self.permanent_context}\n\n"
            f"=== KNOWLEDGE DOCUMENTS AVAILABLE VIA TOOL ===\n"
            f"You have access to a tool `retrieve_document_content` which can fetch details for:\n"
            f"{doc_list_str}\n\n"
            f"=== EMOTIONAL & INTENT CONTEXT ===\n"
            f"- User emotional state: {emotion} (Reason: {reason})\n"
            f"- User buying intent level: {intent}\n"
            f"Instruction: Adapt your tone and response format to match the customer's emotional state. "
            f"If the user is anxious or frustrated, address their concern directly and reassuringly."
        )
        
        return {"enhanced_prompt": enhanced_prompt}

    def _generate_response(self, state: AgentState) -> Dict:
        """
        Executes a dynamic tool-calling React loop to generate a candidate response.
        
        Args:
            state: The current operational state.
            
        Returns:
            State updates containing the generated response and tracking messages.
        """
        if not state.get("is_safe", True):
            return {}
            
        user_prompt = state["user_prompt"]
        
        @tool
        def retrieve_document_content(document_name: str) -> str:
            """Retrieves the full content of a specific knowledge document by its name.
            Available document names:
            - 'faq': FAQ, shipping fees, shipping times, return windows, exchange rules, international delivery.
            - 'icp': Customer career segments, demographic traits, and behavioral triggers.
            - 'meta_ad_strat': Ad campaigns, Shark Tank Egypt, Discovery Box bundles, active promos.
            - 'product_specs': Fragrance notes, classification, ingredients, bottle sizes, application protocols.
            - 'terms_of_conditions_and_policies': Pricing matrix, variant names, return/refund exclusions, damaged item reporting.
            """
            doc_name = document_name.strip().lower()
            return self.doc_registry.get(doc_name, f"Document '{document_name}' not found. Available documents: {list(self.doc_registry.keys())}")

        model_with_tools = self.model.bind_tools([retrieve_document_content])
        
        messages = [SystemMessage(content=state["enhanced_prompt"])]
        messages.extend(state.get("messages", [])[-5:])
        messages.append(HumanMessage(content=user_prompt))
        
        if state.get("iteration_count", 0) > 0:
            revision_feedback = (
                f"CRITICAL: The previous response failed verification audits.\n"
                f"Failed Checks:\n" + "\n".join([f"- {err}" for err in state["failed_checks"]]) + "\n\n"
                f"Please rewrite the response to resolve these violations. Do not repeat the same errors."
            )
            messages.append(SystemMessage(content=revision_feedback))
            
        new_messages = [HumanMessage(content=user_prompt)]
        
        for _ in range(5):
            response = model_with_tools.invoke(messages)
            messages.append(response)
            new_messages.append(response)
            
            if not response.tool_calls:
                return {
                    "response": response.content,
                    "messages": new_messages
                }
                
            for tool_call in response.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]
                if tool_name == "retrieve_document_content":
                    content = retrieve_document_content.invoke(tool_args)
                else:
                    content = f"Unknown tool: {tool_name}"
                
                tool_msg = ToolMessage(content=content, tool_call_id=tool_call["id"])
                messages.append(tool_msg)
                new_messages.append(tool_msg)
                
        return {
            "response": response.content,
            "messages": new_messages
        }

    def _run_audits(self, state: AgentState) -> Dict:
        """
        Runs Brand, Fact, Emotional, and Output Guardrail evaluations on candidate output.
        
        Args:
            state: The current operational state.
            
        Returns:
            State updates containing failed check lists and evaluation logs.
        """
        if not state.get("is_safe", True):
            return {}
            
        candidate = state["response"]
        failed_checks = []
        audit_logs = list(state.get("audit_logs", []))
        
        # 1. Brand Audit
        brand_res = self.model.invoke([
            SystemMessage(content=self.brand_audit_prompt),
            HumanMessage(content=candidate)
        ]).content.strip()
        
        if "PASS" not in brand_res:
            failed_checks.append(f"Brand Audit: {brand_res}")
            audit_logs.append(f"Iteration {state['iteration_count']} - Brand Audit: Failed: {brand_res}")
        else:
            audit_logs.append(f"Iteration {state['iteration_count']} - Brand Audit: Passed")
            
        # 2. Fact Audit
        fact_res = self.model.invoke([
            SystemMessage(content=self.fact_audit_prompt),
            HumanMessage(content=candidate)
        ]).content.strip()
        
        if "PASS" not in fact_res:
            failed_checks.append(f"Fact Audit: {fact_res}")
            audit_logs.append(f"Iteration {state['iteration_count']} - Fact Audit: Failed: {fact_res}")
        else:
            audit_logs.append(f"Iteration {state['iteration_count']} - Fact Audit: Passed")

        # 3. Emotional Audit
        emotion_audit_instruction = self.emotional_audit_prompt_template.format(
            vibe=state['emotion_signals'].get('vibe', 'calm')
        )
        emotion_res = self.model.invoke([
            SystemMessage(content=emotion_audit_instruction),
            HumanMessage(content=candidate)
        ]).content.strip()
        
        if "PASS" not in emotion_res:
            failed_checks.append(f"Emotional Audit: {emotion_res}")
            audit_logs.append(f"Iteration {state['iteration_count']} - Emotional Audit: Failed: {emotion_res}")
        else:
            audit_logs.append(f"Iteration {state['iteration_count']} - Emotional Audit: Passed")

        # 4. Output Guardrail
        guardrail_res = self.model.invoke([
            SystemMessage(content=self.output_guardrail_prompt),
            HumanMessage(content=candidate)
        ]).content.strip()
        
        if "PASS" not in guardrail_res:
            failed_checks.append(f"Output Guardrail: {guardrail_res}")
            audit_logs.append(f"Iteration {state['iteration_count']} - Output Guardrail: Failed: {guardrail_res}")
        else:
            audit_logs.append(f"Iteration {state['iteration_count']} - Output Guardrail: Passed")

        return {"failed_checks": failed_checks, "audit_logs": audit_logs}

    def _iteration_enhancer(self, state: AgentState) -> Dict:
        """
        Increments the graph iteration count during revision loops.
        
        Args:
            state: The current operational state.
            
        Returns:
            State updates containing the incremented count.
        """
        return {"iteration_count": state["iteration_count"] + 1}

    def _compile_graph(self):
        """
        Assembles, binds conditional transitions, and compiles the state graph workflow.
        
        Returns:
            Compiled StateGraph with native checkpointer memory bindings.
        """
        workflow = StateGraph(AgentState)
        
        workflow.add_node("input_guardrail", self._input_guardrail)
        workflow.add_node("analyze_emotion", self._analyze_emotion_intent)
        workflow.add_node("enhance_prompt", self._enhance_prompt)
        workflow.add_node("generate", self._generate_response)
        workflow.add_node("run_audits", self._run_audits)
        workflow.add_node("iteration_enhancer", self._iteration_enhancer)
        
        workflow.set_entry_point("input_guardrail")
        
        workflow.add_conditional_edges(
            "input_guardrail",
            lambda state: "analyze_emotion" if state.get("is_safe", True) else END
        )
        
        workflow.add_edge("analyze_emotion", "enhance_prompt")
        workflow.add_edge("enhance_prompt", "generate")
        workflow.add_edge("generate", "run_audits")
        
        def should_continue(state: AgentState):
            if not state.get("is_safe", True):
                return "end"
            if not state.get("failed_checks"):
                return "end"
            if state.get("iteration_count", 0) >= 3:
                return "end"
            return "iterate"
            
        workflow.add_conditional_edges(
            "run_audits",
            should_continue,
            {
                "iterate": "iteration_enhancer",
                "end": END
            }
        )
        
        workflow.add_edge("iteration_enhancer", "generate")
        
        return workflow.compile(checkpointer=self.memory)

    @traceable
    def send_message(self, message: str) -> str:
        """
        Dispatches a message thread to the compiled LangGraph pipeline.
        
        Args:
            message: User query text input.
            
        Returns:
            The finalized agent reply text.
        """
        # Load messages from current session thread
        current_state = self.agent.get_state(self.config)
        messages = current_state.values.get("messages", [])
        
        inputs = {
            "messages": messages,
            "user_prompt": message,
            "is_safe": True,
            "emotion_signals": {},
            "enhanced_prompt": "",
            "response": "",
            "audit_logs": [],
            "failed_checks": [],
            "iteration_count": 0
        }
        
        # Invoke Graph
        final_state = self.agent.invoke(inputs, config=self.config)
        
        # Print audit reports (simple print logs)
        print("\n=== SYSTEM AUDIT REPORT ===")
        if not final_state.get("is_safe", True):
            print("Input Guardrail: BLOCKED (unrelated or unsafe input)")
        else:
            signals = final_state.get("emotion_signals", {})
            print(f"Detected Emotion: {signals.get('vibe', 'neutral').upper()}")
            print(f"Detected Intent: {signals.get('intent', 'general').upper()}")
            print(f"Reasoning: {signals.get('reason', '')}")
            print("\nAudit Steps:")
            for log in final_state.get("audit_logs", []):
                print(f"  {log}")
            print(f"Total Revision Loops: {final_state.get('iteration_count', 0)}")
        print("===========================\n")
        
        return final_state["response"]

    def get_history(self):
        """
        Retrieves the thread history messages from checkpointer memory.
        
        Returns:
            A list of historical messages.
        """
        state = self.agent.get_state(self.config)
        return state.values.get("messages", [])
