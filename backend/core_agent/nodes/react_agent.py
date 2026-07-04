"""
ReAct agent node — handles CRM operations with tool calling.
Uses a reasoning-first approach: plan → check params → call tools → return result.
"""

import re
import json
from typing import Dict
from langchain_core.messages import SystemMessage, ToolMessage
from langsmith import traceable

from ..state import AgentState, ReactResult
from ..config import get_model, load_prompt
from ..tools import lookup_order, register_return, register_exchange


# Tools available to the ReAct agent
REACT_TOOLS = [lookup_order, register_return, register_exchange]
REACT_TOOLS_BY_NAME = {t.name: t for t in REACT_TOOLS}


def _extract_missing_params(text: str) -> list[str]:
    """
    Extract missing parameter names from the agent's response.
    Looks for the pattern: [MISSING: param1, param2]
    """
    match = re.search(r"\[MISSING:\s*(.+?)\]", text, re.IGNORECASE)
    if match:
        params_str = match.group(1)
        return [p.strip() for p in params_str.split(",") if p.strip()]

    # Fallback: look for common parameter names mentioned as needed
    missing = []
    text_lower = text.lower()
    if "order" in text_lower and ("id" in text_lower or "number" in text_lower):
        if "need" in text_lower or "provide" in text_lower or "missing" in text_lower:
            missing.append("order_id")
    if "phone" in text_lower:
        if "need" in text_lower or "provide" in text_lower or "missing" in text_lower:
            missing.append("phone")

    return missing if missing else ["additional information"]


@traceable(name="react_agent_node")
def react_agent_node(state: AgentState) -> Dict:
    """
    Executes CRM operations using tool calling.

    Flow:
    1. Receives task from QA via react_request
    2. Plans what tools to call
    3. If params missing → returns need_info with missing_params
    4. If params present → calls tool → returns success/failed with result
    """
    model = get_model()
    system_prompt = load_prompt("react_agent.md")

    # Build the task context
    react_request = state.get("react_request", "")
    task_section = f"\n\n# CURRENT TASK\n{react_request}" if react_request else ""

    full_system = system_prompt + task_section

    # Build message list: system prompt + conversation history
    messages = state.get("messages", [])
    llm_messages = [SystemMessage(content=full_system)] + list(messages)

    # Bind tools to model
    model_with_tools = model.bind_tools(REACT_TOOLS)

    # Tool calling loop (max 3 steps to prevent runaway)
    tool_results = []
    reasoning_parts = []
    max_steps = 3
    active_messages = list(llm_messages)

    for step in range(max_steps):
        response = model_with_tools.invoke(active_messages)

        # Capture any reasoning text
        if response.content:
            reasoning_parts.append(response.content)

        if not response.tool_calls:
            # Agent decided NOT to call tools — means it needs more info or is done
            break

        # Process tool calls
        active_messages.append(response)

        for tool_call in response.tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]
            tool_fn = REACT_TOOLS_BY_NAME.get(tool_name)

            if tool_fn is None:
                tool_result_str = json.dumps({
                    "status": "error",
                    "message": f"Unknown tool: {tool_name}",
                })
            else:
                try:
                    tool_result_str = tool_fn.invoke(tool_args)
                except Exception as e:
                    tool_result_str = json.dumps({
                        "status": "error",
                        "message": f"Tool execution error: {str(e)}",
                    })

            # Parse the result
            try:
                parsed = json.loads(tool_result_str)
            except json.JSONDecodeError:
                parsed = {"status": "error", "message": tool_result_str}

            tool_results.append({
                "tool": tool_name,
                "args": tool_args,
                "result": parsed,
            })

            # Add tool message for the next iteration
            active_messages.append(
                ToolMessage(content=tool_result_str, tool_call_id=tool_call["id"])
            )

    # Compile reasoning
    reasoning = "\n".join(reasoning_parts) if reasoning_parts else "No reasoning output captured."

    # Determine the ReactResult based on what happened
    current_count = state.get("react_turn_count", 0) + 1

    if tool_results:
        # Tools were called — check outcomes
        successes = [r for r in tool_results if r["result"].get("status") == "success"]
        failures = [r for r in tool_results if r["result"].get("status") != "success"]

        if successes:
            # Use the last successful result as the primary output
            return {
                "react_result": ReactResult(
                    status="success",
                    tool_output=successes[-1]["result"],
                    missing_params=None,
                    reasoning=reasoning,
                    failure_reason=None,
                ),
                "react_turn_count": current_count,
            }
        else:
            # All tools failed
            failure_messages = [
                r["result"].get("message", "Unknown error") for r in failures
            ]
            return {
                "react_result": ReactResult(
                    status="failed",
                    tool_output=failures[-1]["result"] if failures else None,
                    missing_params=None,
                    reasoning=reasoning,
                    failure_reason="; ".join(failure_messages),
                ),
                "react_turn_count": current_count,
            }
    else:
        # No tools called — agent needs more info from the user
        missing = _extract_missing_params(reasoning)
        return {
            "react_result": ReactResult(
                status="need_info",
                tool_output=None,
                missing_params=missing,
                reasoning=reasoning,
                failure_reason=None,
            ),
            "react_turn_count": current_count,
        }
