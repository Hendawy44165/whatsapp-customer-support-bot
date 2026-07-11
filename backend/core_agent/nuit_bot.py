from typing import Dict

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import HumanMessage
from langsmith import traceable
from dotenv import load_dotenv

from .state import ServiceBotState
from .nodes import (
    router_node,
    simple_qa_node,
    analyzer_node,
    need_qa_node,
    escalation_node,
    blocker_node,
    planner_node,
    executer_node,
)

load_dotenv()


class NuitBot:
    """
    High-level wrapper around the compiled LangGraph.
    Manages model instance, checkpointer, and message dispatch.
    """

    def __init__(self):
        self.memory = MemorySaver()
        self.graph = self.compile_graph(checkpointer=self.memory)

    @traceable(name="send_message")
    def send_message(self, message: str, thread_id: str = "default"):
        """
        Send a user message through the graph pipeline.

        Args:
            message: The user's message text.
            thread_id: UUID session ID for thread persistence.

        Returns:
            The final response string to send to the user.
        """

        config = {"configurable": {"thread_id": thread_id}}

        input = {
            "messages": [HumanMessage(content=message)],
        }

        response = self.graph.invoke(input=input, config=config)

        # CRM Update Subroutine: Sync profile details when turn finishes
        state = self.graph.get_state(config).values
        phone = ""
        extracted_params = state.get("extracted_parameters") or {}
        gathered_params = state.get("gathered_parameters") or {}
        if extracted_params.get("phone"):
            phone = extracted_params["phone"]
        elif gathered_params.get("phone"):
            phone = gathered_params["phone"]

        metadata = state.get("analyzer_metadata")
        if phone and metadata and metadata.get("knowledge_graph"):
            from .tools import update_crm_profile

            update_crm_profile(
                phone,
                {
                    "knowledge_graph": metadata["knowledge_graph"],
                    "evidence": metadata.get("evidence", ""),
                    "directive": metadata.get("directive", ""),
                },
            )

        return response["messages"][-1].content

    def get_thread_state(self, thread_id: str) -> Dict:
        """Retrieve the current state of a conversation thread."""
        config = {"configurable": {"thread_id": thread_id}}
        return self.graph.get_state(config).values

    def compile_graph(self, checkpointer=None):
        """
        Build and compile the Nuit Bot v2 LangGraph.

        Returns a compiled CompiledGraph ready for invocation.
        """
        if checkpointer is None:
            checkpointer = MemorySaver()

        workflow = StateGraph(ServiceBotState)

        # Register nodes
        workflow.add_node("router", router_node)
        workflow.add_node("simple_qa", simple_qa_node)
        workflow.add_node("analyzer", analyzer_node)
        workflow.add_node("need_qa", need_qa_node)
        workflow.add_node("escalator", escalation_node)
        workflow.add_node("blocker", blocker_node)

        # Entry point
        workflow.set_entry_point("router")

        # Router routes to simple_qa, analyzer, escalator, or blocker
        workflow.add_conditional_edges(
            "router",
            self._route,
            {
                "simple_qa": "simple_qa",
                "analyzer": "analyzer",
                "escalate": "escalator",
                "blocker": "blocker",
            },
        )

        # Simple QA node always goes directly to the analyzer node
        workflow.add_edge("simple_qa", "analyzer")

        # Analyzer routes conditionally
        workflow.add_conditional_edges(
            "analyzer",
            self._route,
            {
                "need_qa": "need_qa",
                "escalate": "escalator",
                "end": END,
            },
        )

        # Need QA node always ends the turn
        workflow.add_edge("need_qa", END)
        workflow.add_edge("blocker", END)
        workflow.add_edge("escalator", END)

        return workflow.compile(checkpointer=checkpointer)

    def _route(self, state: ServiceBotState) -> str:
        """
        Determine the next node to route to based on the current state.

        Returns:
            The name of the next node to invoke.
        """
        next_agent = state["next_agent"]

        if next_agent is None:
            raise ValueError("Router output is None; cannot determine next node.")

        if next_agent == "simple_qa":
            return "simple_qa"
        elif next_agent == "analyzer":
            return "analyzer"
        elif next_agent == "need_qa":
            return "need_qa"
        elif next_agent == "escalate" or next_agent == "escalator":
            return "escalate"
        elif next_agent == "blocker" or next_agent == "block":
            return "blocker"
        elif next_agent == "end":
            return "end"
        else:
            raise ValueError(
                f"Router output does not specify a valid route: {next_agent}"
            )
