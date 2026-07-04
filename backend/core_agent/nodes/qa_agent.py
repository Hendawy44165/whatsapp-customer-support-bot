"""
QA agent node — handles FAQ, policy questions, and presents ReAct results.
Uses hardcoded knowledge in the system prompt (no RAG) and a query_products tool.
Coordinates bidirectionally with the ReAct agent.
"""

from typing import Dict
from langchain_core.messages import SystemMessage, AIMessage, ToolMessage
from langsmith import traceable

from ..state import AgentState, QAOutput
from ..config import get_model, load_prompt
from ..tools import query_products


def _get_attr_or_key(obj, attr: str, default=None):
    """Safely get an attribute or dict key from an object."""
    if hasattr(obj, attr):
        return getattr(obj, attr, default)
    if isinstance(obj, dict):
        return obj.get(attr, default)
    return default


def _build_context_section(state: AgentState) -> str:
    """Build the dynamic context section injected after the system prompt.
    Only adds raw data context, with no python-side instructions or guiding text.
    """
    lines = []

    # Router context
    router_output = state.get("router_output")
    if router_output:
        sentiment = _get_attr_or_key(router_output, "sentiment")
        classification = _get_attr_or_key(router_output, "classification")
        if sentiment:
            lines.append(f"sentiment: {sentiment}")
        if classification:
            lines.append(f"classification: {classification}")

    # ReAct result context (if coming back from ReAct)
    react_result = state.get("react_result")
    if react_result:
        status = _get_attr_or_key(react_result, "status")
        if status:
            lines.append(f"react_status: {status}")

        tool_output = _get_attr_or_key(react_result, "tool_output")
        if tool_output:
            lines.append(f"react_tool_output: {tool_output}")

        missing = _get_attr_or_key(react_result, "missing_params")
        if missing:
            lines.append(f"react_missing_params: {missing}")

        reason = _get_attr_or_key(react_result, "failure_reason")
        if reason:
            lines.append(f"react_failure_reason: {reason}")

    # Learned user info
    user_info = state.get("learned_user_info", {})
    if user_info:
        lines.append(f"learned_user_info: {user_info}")

    if not lines:
        return ""

    return "\n\n# CONTEXT VARIABLES\n" + "\n".join(f"{line}" for line in lines)


@traceable(name="qa_agent_node")
def qa_agent_node(state: AgentState) -> Dict:
    """
    Generates a brand-voice response for the customer.

    Handles:
    - Direct FAQ/policy answers (knowledge hardcoded in system prompt)
    - Querying product details via query_products tool
    - Parameter collection for ReAct delegation
    - Presenting ReAct tool results in brand voice
    - Escalation when unable to resolve
    """
    model = get_model()
    system_prompt = load_prompt("qa_agent.md")

    # Append dynamic context
    context_section = _build_context_section(state)
    full_system_prompt = system_prompt + context_section

    # Build initial message list
    messages = state.get("messages", [])
    active_messages = [SystemMessage(content=full_system_prompt)] + list(messages)

    # 1. Bind query_products tool to model for any product information retrieval
    model_with_tools = model.bind_tools([query_products])

    # Run tool invocation loop (max 2 steps)
    for _ in range(2):
        response = model_with_tools.invoke(active_messages)
        if not response.tool_calls:
            break

        active_messages.append(response)
        for tool_call in response.tool_calls:
            if tool_call["name"] == "query_products":
                tool_result_str = query_products.invoke(tool_call["args"])
                active_messages.append(
                    ToolMessage(content=tool_result_str, tool_call_id=tool_call["id"])
                )

    # 2. Get final structured output using the Pydantic QAOutput schema
    structured_model = model.with_structured_output(QAOutput)
    final_output = structured_model.invoke(active_messages)

    # Extract final clean user-facing message and directive
    clean_message = final_output.message.strip()
    directive = final_output.qa_directive
    react_request = final_output.react_request

    updates: Dict = {
        "messages": [AIMessage(content=clean_message)],
        "qa_directive": directive,
        "final_response": clean_message,
    }

    if react_request:
        updates["react_request"] = react_request

    # Clear react_result after we've consumed it (prevent stale data on next turn)
    if state.get("react_result") is not None:
        updates["react_result"] = None

    return updates
