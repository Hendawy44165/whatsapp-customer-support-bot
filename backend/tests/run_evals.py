import os
import sys
import json
import uuid
import csv
from pathlib import Path
from dotenv import load_dotenv
from langsmith import evaluate
from langchain_core.messages import HumanMessage, AIMessage

# Add backend directory to python import path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

load_dotenv()

from core_agent.nuit_bot import NuitBot


def load_scenarios_from_csv(csv_path: str) -> list:
    """Load evaluation scenarios from CSV file."""
    scenarios = []
    csv_path = Path(csv_path)

    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            history_str = row.get("history", "[]")
            try:
                history = json.loads(history_str)
            except json.JSONDecodeError:
                history = []

            scenarios.append(
                {
                    "scenario_id": row.get("scenario_id", "").strip(),
                    "turn_number": int(row.get("turn_number", 1)),
                    "user_message": row.get("user_message", "").strip(),
                    "history": history,
                    "output_reference": row.get("output_reference", "").strip(),
                }
            )

    return scenarios


def evaluate_target(inputs: dict) -> dict:
    """Runs the bot with history population."""
    bot = NuitBot()
    thread_id = inputs.get("thread_id", str(uuid.uuid4()))

    # Parse and populate history
    history_list = inputs.get("history", [])
    if isinstance(history_list, str):
        try:
            history_list = json.loads(history_list)
        except json.JSONDecodeError:
            history_list = []

    if history_list:
        history_msgs = []
        for msg in history_list:
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

    # Invoke agent with current message
    user_message = inputs.get("user_message", "")
    response = bot.send_message(user_message, thread_id=thread_id)

    return {"response": response}


def main():
    """Main entry point."""
    if not os.getenv("LANGSMITH_API_KEY"):
        raise RuntimeError("LANGSMITH_API_KEY not set in environment")

    # Load scenarios
    tests_dir = Path(__file__).parent
    csv_path = tests_dir / "scenarios.csv"
    scenarios = load_scenarios_from_csv(str(csv_path))

    print(f"\n{'='*60}")
    print("NuitBot LangSmith Evaluation")
    print(f"{'='*60}")
    print(f"Loaded {len(scenarios)} scenario(s)\n")

    for scenario in scenarios:
        print(
            f"  - {scenario['scenario_id']} (Turn {scenario['turn_number']}, History: {len(scenario['history'])} msgs)"
        )
    print()

    # Get dataset name and model name
    dataset_name = "golden_dataset"
    model_name = os.getenv("PROVIDER_MODEL_NAME", "unknown-model")
    experiment_prefix = f"nuit-bot-correctness-{model_name.replace('/', '-')}"

    # Run evaluation
    print(f"Starting evaluation against dataset: {dataset_name}\n")

    evaluate(
        evaluate_target,
        data=dataset_name,
        evaluators=[],
        experiment_prefix=experiment_prefix,
    )

    print("\n✓ Evaluation submitted to LangSmith!")


if __name__ == "__main__":
    main()
