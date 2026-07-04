"""
Nuit Bot v2 — LangGraph compilation and entry point.

Replaces the old chatbot.py. Compiles the multi-agent graph with:
  Router → QA ↔ ReAct → Escalation
"""

import os
from typing import Dict

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langsmith import traceable
from dotenv import load_dotenv

from .state import AgentState
from .config import get_model
from .nodes import (
    router_node,
    qa_agent_node,
    react_agent_node,
    escalation_node,
    blocker_node,
    crm_updater_node,
)

load_dotenv()


# ---------------------------------------------------------------------------
# Routing functions
# ---------------------------------------------------------------------------

def _route_after_router(state: AgentState) -> str:
    """Decide which node to go to after the Router."""
    router_output = state.get("router_output")
    if router_output is None:
        return "qa"

    # Handle both Pydantic model and dict (checkpointer may deserialize as dict)
    if isinstance(router_output, dict):
        next_agent = router_output.get("next_agent", "qa")
    else:
        next_agent = router_output.next_agent

    if next_agent == "escalate":
        return "escalation"
    if next_agent == "block":
        return "blocker"
    return "qa"


def _route_after_qa(state: AgentState) -> str:
    """Decide which node to go to after the QA agent."""
    directive = state.get("qa_directive", "answer")

    if directive == "delegate_to_react":
        # Guardrail: max 3 ReAct invocations per turn
        if state.get("react_turn_count", 0) >= 3:
            return "escalation"
        return "react"

    if directive == "escalate":
        return "escalation"

    # "answer", "present_results", "ask_for_params" — all go to CRM update then END
    return "crm_updater"


# ---------------------------------------------------------------------------
# Graph compilation
# ---------------------------------------------------------------------------

def compile_graph(checkpointer=None):
    """
    Build and compile the Nuit Bot v2 LangGraph.

    Returns a compiled CompiledGraph ready for invocation.
    """
    if checkpointer is None:
        checkpointer = MemorySaver()

    workflow = StateGraph(AgentState)

    # Register nodes
    workflow.add_node("router", router_node)
    workflow.add_node("qa", qa_agent_node)
    workflow.add_node("react", react_agent_node)
    workflow.add_node("escalation", escalation_node)
    workflow.add_node("blocker", blocker_node)
    workflow.add_node("crm_updater", crm_updater_node)

    # Entry point
    workflow.set_entry_point("router")

    # Router → QA | Escalation | Blocker
    workflow.add_conditional_edges(
        "router",
        _route_after_router,
        {
            "qa": "qa",
            "escalation": "escalation",
            "blocker": "blocker",
        },
    )

    # QA → ReAct | Escalation | CRM Update
    workflow.add_conditional_edges(
        "qa",
        _route_after_qa,
        {
            "react": "react",
            "escalation": "escalation",
            "crm_updater": "crm_updater",
        },
    )

    # ReAct always returns to QA
    workflow.add_edge("react", "qa")

    # Terminal edges
    workflow.add_edge("crm_updater", END)
    workflow.add_edge("escalation", END)
    workflow.add_edge("blocker", END)

    return workflow.compile(checkpointer=checkpointer)


# ---------------------------------------------------------------------------
# High-level send_message API
# ---------------------------------------------------------------------------

class NuitBot:
    """
    High-level wrapper around the compiled LangGraph.
    Manages model instance, checkpointer, and message dispatch.
    """

    def __init__(self):
        self.model = get_model()
        self.memory = MemorySaver()
        self.graph = compile_graph(checkpointer=self.memory)

    @traceable(name="send_message")
    def send_message(self, message: str, thread_id: str = "default") -> str:
        """
        Send a user message through the graph pipeline.

        Args:
            message: The user's message text.
            thread_id: UUID session ID for thread persistence.

        Returns:
            The final response string to send to the user.
        """
        from langchain_core.messages import HumanMessage

        config = {"configurable": {"thread_id": thread_id}}

        inputs = {
            "messages": [HumanMessage(content=message)],
            "router_output": None,
            "qa_directive": "answer",
            "react_request": None,
            "react_result": None,
            "escalation_report": None,
            "learned_user_info": {},
            "react_turn_count": 0,
            "final_response": "",
        }

        # Run the graph
        result = self.graph.invoke(inputs, config=config)

        return result.get("final_response", "[No response generated]")

    def get_thread_state(self, thread_id: str) -> Dict:
        """Retrieve the current state of a conversation thread."""
        config = {"configurable": {"thread_id": thread_id}}
        return self.graph.get_state(config).values
