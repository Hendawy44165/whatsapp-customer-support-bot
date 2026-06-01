import os
from typing import Dict, List
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langsmith import traceable

# Local imports
from agent.state import AgentState
from agent.utils import DocumentAndPromptLoader
from agent.nodes import (
    ClassifierNode,
    DirectResponseNode,
    EmotionAnalyzerNode,
    EnhancePromptNode,
    GeneratorNode,
    AuditorNode,
    QuickFixerNode,
    IterationEnhancerNode,
    HumanHandoffNode,
    SaveHistoryNode,
)



class CustomerServiceAgent:
    """
    A multi-stage agentic customer support chatbot built using LangGraph.

    Orchestrates nodes, coordinates graph transitions, manages checkpointer memory,
    and exposes interface methods to submit customer service requests.
    """

    def __init__(
        self, docs_dir="agent/docs", prompt_path="agent/prompts/system_prompt.md"
    ):
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
            model=provider_model_name,
        )

        # Initialize Memory Checkpointer
        self.memory = MemorySaver()
        self.config = {"configurable": {"thread_id": "default-thread"}}

        # Define the dynamic document retrieval tool
        @tool
        def retrieve_document_content(document_name: str) -> str:
            """Retrieves the full content of a specific knowledge document by its name.
            Available document names:
            - 'faq': FAQ, shipping fees, shipping times, return windows, exchange rules, international delivery.
            - 'icp': Customer career segments, demographic traits, and behavioral triggers.
            - 'meta_ad_strat': Ad campaigns, Shark Tank Egypt, Discovery Box bundles, active promos.
            - 'product_specs': Fragrance notes, classification, ingredients, bottle sizes, application protocols.
            - 'terms_of_conditions_and_policies': Pricing matrix, variant names, return/refund exclusions, damaged item reporting.
            - 'brand_identity': Brand voice guide, vocabulary list, and tone constraints.
            - 'customer_service_sop': Standard operating procedures for customer service.
            """
            doc_name = document_name.strip().lower()
            return self.loader.doc_registry.get(
                doc_name,
                f"Document '{document_name}' not found. Available documents: {list(self.loader.doc_registry.keys())}",
            )

        # Define the order tracking tool
        @tool
        def look_up_order(order_id: str | None = None, phone_number: str | None = None) -> str:

            """Retrieves current order tracking status, items, carrier, tracking ID, and shipping details.
            Provide either 'order_id' or 'phone_number' (or both) to locate the shipment in the database.
            Example Order IDs: 'NUIT-1001', 'NUIT-1002', 'NUIT-1003'.
            Example Phone Numbers: '+201234567890', '+201099887766'.
            """
            from agent.mock_db import MOCK_ORDERS_DB

            if not order_id and not phone_number:
                return "Please provide an Order ID or Phone Number to lookup shipment status."

            if order_id:
                oid = order_id.strip().upper()
                if oid in MOCK_ORDERS_DB:
                    order = MOCK_ORDERS_DB[oid]
                    return (
                        f"Order {oid} status is: {order['status'].upper()}.\n"
                        f"- Customer: {order['customer_name']}\n"
                        f"- Items: {order['items']}\n"
                        f"- Carrier: {order['carrier']}\n"
                        f"- Tracking ID: {order['tracking_number']}\n"
                        f"- Estimated Delivery/Status: {order['estimated_delivery']}"
                    )

            if phone_number:
                ph = phone_number.strip()
                matches = []
                for oid, order in MOCK_ORDERS_DB.items():
                    if order["mobile_number"] == ph:
                        matches.append(order)
                if matches:
                    results = []
                    for order in matches:
                        results.append(
                            f"Order {order['order_id']} status is: {order['status'].upper()}.\n"
                            f"- Customer: {order['customer_name']}\n"
                            f"- Items: {order['items']}\n"
                            f"- Carrier: {order['carrier']}\n"
                            f"- Tracking ID: {order['tracking_number']}\n"
                            f"- Estimated Delivery/Status: {order['estimated_delivery']}"
                        )
                    return "\n\n".join(results)

            return f"No matching order found in the system database for Order ID: '{order_id}' / Phone Number: '{phone_number}'."

        self.retrieve_tool = retrieve_document_content
        self.lookup_tool = look_up_order
        self.tools = [retrieve_document_content, look_up_order]
        self.tools_by_name = {
            "retrieve_document_content": retrieve_document_content,
            "look_up_order": look_up_order,
        }

        # Initialize Nodes
        self.classifier_node = ClassifierNode(self)
        self.direct_response_node = DirectResponseNode(self)
        self.emotion_analyzer_node = EmotionAnalyzerNode(self)
        self.enhance_prompt_node = EnhancePromptNode(self)
        self.generator_node = GeneratorNode(self)
        self.auditor_node = AuditorNode(self)
        self.quick_fixer_node = QuickFixerNode(self)
        self.iteration_enhancer_node = IterationEnhancerNode(self)
        self.handoff_node = HumanHandoffNode(self)
        self.save_history_node = SaveHistoryNode(self)

        # Compile State Graph
        self.agent = self._compile_graph()

    def _compile_graph(self):
        """
        Assembles, binds conditional transitions, and compiles the state graph workflow.

        Returns:
            Compiled StateGraph with native checkpointer memory bindings.
        """
        workflow = StateGraph(AgentState)

        workflow.add_node("classifier", self.classifier_node)
        workflow.add_node("direct_response", self.direct_response_node)
        workflow.add_node("analyze_emotion", self.emotion_analyzer_node)
        workflow.add_node("enhance_prompt", self.enhance_prompt_node)
        workflow.add_node("generate", self.generator_node)
        workflow.add_node("run_audits", self.auditor_node)
        workflow.add_node("iteration_enhancer", self.iteration_enhancer_node)
        workflow.add_node("quick_fixer", self.quick_fixer_node)
        workflow.add_node("handoff", self.handoff_node)
        workflow.add_node("save_history", self.save_history_node)


        workflow.set_entry_point("classifier")

        def route_classifier(state: AgentState):
            category = state.get("category", "complex_uncategorized")
            if category in ["complex_uncategorized", "order_tracking"]:
                return "analyze_emotion"
            return "direct_response"

        workflow.add_conditional_edges(
            "classifier",
            route_classifier,
            {
                "analyze_emotion": "analyze_emotion",
                "direct_response": "direct_response",
            },
        )

        workflow.add_edge("direct_response", END)

        workflow.add_edge("analyze_emotion", "enhance_prompt")
        workflow.add_edge("enhance_prompt", "generate")
        workflow.add_edge("generate", "run_audits")

        def should_continue(state: AgentState):
            if state.get("is_handoff", False):
                return "handoff"

            if not state.get("failed_checks"):
                return "save_history"

            # Route to handoff if iterations exceed limit and checks still fail
            if state.get("iteration_count", 0) >= 3:
                return "handoff"

            audit_results = state.get("audit_results", [])
            for res in audit_results:
                if res.get("action_type") == "human_handoff":
                    return "handoff"

            has_full_iteration = False
            for res in audit_results:
                if (
                    res.get("status_code") == "hard_error"
                    and res.get("action_type") == "full_iteration"
                ):
                    has_full_iteration = True
                    break

            if has_full_iteration:
                return "full_iteration"
            return "quick_fix"

        workflow.add_conditional_edges(
            "run_audits",
            should_continue,
            {
                "full_iteration": "iteration_enhancer",
                "quick_fix": "quick_fixer",
                "handoff": "handoff",
                "save_history": "save_history",
            },
        )

        workflow.add_edge("iteration_enhancer", "generate")
        workflow.add_edge("quick_fixer", "run_audits")
        workflow.add_edge("handoff", END)
        workflow.add_edge("save_history", END)


        return workflow.compile(checkpointer=self.memory)

    @traceable
    def send_message(self, message: str, thread_id: str = "default-thread") -> str:
        """
        Dispatches a message thread to the compiled LangGraph pipeline.

        Args:
            message: User query text input.
            thread_id: Thread/session identifier.

        Returns:
            The finalized agent reply text.
        """
        config = {"configurable": {"thread_id": thread_id}}
        
        # Load messages from current session thread
        current_state = self.agent.get_state(config)
        messages = current_state.values.get("messages", [])

        inputs = {
            "messages": messages,
            "user_prompt": message,
            "category": "complex_uncategorized",
            "is_safe": True,
            "emotion_signals": {},
            "enhanced_prompt": "",
            "response": "",
            "audit_results": [],
            "audit_logs": [],
            "failed_checks": [],
            "iteration_count": 0,
            "is_handoff": False,
            "handoff_summary": "",
        }

        # Stream Graph updates in real-time
        print("\n>>> STARTING GRAPH EXECUTION STREAM <<<")
        for chunk in self.agent.stream(
            inputs, config=config, stream_mode="updates"
        ):
            for node_name, update in chunk.items():
                print(f"\n[Node: {node_name}] Completed")
                for key, val in update.items():
                    val_str = str(val)
                    print(f"  └─ {key}: {val_str}")
        print("\n>>> GRAPH EXECUTION COMPLETED <<<\n")

        # Get final state from checkpointer
        final_state = self.agent.get_state(config).values

        # Print audit reports (simple print logs)
        print("=== SYSTEM AUDIT REPORT ===")
        category = final_state.get("category", "complex_uncategorized")
        print(f"Routed Category: {category.upper()}")
        if category != "complex_uncategorized" and category != "order_tracking":
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

    def get_thread_state(self, thread_id: str) -> Dict:
        """
        Retrieves the state dictionary for a specific thread.
        """
        config = {"configurable": {"thread_id": thread_id}}
        return self.agent.get_state(config).values

