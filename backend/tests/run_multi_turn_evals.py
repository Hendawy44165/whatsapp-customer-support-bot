import os
import sys
import uuid
import json
import re
from typing import List, Dict, Any, Optional, Callable
from dotenv import load_dotenv

# Add backend directory to python import path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

load_dotenv()

from core_agent.nuit_bot import NuitBot
from core_agent.config import get_model
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage, AIMessage

# Define ANSI colors for terminal output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"


class Turn:
    def __init__(
        self,
        user_input: str,
        expected_tool: Optional[str] = None,
        expected_tool_status: Optional[str] = None,
        expected_missing_param: Optional[str] = None,
        judge_criteria: str = "",
    ):
        self.user_input = user_input
        self.expected_tool = expected_tool
        self.expected_tool_status = expected_tool_status
        self.expected_missing_param = expected_missing_param
        self.judge_criteria = judge_criteria


class TestCase:
    def __init__(self, id: str, name: str, description: str, turns: List[Turn]):
        self.id = id
        self.name = name
        self.description = description
        self.turns = turns


def run_llm_judge(model, history_msgs: List[Any], user_input: str, bot_response: str, criteria: str) -> dict:
    """
    Evaluates a single turn of the bot response using an LLM-as-a-judge.
    Attempts to use structured output, with text completion fallback.
    """
    history_str = ""
    for msg in history_msgs:
        role = "User" if isinstance(msg, HumanMessage) else "Bot"
        history_str += f"{role}: {msg.content}\n"

    prompt = f"""You are an objective AI evaluator grading a customer support bot's performance.

Evaluate the following turn of a conversation between a User and the Support Bot.

### Conversation History:
{history_str}

### Current Turn:
User: {user_input}
Bot: {bot_response}

### Grading Criteria for this Turn:
{criteria}

Determine if the Bot's response satisfies the Grading Criteria.
Consider the following:
1. Did the bot follow the specific instructions in the criteria?
2. Did the bot maintain a professional, polite customer service tone?
3. Did the bot avoid sharing raw technical errors, internal variables, or code-like output?

Return your evaluation ONLY as a JSON object with two fields:
{{
  "passed": true,
  "reason": "Detailed explanation referencing the criteria and the bot's response."
}}
Do not include any Markdown styling (such as ```json) or extra text outside the JSON object.
"""

    try:
        from pydantic import BaseModel, Field

        class JudgeVerdict(BaseModel):
            passed: bool = Field(description="True if the response passed, False otherwise")
            reason: str = Field(description="Reasoning behind the pass/fail decision")

        try:
            # Attempt to use structured output
            structured_model = model.with_structured_output(JudgeVerdict)
            verdict = structured_model.invoke([HumanMessage(content=prompt)])
            return {"passed": verdict.passed, "reason": verdict.reason}
        except Exception:
            # Fallback to standard text invocation and manual parsing
            resp = model.invoke([HumanMessage(content=prompt)])
            text = resp.content.strip()
            # Remove potential code fences
            if text.startswith("```"):
                text = re.sub(r"^```(?:json)?\n", "", text)
                text = re.sub(r"\n```$", "", text)
            data = json.loads(text.strip())
            return {"passed": bool(data.get("passed")), "reason": str(data.get("reason", ""))}
    except Exception as e:
        return {"passed": False, "reason": f"Judge invocation or parsing failed: {str(e)}"}


def check_tool_invocation(new_messages: List[Any], expected_tool: Optional[str], expected_status: Optional[str]) -> tuple[bool, str]:
    """Check if the expected tool was called (or not called) and if status matches."""
    tool_msgs = [
        msg for msg in new_messages 
        if isinstance(msg, ToolMessage) or msg.type == "tool" or msg.__class__.__name__ == "ToolMessage"
    ]

    if expected_tool is None:
        if tool_msgs:
            called = [getattr(m, "name", None) or getattr(m, "additional_kwargs", {}).get("name", "unknown") for m in tool_msgs]
            return False, f"Expected NO tool calls, but tool(s) {called} were called."
        return True, "No tools were called (as expected)."

    if not tool_msgs:
        return False, f"Expected tool '{expected_tool}' to be called, but no tools were called."

    # Look for the expected tool call
    matching_msg = None
    for msg in tool_msgs:
        name = getattr(msg, "name", None) or getattr(msg, "additional_kwargs", {}).get("name", None)
        if name == expected_tool:
            matching_msg = msg
            break

    if not matching_msg:
        called = [getattr(m, "name", None) or getattr(m, "additional_kwargs", {}).get("name", "unknown") for m in tool_msgs]
        return False, f"Expected tool '{expected_tool}' to be called, but instead {called} were called."

    # Verify status if specified
    if expected_status:
        content = matching_msg.content
        if expected_status not in content:
            return False, f"Expected tool '{expected_tool}' status to contain '{expected_status}', but got: {content}"
        return True, f"Tool '{expected_tool}' called successfully and returned status '{expected_status}'."

    return True, f"Tool '{expected_tool}' called successfully."


