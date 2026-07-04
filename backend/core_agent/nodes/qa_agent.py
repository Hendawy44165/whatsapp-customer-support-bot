"""
QA agent node — handles FAQ, policy questions, and presents ReAct results.
Uses hardcoded knowledge in the system prompt (no RAG).
Coordinates bidirectionally with the ReAct agent.
"""

import re
from typing import Dict
from langchain_core.messages import SystemMessage, AIMessage
from langsmith import traceable

from ..state import AgentState
from ..config import get_model, load_prompt


def _get_attr_or_key(obj, attr: str, default=None):
    """Safely get an attribute or dict key from an object."""
    if hasattr(obj, attr):
        return getattr(obj, attr, default)
    if isinstance(obj, dict):
        return obj.get(attr, default)
    return default


def _build_context_section(state: AgentState) -> str:
    """Build the dynamic context section injected after the system prompt."""
    lines = []

    # Router context
    router_output = state.get("router_output")
    if router_output:
        sentiment = _get_attr_or_key(router_output, "sentiment")
        classification = _get_attr_or_key(router_output, "classification")
        if sentiment:
            lines.append(f"User Sentiment: {sentiment}")
        if classification:
            lines.append(f"Intent Classification: {classification}")

    # ReAct result context (if coming back from ReAct)
    react_result = state.get("react_result")
    if react_result:
        status = _get_attr_or_key(react_result, "status")
        if status:
            lines.append(f"ReAct Agent Status: {status}")

        if status == "success":
            tool_output = _get_attr_or_key(react_result, "tool_output")
            if tool_output:
                lines.append(f"ReAct Tool Output: {tool_output}")
            lines.append(
                "INSTRUCTION: Present these results to the customer in brand voice. "
                "Use the directive [DIRECTIVE: present_results]."
            )

        elif status == "need_info":
            missing = _get_attr_or_key(react_result, "missing_params")
            if missing:
                lines.append(f"Missing Parameters Needed From User: {missing}")
            reasoning = _get_attr_or_key(react_result, "reasoning")
            if reasoning:
                lines.append(f"ReAct Reasoning: {reasoning}")
            lines.append(
                "INSTRUCTION: Ask the user politely for the missing information listed above. "
                "Use the directive [DIRECTIVE: ask_for_params]."
            )

        elif status == "failed":
            reason = _get_attr_or_key(react_result, "failure_reason")
            if reason:
                lines.append(f"ReAct Failure Reason: {reason}")
            tool_output = _get_attr_or_key(react_result, "tool_output")
            if tool_output:
                lines.append(f"ReAct Failed Tool Output: {tool_output}")
            lines.append(
                "INSTRUCTION: The operation failed. If the failure message contains useful info "
                "(e.g. 'not eligible for return'), explain it to the user. "
                "If the error is a system error, apologize and escalate. "
                "Use [DIRECTIVE: answer] if you can explain the failure, "
                "or [DIRECTIVE: escalate] if it requires human help."
            )

    # Learned user info
    user_info = state.get("learned_user_info", {})
    if user_info:
        lines.append(f"Known User Info: {user_info}")

    if not lines:
        return ""

    return "\n\n# CONTEXT VARIABLES\n" + "\n".join(f"- {line}" for line in lines)


def _parse_directive(response_text: str) -> tuple[str, str | None, str]:
    """
    Parse the directive and optional react_request from the response text.
    Returns (directive, react_request, clean_response).
    """
    directive = "answer"
    react_request = None

    # Extract directive
    directive_match = re.search(r"\[DIRECTIVE:\s*([\w_]+)\]", response_text)
    if directive_match:
        directive = directive_match.group(1).strip()

    # Extract react request
    react_match = re.search(r"\[REACT_REQUEST:\s*(.+?)\]", response_text)
    if react_match:
        react_request = react_match.group(1).strip()

    # Clean all bracket tags from the user-facing response
    clean_text = re.sub(r"\[DIRECTIVE:.*?\]", "", response_text)
    clean_text = re.sub(r"\[REACT_REQUEST:.*?\]", "", clean_text)
    clean_text = clean_text.strip()

    return directive, react_request, clean_text


@traceable(name="qa_agent_node")
def qa_agent_node(state: AgentState) -> Dict:
    """
    Generates a brand-voice response for the customer.

    Handles:
    - Direct FAQ/policy answers (knowledge hardcoded in system prompt)
    - Parameter collection for ReAct delegation
    - Presenting ReAct tool results in brand voice
    - Escalation when unable to resolve
    """
    model = get_model()
    system_prompt = load_prompt("qa_agent.md")

    # Append dynamic context
    context_section = _build_context_section(state)
    full_system_prompt = system_prompt + context_section

    # Build message list: system prompt + full conversation history
    messages = state.get("messages", [])
    llm_messages = [SystemMessage(content=full_system_prompt)] + list(messages)

    # Invoke LLM
    response = model.invoke(llm_messages)
    response_text = response.content or ""

    # Parse directive and clean response
    directive, react_request, clean_response = _parse_directive(response_text)

    # Validate directive
    valid_directives = {
        "answer", "delegate_to_react", "present_results",
        "ask_for_params", "escalate",
    }
    if directive not in valid_directives:
        directive = "answer"

    updates: Dict = {
        "messages": [AIMessage(content=clean_response)],
        "qa_directive": directive,
        "final_response": clean_response,
    }

    if react_request:
        updates["react_request"] = react_request

    # Clear react_result after we've consumed it (prevent stale data on next turn)
    if state.get("react_result") is not None:
        updates["react_result"] = None

    return updates
