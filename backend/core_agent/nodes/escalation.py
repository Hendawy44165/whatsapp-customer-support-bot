"""
Human Escalation agent node — generates escalation reports and queues them.
Uses structured output with Pydantic for reliable report generation.
"""

from typing import Dict
from langchain_core.messages import SystemMessage, AIMessage, HumanMessage
from langsmith import traceable

from ..state import AgentState, EscalationReport
from ..config import get_model, load_prompt
from ..tools import add_to_escalation_queue


HANDOFF_MESSAGE = (
    "I am connecting you directly with a specialist from our care team "
    "to resolve this for you immediately. A live representative will review "
    "your message history and pick up this chat right here within 60 seconds."
)


@traceable(name="escalation_node")
def escalation_node(state: AgentState) -> Dict:
    """
    Generates a structured escalation report from the conversation history
    and adds it to the escalation queue for human agents.
    """
    model = get_model()
    system_prompt = load_prompt("escalation.md")

    # Build messages for report generation
    messages = state.get("messages", [])
    llm_messages = [SystemMessage(content=system_prompt)] + list(messages)

    # Structured output with retries
    structured_model = model.with_structured_output(EscalationReport)

    max_retries = 2
    last_error = None
    report = None

    for attempt in range(max_retries + 1):
        try:
            if attempt == 0:
                report = structured_model.invoke(llm_messages)
            else:
                retry_messages = llm_messages + [
                    HumanMessage(content=(
                        f"Your previous response failed validation: {last_error}\n"
                        "Please try again with the correct format."
                    ))
                ]
                report = structured_model.invoke(retry_messages)
            break

        except Exception as e:
            last_error = str(e)
            if attempt == max_retries:
                # Fallback report
                report = EscalationReport(
                    reason="direct_request",
                    chat_summary="Escalation report generation failed. Manual review required.",
                    urgency=0.7,
                    collected_metadata={},
                    recommended_actions=["Review full conversation history manually"],
                )

    # Write to escalation queue
    add_to_escalation_queue(report.model_dump())

    return {
        "escalation_report": report,
        "messages": [AIMessage(content=HANDOFF_MESSAGE)],
        "final_response": HANDOFF_MESSAGE,
    }
