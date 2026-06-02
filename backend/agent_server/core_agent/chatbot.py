import os
import sys
from typing import Dict, List
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langsmith import traceable

# Local imports
from .state import AgentState
from .utils import DocumentAndPromptLoader
from .nodes import (
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

# Import our backend mcp client and db client
# Since the path redirects are set up by app.py, we can import them from parent folders
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from backend.agent_server.mcp_client import mcp_client
from backend.database import db

class CustomerServiceAgent:
    """
    A multi-stage agentic customer support chatbot built using LangGraph.
    Adapted to use Model Context Protocol (MCP) microservices for CRM, cart, 
    conversations, and expert routing.
    """

    def __init__(
        self, docs_dir="agent/docs", prompt_path="agent/prompts/system_prompt.md"
    ):
        self.docs_dir = docs_dir
        self.prompt_path = prompt_path

        # Load modular prompt files via utility helper
        # If the folders don't exist in local directory, point to core_agent prompts
        local_prompt_path = prompt_path
        if not os.path.exists(local_prompt_path):
            local_prompt_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "prompts", "system_prompt.md")
        
        local_docs_dir = docs_dir
        if not os.path.exists(local_docs_dir):
            local_docs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "docs")

        self.loader = DocumentAndPromptLoader(local_docs_dir, local_prompt_path)
        self.loader.setup_static_prompt()

        # Retrieve LLM config from database settings or environment variables
        llm_config = db.get_setting("llm_config") or {}
        provider_model_name = llm_config.get("provider_model_name") or os.getenv("PROVIDER_MODEL_NAME", "deepseek-chat")
        provider_api_key = os.getenv("PROVIDER_API_KEY")
        provider_base_url = os.getenv("PROVIDER_BASE_URL")

        # Initialize LLM
        self.model = ChatOpenAI(
            api_key=provider_api_key,
            base_url=provider_base_url,
            model=provider_model_name,
        )

        # Initialize Memory Checkpointer
        self.memory = MemorySaver()

        # --- MCP CRM Tools ---
        @tool
        def get_contact_profile(email: str) -> str:
            """Retrieves the HubSpot CRM customer profile by email. Returns contact details, lifecycle stage, and custom notes."""
            return mcp_client.call_tool("hubspot", "get_contact_profile", {"email": email})

        @tool
        def create_support_ticket(email: str, subject: str, description: str) -> str:
            """Creates a new support ticket in HubSpot CRM. Returns the ticket ID and status."""
            return mcp_client.call_tool("hubspot", "create_support_ticket", {"email": email, "subject": subject, "description": description})

        # --- MCP Shop Cart Tools ---
        @tool
        def list_products() -> str:
            """Lists all available fragrances in the Nuit catalog with prices, codes, and sizes."""
            return mcp_client.call_tool("shop_cart", "list_products", {})

        @tool
        def add_to_cart(conversation_id: str, product_code: str, quantity: int = 1) -> str:
            """Adds a fragrance to the client's shopping cart. Requires product_code (e.g. 'signature')."""
            return mcp_client.call_tool("shop_cart", "add_to_cart", {"conversation_id": conversation_id, "product_code": product_code, "quantity": quantity})

        @tool
        def edit_cart(conversation_id: str, product_code: str, quantity: int) -> str:
            """Modifies the quantity of a product in the cart. Set quantity to 0 to remove the item."""
            return mcp_client.call_tool("shop_cart", "edit_cart", {"conversation_id": conversation_id, "product_code": product_code, "quantity": quantity})

        @tool
        def get_cart(conversation_id: str) -> str:
            """Retrieves the active cart contents and calculates total price for the session."""
            return mcp_client.call_tool("shop_cart", "get_cart", {"conversation_id": conversation_id})

        @tool
        def generate_cart_report(conversation_id: str) -> str:
            """Programmatically generates a clean structured textual cart report (Without using AI generation)."""
            return mcp_client.call_tool("shop_cart", "generate_cart_report", {"conversation_id": conversation_id})

        # --- MCP Conversations Tools ---
        @tool
        def get_chat_history(conversation_id: str) -> str:
            """Retrieves the chronological text history of messages for context analysis."""
            return mcp_client.call_tool("conversations", "get_chat_history", {"conversation_id": conversation_id})

        @tool
        def queue_immediate_message(conversation_id: str, content: str) -> str:
            """Queues a reply message in the outbound buffer to be sent immediately to the user."""
            return mcp_client.call_tool("conversations", "queue_immediate_message", {"conversation_id": conversation_id, "content": content})

        @tool
        def queue_scheduled_followup(conversation_id: str, content: str, delay_seconds: int) -> str:
            """Schedules an outbound follow-up message to the customer after a specific delay in seconds."""
            return mcp_client.call_tool("conversations", "queue_scheduled_followup", {"conversation_id": conversation_id, "content": content, "delay_seconds": delay_seconds})

        # --- MCP Human Expert Handoff Tool ---
        @tool
        def request_human_handoff(conversation_id: str, handoff_summary: str) -> str:
            """Triggers the human escalation pipeline, assigning the chat to the least loaded expert and providing a redirection deep-link."""
            return mcp_client.call_tool("human_expert", "request_human_handoff", {"conversation_id": conversation_id, "handoff_summary": handoff_summary})

        # --- Internal Knowledge base doc retrieval tool ---
        @tool
        def retrieve_document_content(document_name: str) -> str:
            """Retrieves the full content of a specific knowledge document by its name.
            Available default document names:
            - 'faq': faq, shipping fees, return window, delivery.
            - 'icp': client profiles.
            - 'product_specs': fragrance notes, sizes.
            - 'brand_identity': brand voice and tone guide.
            - 'customer_service_sop': support SOP.
            """
            doc_name = document_name.strip().lower()
            # Try to get from database first
            all_db_docs = db.get_documents()
            for doc in all_db_docs:
                if doc_name in doc["filename"].lower():
                    return doc["content"]
            
            # Fallback to local prompt loader file registry
            return self.loader.doc_registry.get(
                doc_name,
                f"Document '{document_name}' not found. Available documents: {list(self.loader.doc_registry.keys())}",
            )

        # Collect tools
        self.tools = [
            get_contact_profile,
            create_support_ticket,
            list_products,
            add_to_cart,
            edit_cart,
            get_cart,
            generate_cart_report,
            get_chat_history,
            queue_immediate_message,
            queue_scheduled_followup,
            request_human_handoff,
            retrieve_document_content
        ]
        self.tools_by_name = {t.name: t for t in self.tools}

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
        Creates an isolated, separate execution run.
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

        self.agent.invoke(inputs, config=config)

        final_state = self.agent.get_state(config).values

        # Secure output: write output response to message queue instead of direct client reply,
        # but return response text here for internal tracking/testing
        return final_state["response"]

    def get_thread_state(self, thread_id: str) -> Dict:
        config = {"configurable": {"thread_id": thread_id}}
        return self.agent.get_state(config).values
