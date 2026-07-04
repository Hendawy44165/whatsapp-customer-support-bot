"""
Blocker node — handles unrelated or harmful messages with a polite refusal.
No LLM call needed — simple deterministic response.
"""

from typing import Dict
from langchain_core.messages import AIMessage
from langsmith import traceable
from ..state import AgentState


BLOCK_RESPONSE = (
    "Thank you for reaching out. I am Nuit Fragrances' dedicated concierge "
    "and can only assist with questions about our fragrances, orders, and services. "
    "Is there anything fragrance-related I can help you with today?"
)


@traceable(name="blocker_node")
def blocker_node(state: AgentState) -> Dict:
    """
    Returns a polite refusal for unrelated or harmful content.
    Deterministic — no LLM call.
    """
    return {
        "messages": [AIMessage(content=BLOCK_RESPONSE)],
        "final_response": BLOCK_RESPONSE,
    }
