"""
Human Escalation agent node — generates escalation reports and queues them.
Uses structured output with Pydantic for reliable report generation.
"""

from typing import Dict
from langchain_core.messages import SystemMessage, AIMessage, HumanMessage
from langsmith import traceable

from ..state import AgentState, ServiceBotState
from ..config import get_model, load_prompt
from ..tools import add_to_escalation_queue

HANDOFF_MESSAGE = (
    "I am connecting you directly with a specialist from our care team "
    "to resolve this for you immediately. A live representative will review "
    "your message history and pick up this chat right here within 60 seconds."
)


@traceable
def escalation_node(state: ServiceBotState) -> Dict:
    """
    Generates a structured escalation report from the conversation history
    and adds it to the escalation queue for human agents.
    """
    model = get_model()
    system_prompt = load_prompt("escalation.md")

    return {
        "messages": [AIMessage(content="Generating escalation report...")],
    }
