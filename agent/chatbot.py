import os
from typing import Dict
from langgraph.graph.message import add_messages
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langsmith import traceable

# Local imports
from agent.state import AgentState
from agent.constants import VALID_CATEGORIES, DIRECT_RESPONSES
from agent.utils import DocumentAndPromptLoader

class CustomerServiceAgent:
    """
    A multi-stage agentic customer support chatbot built using LangGraph.
    
    Handles incoming support requests for Nuit Fragrances with safety guardrails,
    emotional intelligence analysis, dynamic document retrieval tools, and
    audited self-correction iteration loops.
    """
    def __init__(self, docs_dir="agent/docs", prompt_path="agent/prompts/system_prompt.md"):
        """
        Initializes the Customer Service Agent.
        
        Args:
            docs_dir: Directory containing knowledge files (FAQ, policies, specs).
            prompt_path: File path to the core concierge system instructions.
        """
        self.docs_dir = docs_dir
        self.prompt_path = prompt_path
        
        # Load modular prompt files and document collections via utility helper
        self.loader = DocumentAndPromptLoader(docs_dir, prompt_path)
        
        # Setup static prompt content
        self.loader.setup_static_prompt()
        
        # Retrieve configuration from environment variables
        provider_api_key = os.getenv("PROVIDER_API_KEY")
        provider_base_url = os.getenv("PROVIDER_BASE_URL")
        provider_model_name = os.getenv("PROVIDER_MODEL_NAME", "deepseek-chat")
        
        # Initialize LangChain OpenAI Compatible Model
        self.model = ChatOpenAI(
            api_key=provider_api_key,
            base_url=provider_base_url,
            model=provider_model_name
        )
        
        # Initialize Memory Checkpointer
        self.memory = MemorySaver()
        self.config = {"configurable": {"thread_id": "default-thread"}}
        
        # Compile State Graph
        self.agent = self._compile_graph()

    def _classifier(self, state: AgentState) -> Dict:
        """
        Classifies the incoming user prompt to determine if it can be routed directly
        or requires the main complex agent workflow.
        
        Args:
            state: The current operational state.
            
        Returns:
            State updates containing the classified 'category'.
        """
        user_prompt = state["user_prompt"]
        res = self.model.invoke([
            SystemMessage(content=self.loader.classifier_prompt),
            HumanMessage(content=user_prompt)
        ]).content.strip().lower()
        
        res = res.replace("`", "").strip()
        category = res if res in VALID_CATEGORIES else "complex_uncategorized"
        
        return {"category": category}

    def _direct_response(self, state: AgentState) -> Dict:
        """
        Generates brand-compliant direct responses for simple categories,
        bypassing the main generator loop and audits.
        
        Args:
            state: The current operational state.
            
        Returns:
            State updates containing the final direct response.
        """
        category = state.get("category", "complex_uncategorized")
        user_prompt = state["user_prompt"]
        reply = DIRECT_RESPONSES.get(category, "I apologize, let me connect you with support.")
        
        return {
            "response": reply,
            "messages": [HumanMessage(content=user_prompt), AIMessage(content=reply)]
        }

    def _analyze_emotion_intent(self, state: AgentState) -> Dict:
        """
        Extracts customer sentiment patterns and intent level from conversation history.
        
        Args:
            state: The current operational state.
            
        Returns:
            State updates containing structured emotion signals.
        """
        user_prompt = state["user_prompt"]
        history = state.get("messages", [])
        history_text = "\n".join([f"{m.type}: {m.content}" for m in history[-5:]])
        
        prompt = f"Chat History:\n{history_text}\n\nUser Prompt: {user_prompt}"
        res = self.model.invoke([
            SystemMessage(content=self.loader.emotion_analysis_prompt),
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
        Used primarily as fallback if context caching is unavailable.
        
        Args:
            state: The current operational state.
            
        Returns:
            State updates with the consolidated 'enhanced_prompt' string.
        """
        system_prompt = self.loader.load_system_prompt()
        doc_list_str = "\n".join(self.loader.doc_descriptions)
        
        signals = state.get("emotion_signals", {})
        emotion = signals.get("vibe", "calm")
        intent = signals.get("intent", "browsing")
        reason = signals.get("reason", "")
        
        enhanced_prompt = (
            f"{system_prompt}\n\n"
            f"=== PERMANENT CONTEXT ===\n{self.loader.permanent_context}\n\n"
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
            return self.loader.doc_registry.get(doc_name, f"Document '{document_name}' not found. Available documents: {list(self.loader.doc_registry.keys())}")

        model_with_tools = self.model.bind_tools([retrieve_document_content])
        
        signals = state.get("emotion_signals", {})
        emotion = signals.get("vibe", "calm")
        intent = signals.get("intent", "browsing")
        reason = signals.get("reason", "")
        
        dynamic_context = (
            f"=== EMOTIONAL & INTENT CONTEXT ===\n"
            f"- User emotional state: {emotion} (Reason: {reason})\n"
            f"- User buying intent level: {intent}\n"
            f"Instruction: Adapt your tone and response format to match the customer's emotional state. "
            f"If the user is anxious or frustrated, address their concern directly and reassuringly."
        )
        
        full_system = f"{self.loader.static_prompt_content}\n\n{dynamic_context}"
        messages = [
            SystemMessage(content=full_system)
        ]
            
        if state.get("iteration_count", 0) > 0:
            revision_feedback = (
                f"CRITICAL: The previous response failed verification audits.\n"
                f"Failed Checks:\n" + "\n".join([f"- {err}" for err in state["failed_checks"]]) + "\n\n"
                f"Please rewrite the response to resolve these violations. Do not repeat the same errors."
            )
            messages.append(SystemMessage(content=revision_feedback))
            
        messages.extend(state.get("messages", [])[-5:])
        messages.append(HumanMessage(content=user_prompt))
        
        new_messages = [HumanMessage(content=user_prompt)]
        
        for _ in range(5):
            response = model_with_tools.invoke(messages)
                
            messages.append(response)
            new_messages.append(response)
            
            if not response.tool_calls:
                content = response.content
                if isinstance(content, list):
                    texts = []
                    for block in content:
                        if isinstance(block, dict) and "text" in block:
                            texts.append(block["text"])
                        elif isinstance(block, str):
                            texts.append(block)
                    content = "".join(texts)
                return {
                    "response": content,
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
                
        content = response.content
        if isinstance(content, list):
            texts = []
            for block in content:
                if isinstance(block, dict) and "text" in block:
                    texts.append(block["text"])
                elif isinstance(block, str):
                    texts.append(block)
            content = "".join(texts)
            
        return {
            "response": content,
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
        candidate = state.get("response", "")
        if isinstance(candidate, list):
            texts = []
            for block in candidate:
                if isinstance(block, dict) and "text" in block:
                    texts.append(block["text"])
                elif isinstance(block, str):
                    texts.append(block)
            candidate = "".join(texts)
            
        failed_checks = []
        audit_logs = list(state.get("audit_logs", []))
        
        # Guard against empty candidate responses (e.g. if the generator loop fails or is blocked)
        if not candidate or not candidate.strip():
            failed_checks.append("Generation Audit: Candidate response is empty.")
            audit_logs.append(f"Iteration {state['iteration_count']} - Generation Audit: Failed: Response is empty.")
            return {"failed_checks": failed_checks, "audit_logs": audit_logs}
        
        # 1. Brand Audit
        brand_res = self.model.invoke([
            SystemMessage(content=self.loader.brand_audit_prompt),
            HumanMessage(content=candidate)
        ]).content.strip()
        
        if "PASS" not in brand_res:
            failed_checks.append(f"Brand Audit: {brand_res}")
            audit_logs.append(f"Iteration {state['iteration_count']} - Brand Audit: Failed: {brand_res}")
        else:
            audit_logs.append(f"Iteration {state['iteration_count']} - Brand Audit: Passed")
            
        # 2. Fact Audit
        fact_res = self.model.invoke([
            SystemMessage(content=self.loader.fact_audit_prompt),
            HumanMessage(content=candidate)
        ]).content.strip()
        
        if "PASS" not in fact_res:
            failed_checks.append(f"Fact Audit: {fact_res}")
            audit_logs.append(f"Iteration {state['iteration_count']} - Fact Audit: Failed: {fact_res}")
        else:
            audit_logs.append(f"Iteration {state['iteration_count']} - Fact Audit: Passed")

        # 3. Emotional Audit
        emotion_audit_instruction = self.loader.emotional_audit_prompt_template.format(
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
            SystemMessage(content=self.loader.output_guardrail_prompt),
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
        
        workflow.add_node("classifier", self._classifier)
        workflow.add_node("direct_response", self._direct_response)
        workflow.add_node("analyze_emotion", self._analyze_emotion_intent)
        workflow.add_node("enhance_prompt", self._enhance_prompt)
        workflow.add_node("generate", self._generate_response)
        workflow.add_node("run_audits", self._run_audits)
        workflow.add_node("iteration_enhancer", self._iteration_enhancer)
        
        workflow.set_entry_point("classifier")
        
        def route_classifier(state: AgentState):
            category = state.get("category", "complex_uncategorized")
            if category == "complex_uncategorized":
                return "analyze_emotion"
            return "direct_response"
            
        workflow.add_conditional_edges(
            "classifier",
            route_classifier,
            {
                "analyze_emotion": "analyze_emotion",
                "direct_response": "direct_response"
            }
        )
        
        workflow.add_edge("direct_response", END)
        
        workflow.add_edge("analyze_emotion", "enhance_prompt")
        workflow.add_edge("enhance_prompt", "generate")
        workflow.add_edge("generate", "run_audits")
        
        def should_continue(state: AgentState):
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
            "category": "complex_uncategorized",
            "is_safe": True,
            "emotion_signals": {},
            "enhanced_prompt": "",
            "response": "",
            "audit_logs": [],
            "failed_checks": [],
            "iteration_count": 0
        }
        
        # Stream Graph updates in real-time
        print("\n>>> STARTING GRAPH EXECUTION STREAM <<<")
        for chunk in self.agent.stream(inputs, config=self.config, stream_mode="updates"):
            for node_name, update in chunk.items():
                print(f"\n[Node: {node_name}] Completed")
                for key, val in update.items():
                    val_str = str(val)
                    if len(val_str) > 160:
                        val_str = val_str[:160] + "..."
                    print(f"  └─ {key}: {val_str}")
        print("\n>>> GRAPH EXECUTION COMPLETED <<<\n")
        
        # Get final state from checkpointer
        final_state = self.agent.get_state(self.config).values
        
        # Print audit reports (simple print logs)
        print("=== SYSTEM AUDIT REPORT ===")
        category = final_state.get("category", "complex_uncategorized")
        print(f"Routed Category: {category.upper()}")
        if category != "complex_uncategorized":
            print("Action: DIRECT RESPONSE ROUTE (audits bypassed)")
        else:
            signals = final_state.get("emotion_signals", {})
            print(f"Detected Emotion: {signals.get('vibe', 'neutral').upper()}")
            print(f"Detected Intent: {signals.get('intent', 'general').upper()}")
            print(f"Reasoning: {signals.get('reason', '')}")
            print("\nAudit Steps:")
            for log in final_state.get("audit_logs", []):
                print(f"  {log}")
            print(f"Total Revision Loops: {final_state.get('iteration_count', 0)}")
        print(f"\nFinal AI Response:\n{final_state.get('response', '')}")
        print("===========================\n")
        
        return final_state["response"]

    @traceable
    def get_history(self):
        """
        Retrieves the thread history messages from checkpointer memory.
        
        Returns:
            A list of historical messages.
        """
        state = self.agent.get_state(self.config)
        return state.values.get("messages", [])
