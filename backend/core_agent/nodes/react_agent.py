"""
ReAct agent node — handles CRM operations with tool calling.
"""

from typing import Dict
from langsmith import traceable
from ..state import AgentState, ReactResult


@traceable(name="react_agent_node")
def react_agent_node(state: AgentState) -> Dict:
    """
    Stub: Executes CRM operations (order lookup, returns, exchanges).
    Uses reasoning-first approach: plan → check params → call tools.
    
    Will be implemented in Phase 3.
    """
    stub_result = ReactResult(
        status="failed",
        tool_output=None,
        missing_params=None,
        reasoning="[STUB] ReAct agent not yet implemented.",
        failure_reason="ReAct agent is a stub — coming in Phase 3.",
    )

    return {
        "react_result": stub_result,
        "react_turn_count": state.get("react_turn_count", 0) + 1,
    }
