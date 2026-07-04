"""
CRM auto-update node — extracts user info from conversation and updates CRM.
"""

from typing import Dict
from langsmith import traceable
from ..state import AgentState


@traceable(name="crm_updater_node")
def crm_updater_node(state: AgentState) -> Dict:
    """
    Stub: Extracts new user info from the conversation and updates the CRM.
    
    Will be implemented in Phase 4 with LLM-powered extraction.
    """
    # Stub: no-op, pass through
    return {}
