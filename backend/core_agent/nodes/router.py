"""
Router agent node — classifies user intent and routes to the appropriate agent.
Uses structured output with Pydantic validation and retry logic.
"""

from typing import Dict
from langchain_core.messages import SystemMessage, HumanMessage
from langsmith import traceable

from ..state import AgentState, RouterOutput
from ..config import get_model, load_prompt


@traceable(name="router_node")
def router_node(state: AgentState) -> Dict:
    """
    Classifies user intent and decides which agent handles the message.
    
    Uses model.with_structured_output(RouterOutput) for reliable parsing.
    Retries up to 2 times on validation failure.
    """
    model = get_model()
    system_prompt = load_prompt("router.md")

    # Build messages: system prompt + recent history (last 6 messages for context)
    messages = state.get("messages", [])
    recent_history = messages[-6:] if len(messages) > 6 else messages

    llm_messages = [SystemMessage(content=system_prompt)] + list(recent_history)

    # Structured output with retries
    structured_model = model.with_structured_output(RouterOutput)

    max_retries = 2
    last_error = None

    for attempt in range(max_retries + 1):
        try:
            if attempt == 0:
                result = structured_model.invoke(llm_messages)
            else:
                # Append error feedback for retry
                retry_messages = llm_messages + [
                    HumanMessage(content=(
                        f"Your previous response failed validation: {last_error}\n"
                        "Please try again with the correct format."
                    ))
                ]
                result = structured_model.invoke(retry_messages)

            return {"router_output": result}

        except Exception as e:
            last_error = str(e)
            if attempt == max_retries:
                # Fallback: route to QA with neutral sentiment
                fallback = RouterOutput(
                    next_agent="qa",
                    sentiment="neutral",
                    classification="general_inquiry",
                    reasoning=f"Router validation failed after {max_retries + 1} attempts: {last_error}. Falling back to QA.",
                )
                return {"router_output": fallback}