def check_missing_param_in_snapshots(new_snapshots: List[Any], expected_param: str) -> tuple[bool, str]:
    """Check if the expected missing parameter was recorded in the state history of this turn."""
    for snapshot in new_snapshots:
        missing = snapshot.values.get("missing_params")
        if missing and expected_param in missing:
            return True, f"Missing parameter '{expected_param}' was correctly identified in the agent state."
    return False, f"Expected parameter '{expected_param}' to be identified as missing, but it was not found in state history."


def run_eval_suite():
    bot = NuitBot()
    model = get_model()

    # Define the 3 Multi-Turn Test Cases
    test_cases = [
        TestCase(
            id="happy_path_return_exchange",
            name="Happy Path: Return & Exchange",
            description="Tests a customer successfully registering a return for an eligible order, then registering an exchange on the same order.",
            turns=[
                Turn(
                    user_input="Hi, I want to return my order 3021. The scent wasn't what I expected.",
                    expected_tool="register_return",
                    expected_tool_status="success",
                    judge_criteria="The bot must politely acknowledge the return request for order 3021, confirm that it has been successfully registered, and ask if there is anything else it can help with.",
                ),
                Turn(
                    user_input="Can I exchange it for a Born in Milano bottle?",
                    expected_tool="register_exchange",
                    expected_tool_status="success",
                    judge_criteria="The bot must register an exchange for order 3021 with the item 'Born in Milano' and confirm to the customer that the exchange is processed.",
                )
            ]
        ),
        TestCase(
            id="missing_param_clarification",
            name="Missing Parameter: Clarification Loop",
            description="Tests a customer asking to return an item without providing an order ID. The bot must ask for the ID, and then process the return after the ID is supplied.",
            turns=[
                Turn(
                    user_input="Hi, I need to return my perfume.",
                    expected_tool=None,
                    expected_missing_param="order_id",
                    judge_criteria="The bot must recognize the return request but politely ask the user for their order ID before proceeding. It should not make tool calls or fake processing.",
                ),
                Turn(
                    user_input="My order ID is 3021.",
                    expected_tool="register_return",
                    expected_tool_status="success",
                    judge_criteria="Having received the order ID 3021, the bot must process the return and politely confirm that the return has been registered.",
                )
            ]
        ),
        TestCase(
            id="policy_failure_handling",
            name="Policy Failure: Ineligible Return",
            description="Tests a customer trying to return order 4022, which is ineligible. The bot must capture the tool failure and explain the policy failure politely without crashing.",
            turns=[
                Turn(
                    user_input="Hello, I want to return my order 4022. It is too strong for me.",
                    expected_tool="register_return",
                    expected_tool_status="failed",
                    judge_criteria="The bot must attempt to register the return, receive the ineligible failure from the database, and politely explain that order 4022 is not eligible for return. It must not expose technical database details, traceback text, or crash.",
                )
            ]
        ),
    ]

    print(f"\n{BOLD}{CYAN}===================================================================={RESET}")
    print(f"{BOLD}{CYAN}             NUIT BOT MULTI-TURN EVALUATION RUNNER{RESET}")
    print(f"{BOLD}{CYAN}===================================================================={RESET}\n")

    report_details = []
    suite_passed = True

    for tc in test_cases:
        print(f"{BOLD}Running Scenario: {tc.name} ({tc.id}){RESET}")
        print(f"Description: {tc.description}")
        print("-" * 60)

        thread_id = f"eval-thread-{uuid.uuid4()}"
        config = {"configurable": {"thread_id": thread_id}}
        
        tc_passed = True
        tc_turns_log = []

        for idx, turn in enumerate(tc.turns):
            turn_num = idx + 1
            print(f"  {BOLD}Turn {turn_num}:{RESET} User: '{turn.user_input}'")

            # Get state/message count before invocation
            state_before = bot.graph.get_state(config)
            initial_msg_count = len(state_before.values.get("messages", [])) if state_before else 0
            initial_snapshots_count = len(list(bot.graph.get_state_history(config)))

            # Run message through NuitBot
            try:
                response = bot.send_message(turn.user_input, thread_id=thread_id)
            except Exception as e:
                print(f"  {RED}✖ Bot execution crashed: {str(e)}{RESET}\n")
                tc_passed = False
                tc_turns_log.append({
                    "turn": turn_num,
                    "user_input": turn.user_input,
                    "bot_response": "CRASHED",
                    "state_delta_ok": False,
                    "state_delta_reason": f"Execution crashed: {str(e)}",
                    "judge_ok": False,
                    "judge_reason": "Bot crashed during execution."
                })
                break

            print(f"  Bot: '{response}'")

            # Extract new messages & snapshots
            state_after = bot.graph.get_state(config)
            updated_messages = state_after.values.get("messages", []) if state_after else []
            new_messages = updated_messages[initial_msg_count:]

            all_snapshots = list(bot.graph.get_state_history(config))
            new_snapshots_count = len(all_snapshots) - initial_snapshots_count
            new_snapshots = all_snapshots[:new_snapshots_count]

            # 1. State-Delta Check: Tool execution
            tool_ok, tool_reason = check_tool_invocation(new_messages, turn.expected_tool, turn.expected_tool_status)
            
            # 2. State-Delta Check: Missing params (if specified)
            param_ok = True
            param_reason = ""
            if turn.expected_missing_param:
                param_ok, param_reason = check_missing_param_in_snapshots(new_snapshots, turn.expected_missing_param)

            state_delta_ok = tool_ok and param_ok
            state_delta_reason = tool_reason + (" " + param_reason if param_reason else "")

            if state_delta_ok:
                print(f"    {GREEN}✔ State-Delta Check Passed:{RESET} {state_delta_reason}")
            else:
                print(f"    {RED}✖ State-Delta Check Failed:{RESET} {state_delta_reason}")

            # 3. LLM Judge Check
            # Provide the judge with the history prior to this turn
            history_msgs = updated_messages[:initial_msg_count]
            print(f"    Evaluating response with LLM Judge...")
            judge_res = run_llm_judge(model, history_msgs, turn.user_input, response, turn.judge_criteria)

            if judge_res["passed"]:
                print(f"    {GREEN}✔ LLM Judge Passed:{RESET} {judge_res['reason']}")
            else:
                print(f"    {RED}✖ LLM Judge Failed:{RESET} {judge_res['reason']}")

            turn_passed = state_delta_ok and judge_res["passed"]
            if not turn_passed:
                tc_passed = False

            tc_turns_log.append({
                "turn": turn_num,
                "user_input": turn.user_input,
                "bot_response": response,
                "state_delta_ok": state_delta_ok,
                "state_delta_reason": state_delta_reason,
                "judge_ok": judge_res["passed"],
                "judge_reason": judge_res["reason"]
            })
            print()

        if tc_passed:
            print(f"{GREEN}{BOLD}Scenario Result: PASSED{RESET}\n")
        else:
            print(f"{RED}{BOLD}Scenario Result: FAILED{RESET}\n")
            suite_passed = False

        report_details.append({
            "id": tc.id,
            "name": tc.name,
            "description": tc.description,
            "passed": tc_passed,
            "turns": tc_turns_log
        })

    # Generate Markdown Reports
    write_markdown_reports(report_details, suite_passed)

    print(f"{BOLD}===================================================================={RESET}")
    print(f"EVALUATION COMPLETE. Overall Suite Status: " + (f"{GREEN}{BOLD}PASSED{RESET}" if suite_passed else f"{RED}{BOLD}FAILED{RESET}"))
    print(f"Detailed reports have been written to:")
    print(f"  - Local workspace: {BOLD}backend/tests/eval_report.md{RESET}")
    print(f"  - Artifact directory: {BOLD}eval_report.md{RESET}")
    print(f"{BOLD}===================================================================={RESET}\n")


