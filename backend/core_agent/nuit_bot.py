from typing import Dict

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import HumanMessage
from langsmith import traceable
from dotenv import load_dotenv

from .state import ServiceBotState
from .nodes import (
    router_node,
    qa_agent_node,
    react_agent_node,
    escalation_node,
    blocker_node,
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
        workflow.add_node("qa", qa_agent_node)
        workflow.add_node("react", react_agent_node)
        workflow.add_node("escalator", escalation_node)
        workflow.add_node("blocker", blocker_node)

        # Entry point
        workflow.set_entry_point("router")

        workflow.add_conditional_edges(
            "router",
            self._route,
            {
                "qa": "qa",
                "escalate": "escalator",
                "blocker": "blocker",
                "react": "react",
            },
        )

        workflow.add_conditional_edges(
            "qa",
            self._route,
            {
                "react": "react",
                "end": END,
            },
        )

        workflow.add_conditional_edges(
            "react",
            self._route,
            {
                "qa": "qa",
                "escalate": "escalator",
            },
        )

        # Terminal direct edges to END
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

        if next_agent == "qa":
            return "qa"
        elif next_agent == "escalate":
            return "escalate"
        elif next_agent == "blocker":
            return "blocker"
        elif next_agent == "react":
            return "react"
        elif next_agent == "end":
            return "end"

        else:
            raise ValueError("Router output does not specify a valid route.")
