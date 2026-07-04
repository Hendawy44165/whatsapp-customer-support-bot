"""
QA agent node — handles FAQ, policy questions, and presents ReAct results.
Uses hardcoded knowledge in the system prompt (no RAG).
"""

import re
from typing import Dict
from langchain_core.messages import SystemMessage, AIMessage
from langsmith import traceable

from ..state import AgentState
from ..config import get_model, load_prompt


def _build_context_section(state: AgentState) -> str:
    """Build the dynamic context section injected after the system prompt."""
    lines = []

    # Router context
    router_output = state.get("router_output")
    if router_output:
        sentiment = router_output.sentiment if hasattr(router_output, "sentiment") else router_output.get("sentiment")
        classification = router_output.classification if hasattr(router_output, "classification") else router_output.get("classification")
        if sentiment:
            lines.append(f"User Sentiment: {sentiment}")
        if classification:
            lines.append(f"Intent Classification: {classification}")

    # ReAct result context (if coming back from ReAct)
    react_result = state.get("react_result")
    if react_result:
        status = react_result.status if hasattr(react_result, "status") else react_result.get("status")
        if status:
            lines.append(f"ReAct Agent Status: {status}")

        if status == "success":
            tool_output = react_result.tool_output if hasattr(react_result, "tool_output") else react_result.get("tool_output")
            if tool_output:
                lines.append(f"ReAct Tool Output: {tool_output}")

        elif status == "need_info":
            missing = react_result.missing_params if hasattr(react_result, "missing_params") else react_result.get("missing_params")
            if missing:
                lines.append(f"Missing Parameters Needed: {missing}")
            reasoning = react_result.reasoning if hasattr(react_result, "reasoning") else react_result.get("reasoning")
            if reasoning:
                lines.append(f"ReAct Reasoning: {reasoning}")

        elif status == "failed":
            reason = react_result.failure_reason if hasattr(react_result, "failure_reason") else react_result.get("failure_reason")
            if reason:
                lines.append(f"ReAct Failure Reason: {reason}")

    # Learned user info
    user_info = state.get("learned_user_info", {})
    if user_info:
        lines.append(f"Known User Info: {user_info}")

    if not lines:
        return ""

    return "\n\n#9. CONTEXT VARIABLES\n" + "\n".join(f"- {line}" for line in lines)


def _parse_directive(response_text: str) -> tuple[str, str | None, str]:
    """
    Parse the directive and optional react_request from the response text.
    Returns (directive, react_request, clean_response).
    """
    directive = "answer"
    react_request = None
    clean_text = response_text

    # Extract directive
    directive_match = re.search(r"\[DIRECTIVE:\s*(\w+)\]", response_text)
    if directive_match:
        directive = directive_match.group(1).strip()
        clean_text = response_text[:directive_match.start()].strip()

    # Extract react request
    react_match = re.search(r"\[REACT_REQUEST:\s*(.+?)\]", response_text)
    if react_match:
        react_request = react_match.group(1).strip()
        clean_text = clean_text[:react_match.start()].strip() if react_match.start() < len(clean_text) else clean_text

    # Clean up any remaining bracket tags
    clean_text = re.sub(r"\[DIRECTIVE:.*?\]", "", clean_text).strip()
    clean_text = re.sub(r"\[REACT_REQUEST:.*?\]", "", clean_text).strip()

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
    valid_directives = {"answer", "delegate_to_react", "present_results", "ask_for_params", "escalate"}
    if directive not in valid_directives:
        directive = "answer"

    updates = {
        "messages": [AIMessage(content=clean_response)],
        "qa_directive": directive,
        "final_response": clean_response,
    }

    if react_request:
        updates["react_request"] = react_request

    return updates