def write_markdown_reports(details: List[Dict], suite_passed: bool):
    status_emoji = "✅" if suite_passed else "❌"
    status_text = "PASSED" if suite_passed else "FAILED"
    
    report_content = f"""# Nuit Bot Multi-Turn Evaluation Report

This report documents the results of running the multi-turn agent evaluation suite for the Nuit Bot.

**Overall Suite Status:** {status_emoji} **{status_text}**

## Summary of Scenarios

| Scenario Name | ID | Status | Turns |
| :--- | :--- | :---: | :---: |
"""
    for tc in details:
        emoji = "✅" if tc["passed"] else "❌"
        report_content += f"| {tc['name']} | `{tc['id']}` | {emoji} | {len(tc['turns'])} |\n"

    report_content += "\n## Detailed Scenario Results\n\n"

    for tc in details:
        tc_emoji = "✅" if tc["passed"] else "❌"
        report_content += f"### {tc_emoji} {tc['name']} (`{tc['id']}`)\n"
        report_content += f"**Description:** {tc['description']}\n\n"
        
        for turn in tc["turns"]:
            report_content += f"#### Turn {turn['turn']}\n"
            report_content += f"- **User Input:** *\"{turn['user_input']}\"*\n"
            report_content += f"- **Bot Response:** *\"{turn['bot_response']}\"*\n"
            
            delta_emoji = "✅" if turn["state_delta_ok"] else "❌"
            report_content += f"- **State-Delta Validation:** {delta_emoji} {turn['state_delta_reason']}\n"
            
            judge_emoji = "✅" if turn["judge_ok"] else "❌"
            report_content += f"- **LLM Judge Evaluation:** {judge_emoji} {turn['judge_reason']}\n\n"
        
        report_content += "---\n\n"

    # Write locally to workspace
    local_report_path = os.path.join(backend_dir, "tests", "eval_report.md")
    with open(local_report_path, "w", encoding="utf-8") as f:
        f.write(report_content)

    # Write to App Data Artifact path
    artifact_report_path = "/home/hendawy/.gemini/antigravity/brain/08da9305-220f-4dec-915c-f7e0a0442088/multi_turn_eval_report.md"
    try:
        with open(artifact_report_path, "w", encoding="utf-8") as f:
            f.write(report_content)
    except Exception as e:
        print(f"Failed to write artifact report: {str(e)}")


if __name__ == "__main__":
    run_eval_suite()
