import os
from langsmith import Client

def main():
    # Initialize LangSmith client
    # Needs LANGSMITH_API_KEY to be set in environment
    if not os.getenv("LANGSMITH_API_KEY"):
        print("Error: LANGSMITH_API_KEY is not set. Please set it in your environment or .env file.")
        return

    client = Client()
    
    dataset_name = "nuit_bot_golden_dataset"
    
    # Delete existing dataset to allow clean re-runs/iterations
    if client.has_dataset(dataset_name=dataset_name):
        client.delete_dataset(dataset_name=dataset_name)
        print(f"Deleted existing dataset: {dataset_name}")
        
    dataset = client.create_dataset(
        dataset_name=dataset_name,
        description="Golden dataset for Nuit Bot v2 evaluating routing, tool calling, and responses.",
    )
    
    # 8 diverse examples covering blocker, qa, react parameter collection,
    # success/failure tool execution, and high urgency human handoffs.
    examples = [
        {
            "inputs": {
                "message": "Hey, can you recommend a good restaurant in Cairo?",
                "thread_id": "test_blocker_restaurant"
            },
            "outputs": {
                "expected_node": "blocker",
                "expected_tool": None,
                "expected_status": None,
                "response_contains": "concierge and can only assist with questions about our fragrances"
            }
        },
        {
            "inputs": {
                "message": "What fragrances do you have in the Flagship 50ml collection?",
                "thread_id": "test_qa_catalog"
            },
            "outputs": {
                "expected_node": "qa",
                "expected_tool": "query_products",
                "expected_status": None,
                "response_contains": "Rum"
            }
        },
        {
            "inputs": {
                "message": "What is your return policy?",
                "thread_id": "test_qa_faq"
            },
            "outputs": {
                "expected_node": "qa",
                "expected_tool": None,
                "expected_status": None,
                "response_contains": "14"
            }
        },
        {
            "inputs": {
                "message": "I want to track my order please.",
                "thread_id": "test_react_missing_params"
            },
            "outputs": {
                "expected_node": "qa", # QA presents the final question to user
                "expected_tool": None, # Executor did not invoke tool
                "expected_status": "need_info", # ReAct result status
                "response_contains": "order ID"
            }
        },
        {
            "inputs": {
                "message": "Can you check my order 3021? My phone is 01023456789.",
                "thread_id": "test_react_success"
            },
            "outputs": {
                "expected_node": "qa",
                "expected_tool": "lookup_order",
                "expected_status": "success",
                "response_contains": "Ahmed Hassan"
            }
        },
        {
            "inputs": {
                "message": "I want to return order 3021, the scent wasn't what I expected.",
                "thread_id": "test_react_return_success"
            },
            "outputs": {
                "expected_node": "qa",
                "expected_tool": "register_return",
                "expected_status": "success",
                "response_contains": "return"
            }
        },
        {
            "inputs": {
                "message": "I want to return order 4022.",
                "thread_id": "test_react_return_fail"
            },
            "outputs": {
                "expected_node": "qa",
                "expected_tool": "register_return",
                "expected_status": "failed",
                "response_contains": "not eligible"
            }
        },
        {
            "inputs": {
                "message": "This is the worst service ever! I want to talk to a human right now! You guys are thieves!",
                "thread_id": "test_escalation_anger"
            },
            "outputs": {
                "expected_node": "escalation",
                "expected_tool": None,
                "expected_status": None,
                "response_contains": "connecting you directly with a specialist"
            }
        }
    ]
    
    # Upload examples
    for ex in examples:
        client.create_example(
            inputs=ex["inputs"],
            outputs=ex["outputs"],
            dataset_id=dataset.id
        )
        
    print(f"Successfully uploaded {len(examples)} examples to dataset '{dataset_name}'.")

if __name__ == "__main__":
    main()
