import os
import sys
import uuid
from dotenv import load_dotenv
from langsmith import evaluate, Client

# Add backend directory to python import path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

load_dotenv()

from core_agent.graph import NuitBot

# Define multiple models to compare (all available for free on GitHub Models API)
MODELS_TO_TEST = [
    "openai/gpt-4.1-mini",            # Default model
    "meta-llama-3-70b-instruct",       # Meta Llama 70B
    "cohere-command-r-plus"            # Cohere Command R+
]


# ---------------------------------------------------------------------------
# Custom Programmatic Evaluators
# ---------------------------------------------------------------------------

def route_evaluator(run, example) -> dict:
    """Evaluate whether the agent graph visited the expected node."""
    outputs = run.outputs
    reference = example.outputs
    
    expected_node = reference.get("expected_node")
    visited_nodes = outputs.get("visited_nodes", [])
    
    score = 1 if expected_node in visited_nodes else 0
    return {
        "key": "correct_route",
        "score": score,
        "comment": f"Expected node: {expected_node}. Visited nodes: {visited_nodes}"
    }


def tool_evaluator(run, example) -> dict:
    """Evaluate whether the agent executed the correct tool action."""
    outputs = run.outputs
    reference = example.outputs
    
    expected_tool = reference.get("expected_tool")
    if not expected_tool:
        return {"key": "correct_tool", "score": 1, "comment": "No tool expected."}
        
    react_result = outputs.get("react_result")
    score = 0
    comment = "Tool call mismatch."
    
    # QA Node tool
    if expected_tool == "query_products":
        response = outputs.get("response", "")
        # Catalog search outputs product variants/examples
        if "rum" in response.lower() or "price" in response.lower():
            score = 1
            comment = "Successfully queried and presented catalog items."
    
    # ReAct Node tools
    elif react_result:
        tool_output = getattr(react_result, "tool_output", None) or react_result.get("tool_output")
        if tool_output:
            tx_type = tool_output.get("transaction_type")
            if expected_tool == "lookup_order" and "data" in tool_output:
                score = 1
                comment = "Successfully retrieved order profile."
            elif expected_tool == tx_type:
                score = 1
                comment = f"Successfully registered transaction: {tx_type}."
                
    return {
        "key": "correct_tool",
        "score": score,
        "comment": comment
    }


def response_evaluator(run, example) -> dict:
    """Evaluate whether the user-facing response matches the expected keyword/context."""
    outputs = run.outputs
    reference = example.outputs
    
    response = outputs.get("response", "")
    contains_keyword = reference.get("response_contains")
    
    if not contains_keyword:
        return {"key": "response_correctness", "score": 1, "comment": "No keyword check required."}
        
    score = 1 if contains_keyword.lower() in response.lower() else 0
    return {
        "key": "response_correctness",
        "score": score,
        "comment": f"Checked response for '{contains_keyword}'. Found match: {score == 1}"
    }


# ---------------------------------------------------------------------------
# Runner Execution
# ---------------------------------------------------------------------------

def run_evaluations_for_model(model_name: str):
    """Run evaluation dataset for a specific model name."""
    print(f"\n=======================================================")
    print(f" Starting Evaluation for Model: {model_name}")
    print(f"=======================================================\n")
    
    # Update environment variable to swap model dynamically
    os.environ["PROVIDER_MODEL_NAME"] = model_name
    
    # Initialize a new bot instance so it loads the updated model
    bot = NuitBot()

    def evaluate_target(inputs: dict):
        thread_id = inputs.get("thread_id", str(uuid.uuid4()))
        
        # 1. Pre-populate conversation history if present (multi-turn testing)
        if "history" in inputs:
            from langchain_core.messages import HumanMessage, AIMessage
            history_msgs = []
            for msg in inputs["history"]:
                if msg["role"] == "user":
                    history_msgs.append(HumanMessage(content=msg["content"]))
                elif msg["role"] == "assistant":
                    history_msgs.append(AIMessage(content=msg["content"]))
            bot.graph.update_state(
                {"configurable": {"thread_id": thread_id}},
                {"messages": history_msgs}
            )
            
        # 2. Invoke the agent graph
        response = bot.send_message(inputs["message"], thread_id=thread_id)
        
        # 3. Retrieve final state variables
        state = bot.get_thread_state(thread_id)
        
        # 4. Extract all visited nodes from the graph checkpointer history
        config = {"configurable": {"thread_id": thread_id}}
        state_history = list(bot.graph.get_state_history(config))
        visited_nodes = []
        for check in reversed(state_history):
            if check.metadata and "source" in check.metadata:
                source = check.metadata.get("source")
                if source and source not in ("__start__", "__entry__") and source not in visited_nodes:
                    visited_nodes.append(source)
                    
        return {
            "response": response,
            "visited_nodes": visited_nodes,
            "router_output": state.get("router_output"),
            "react_result": state.get("react_result"),
            "escalation_report": state.get("escalation_report"),
        }

    # Execute LangSmith evaluator
    experiment_name = f"nuit-bot-{model_name.replace('/', '-')}"
    evaluate(
        evaluate_target,
        data="nuit_bot_golden_dataset",
        evaluators=[route_evaluator, tool_evaluator, response_evaluator],
        experiment_prefix=experiment_name
    )


def main():
    if not os.getenv("LANGSMITH_API_KEY"):
        print("Error: LANGSMITH_API_KEY is not set. Please set it to enable LangSmith tracking.")
        return

    # Loop through each model to perform side-by-side evaluations
    for model in MODELS_TO_TEST:
        run_evaluations_for_model(model)
        
    print("\nAll evaluations complete! Please open your LangSmith dashboard to see results.")


if __name__ == "__main__":
    main()
