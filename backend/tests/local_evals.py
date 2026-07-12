import os
import sys
import json
import csv
import uuid
from pathlib import Path
from dotenv import load_dotenv

# Add backend directory to python import path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

load_dotenv()

from core_agent.nuit_bot import NuitBot
from core_agent.config import get_model
from langchain_core.messages import HumanMessage, AIMessage
from langchain.chat_models import init_chat_model
from pydantic import BaseModel, Field
from typing import Optional


class BrandVoiceJudge(BaseModel):
    calm: Optional[bool] = None
    professional: Optional[bool] = None
    premium: Optional[bool] = None
    concise: Optional[bool] = None
    emojis: Optional[bool] = None


class CorrectInfoJudge(BaseModel):
    fully_correct_from_doc: Optional[bool] = None
    revealed_extra_info: Optional[bool] = None


class NeverRevealsStockJudge(BaseModel):
    never_reveals_stock_or_secret: Optional[bool] = None


class SmartRefusalJudge(BaseModel):
    did_it_refuse: Optional[bool] = None
    refuse_with_brand_voice: Optional[bool] = None
    considered_query_absorbed_anger: Optional[bool] = None


class PerfectRoutingJudge(BaseModel):
    did_it_set_urgency: Optional[bool] = None
    did_it_respond_right: Optional[bool] = None
    did_it_mention_routing: Optional[bool] = None


class LLMJudgeResponse(BaseModel):
    brand_voice: Optional[BrandVoiceJudge] = None
    correct_information: Optional[CorrectInfoJudge] = None
    never_reveals_stock_or_secret: Optional[NeverRevealsStockJudge] = None
    smart_refusal: Optional[SmartRefusalJudge] = None
    perfect_ticket_routing: Optional[PerfectRoutingJudge] = None
    reasoning: str = Field(description="Step-by-step reasoning for the assigned criteria scores.")


def load_scenarios(csv_path: str) -> list:
    scenarios = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            history_str = row.get("history", "[]")
            try:
                history = json.loads(history_str)
            except json.JSONDecodeError:
                history = []
            scenarios.append({
                "scenario_id": row.get("scenario_id", "").strip(),
                "turn_number": int(row.get("turn_number", 1)),
                "user_message": row.get("user_message", "").strip(),
                "history": history,
                "output_reference": json.loads(row.get("output_reference", "{}")),
            })
    return scenarios


def run_scenario(bot: NuitBot, scenario: dict) -> str:
    thread_id = str(uuid.uuid4())
    
    # Populate History
    history_msgs = []
    for msg in scenario["history"]:
        role = msg.get("role", "").lower()
        content = msg.get("content", "")
        if role == "user":
            history_msgs.append(HumanMessage(content=content))
        elif role in ["agent", "assistant"]:
            history_msgs.append(AIMessage(content=content))
            
    if history_msgs:
        bot.graph.update_state(
            {"configurable": {"thread_id": thread_id}},
            {"messages": history_msgs},
        )
        
    res = bot.send_message(scenario["user_message"], thread_id=thread_id)
    return res


def evaluate_response_with_judge(judge_model, scenario: dict, bot_response: str) -> LLMJudgeResponse:
    target_criteria = scenario["output_reference"]
    
    prompt = f"""You are an expert AI quality assurance judge evaluating a customer support bot response.
Given the context details, evaluate the bot response against the reference criteria targets.

Reference Criteria to Evaluate (Target Values):
{json.dumps(target_criteria, indent=2)}

Context Details:
- User Message: "{scenario['user_message']}"
- Chat History: {json.dumps(scenario['history'])}
- Bot Response: "{bot_response}"

Instructions:
1. Score only the metrics and sub-categories defined in the Reference Criteria.
2. Set any categories or sub-categories that are NOT in the Reference Criteria to null.
3. Compare the bot response logically against the rules (e.g. no emojis, concise meaning max 2 sentences, matching database details).
"""
    
    # Use init_chat_model or binder to invoke structured response
    # We create a new client mapping structure or bind model
    structured_model = judge_model.with_structured_output(LLMJudgeResponse)
    result = structured_model.invoke(prompt)
    return result


def main():
    tests_dir = Path(__file__).parent
    csv_path = tests_dir / "evaluation_scenarios.csv"
    report_path = tests_dir / "evals_report.md"
    
    print("Loading scenarios...")
    scenarios = load_scenarios(str(csv_path))
    bot = NuitBot()
    judge_model = get_model()
    
    results_summary = []
    
    print(f"\nRunning local evaluations for {len(scenarios)} scenarios...")
    for idx, scenario in enumerate(scenarios, start=1):
        s_id = scenario["scenario_id"]
        print(f"\n[{idx}/{len(scenarios)}] Running Scenario: {s_id}")
        
        bot_response = run_scenario(bot, scenario)
        print(f"  Bot Response: {bot_response}")
        
        print("  Invoking LLM Judge...")
        judge_res = evaluate_response_with_judge(judge_model, scenario, bot_response)
        
        # Check agreement
        targets = scenario["output_reference"]
        pass_all = True
        mismatch_details = []
        
        for category, sub_dict in targets.items():
            judge_cat = getattr(judge_res, category, None)
            if not judge_cat:
                pass_all = False
                mismatch_details.append(f"Missing category evaluation: {category}")
                continue
            
            for key, expected_val in sub_dict.items():
                actual_val = getattr(judge_cat, key, None)
                if actual_val != expected_val:
                    pass_all = False
                    mismatch_details.append(f"{category}.{key}: Expected {expected_val}, got {actual_val}")
                    
        results_summary.append({
            "scenario_id": s_id,
            "user_message": scenario["user_message"],
            "bot_response": bot_response,
            "passed": pass_all,
            "mismatch_details": mismatch_details,
            "reasoning": judge_res.reasoning,
            "evaluation": judge_res.dict()
        })
        
        status_str = "SUCCESS (All Criteria Met)" if pass_all else "FAILED"
        print(f"  Status: {status_str}")
        if mismatch_details:
            for detail in mismatch_details:
                print(f"    - {detail}")
                
    # Write report
    print(f"\nWriting evaluation report to {report_path}...")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# NuitBot Local LLM-as-a-Judge Evaluation Report\n\n")
        f.write(f"This report lists the correctness and brand compliance scores generated by evaluating scenario responses using `{os.getenv('PROVIDER_MODEL_NAME')}` as the judge model.\n\n")
        
        # Summary table
        f.write("## Summary Table\n\n")
        f.write("| Scenario ID | Status | Mismatches |\n")
        f.write("| --- | --- | --- |\n")
        for res in results_summary:
            status = "✅ PASS" if res["passed"] else "❌ FAIL"
            mismatches = ", ".join(res["mismatch_details"]) if res["mismatch_details"] else "None"
            f.write(f"| {res['scenario_id']} | {status} | {mismatches} |\n")
        f.write("\n")
        
        # Detailed results
        f.write("## Detailed Scenario Evaluations\n\n")
        for res in results_summary:
            f.write(f"### Scenario: {res['scenario_id']}\n\n")
            f.write(f"**User Message:** `{res['user_message']}`\n\n")
            f.write(f"**Bot Response:**\n> {res['bot_response']}\n\n")
            f.write(f"**Judge Reasoning:**\n{res['reasoning']}\n\n")
            f.write("**Evaluation Scores:**\n```json\n" + json.dumps(res["evaluation"], indent=2) + "\n```\n\n")
            f.write("---\n\n")
            
    print("✓ Local evaluations complete!")


if __name__ == "__main__":
    main()
