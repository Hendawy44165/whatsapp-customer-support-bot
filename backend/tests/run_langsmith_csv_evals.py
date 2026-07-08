import os
import sys
import json
import uuid
from dotenv import load_dotenv
from langsmith import evaluate

# Add backend directory to python import path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

load_dotenv()

from core_agent.nuit_bot import NuitBot

# Dataset name in LangSmith (manually uploaded by you)
DATASET_NAME = "golden_dataset"


def evaluate_target(inputs: dict):
    """Function called by LangSmith for each row in the dataset."""
    bot = NuitBot()
    thread_id = inputs.get("thread_id", str(uuid.uuid4()))

    # Restore history if present
    history_str = inputs.get("history", "[]")
    try:
        history = json.loads(history_str)
    except Exception:
        history = []

    if history:
        from langchain_core.messages import HumanMessage, AIMessage

        history_msgs = []
        for msg in history:
            if msg["role"] == "user":
                history_msgs.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                history_msgs.append(AIMessage(content=msg["content"]))

        bot.graph.update_state(
            {"configurable": {"thread_id": thread_id}}, {"messages": history_msgs}
        )

    # Run the NuitBot
    response = bot.send_message(inputs["message"], thread_id=thread_id)

    return {"response": response}


def main():
    if not os.getenv("LANGSMITH_API_KEY"):
        print(
            "Error: LANGSMITH_API_KEY is not set. Please set it in your env or .env file."
        )
        return

    model_name = os.getenv("PROVIDER_MODEL_NAME", "unknown-model")
    experiment_prefix = f"nuit-bot-correctness-{model_name.replace('/', '-')}"

    print(f"Running LangSmith evaluation against dataset: '{DATASET_NAME}'")
    evaluate(
        evaluate_target,
        data=DATASET_NAME,
        evaluators=[],  # Manual review in LangSmith UI
        experiment_prefix=experiment_prefix,
    )
    print("\nEvaluation run submitted! Check your LangSmith dashboard.")


if __name__ == "__main__":
    main()
