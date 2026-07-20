import os
import sys
import uuid
import json
from datetime import datetime, timezone
from dotenv import load_dotenv
from langsmith import evaluate
from langchain_core.messages import HumanMessage, AIMessage

# Ensure the backend directory is in the import path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# Load environment variables from .env
load_dotenv(os.path.join(backend_dir, ".env"))

from core_agent.nuit_bot import NuitBot


def target_bot(inputs: dict) -> dict:
    """Target function for LangSmith evaluation, wrapping NuitBot.

    Parses and injects any conversation history before invoking the bot's standard response flow.

    Args:
        inputs: Dictionary containing the input data from the dataset,
                including 'query' (the new message) and 'history' (list of past messages).

    Returns:
        A dictionary containing the bot's generated response in the 'output' key.
    """
    bot = NuitBot()
    # Fresh session ID for each case execution
    session_id = f"eval_{uuid.uuid4().hex[:8]}"
    config = {"configurable": {"thread_id": session_id}}

    # 1. Parse and inject history into LangGraph state
    history_raw = inputs.get("history")
    history_messages = []

    if history_raw:
        # Support string-encoded JSON as well as native lists
        if isinstance(history_raw, str):
            try:
                history_list = json.loads(history_raw)
            except Exception:
                history_list = []
        elif isinstance(history_raw, list):
            history_list = history_raw
        else:
            history_list = []

        for msg in history_list:
            if isinstance(msg, dict):
                role = msg.get("role")
                content = msg.get("content", "")
                if role == "human":
                    history_messages.append(HumanMessage(content=content))
                elif role in ("agent", "ai", "assistant"):
                    history_messages.append(AIMessage(content=content))

    if history_messages:
        # Pre-populate thread checkpointer with the conversation history
        bot.graph.update_state(config, {"messages": history_messages})

    # 2. Query the bot with the new user message
    query = inputs.get("query") or inputs.get("question") or ""
    try:
        response = bot.send_message(query, thread_id=session_id)
        actual_output = response.get("message") or str(response)
    except Exception as e:
        actual_output = f"ERROR: {e}"

    return {"output": actual_output}


def run_evaluation():
    dataset_name = "escalation_scenarios"
    print("=" * 60)
    print(f"  Running LangSmith Evaluation on dataset: '{dataset_name}'")
    print("=" * 60)

    try:
        # Run the evaluation using LangSmith
        experiment_prefix = f"nuit-{8}-{datetime.now(timezone.utc):%Y%m%d%H%M%S}"
        results = evaluate(
            target_bot,
            data=dataset_name,
            experiment_prefix=experiment_prefix,
        )
        print("\n" + "=" * 60)
        print("  Evaluation Run Successfully Initiated / Completed!")
        print("=" * 60)
        print(f"Experiment results summary: {results}")
    except Exception as e:
        print(f"Evaluation failed: {e}")
        print("\nMake sure you have:")
        print(f"1. Created a dataset in LangSmith named '{dataset_name}'.")
        print("2. Uploaded the 'scenarios.csv' to that dataset.")
        print("3. Configured your LANGSMITH_API_KEY inside the '.env' file.")


if __name__ == "__main__":
    run_evaluation()
