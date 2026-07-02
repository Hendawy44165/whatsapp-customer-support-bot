import os
import sys
import json
import time
import shutil
import datetime
from dotenv import load_dotenv
import pandas as pd

# Configure path BEFORE importing local modules
_HERE = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.abspath(os.path.join(_HERE, "..", "..", ".."))
sys.path.append(backend_dir)

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.graph import StateGraph, END
from core_agent.state import AgentState, RouterDecision, ReactState
from core_agent.utils import DocumentAndPromptLoader
from core_agent.nodes.qa_agent import QAAgentNode


class MockAgent:
    """
    A lightweight mock CustomerServiceAgent orchestrator.
    Passes self to nodes so they can access loaders and models.
    """
    def __init__(self, model, loader):
        self.model = model
        self.loader = loader

def convert_to_langchain_messages(chat_history):
    messages = []
    for msg in chat_history:
        role = msg.get("role")
        content = msg.get("content")
        if role == "user":
            messages.append(HumanMessage(content=content))
        elif role == "assistant":
            messages.append(AIMessage(content=content))
    return messages

def make_test_graph(qa_node, loader):
    workflow = StateGraph(AgentState)
    
    # Mock / RAG Node
    def mock_and_rag_node(state: AgentState) -> dict:
        # 1. Retrieve query from messages history
        messages = state.get("messages", [])
        user_input = messages[-1].content
                
        # 2. Append actual RAG of the system to get the relevant data
        rag_output = loader.retrieve_context(user_input) if user_input else ""
        
        return {
            "rag_output": rag_output
        }
        
    workflow.add_node("mock_and_rag", mock_and_rag_node)
    workflow.add_node("qa", qa_node)
    
    workflow.set_entry_point("mock_and_rag")
    workflow.add_edge("mock_and_rag", "qa")
    workflow.add_edge("qa", END)
    
    return workflow.compile()

def find_paths() -> dict:
    """
    Finds and resolves all required directories and files for testing.
    """
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = os.path.join(_HERE, "run", timestamp)
    
    return {
        "scenarios_json_path": os.path.join(_HERE, "rag_usage_scenarios.json"),
        "qa_prompt_path": os.path.join(_HERE, "qa_agent_system_prompt.md"),
        "run_dir": run_dir,
        "scenarios_path": os.path.join(run_dir, "rag_usage_scenarios.json"),
        "prompt_path": os.path.join(run_dir, "qa_agent.md"),
        "results_csv_path": os.path.join(run_dir, "results.csv"),
        "manual_audit_path": os.path.join(run_dir, "audit.md"),
        "local_qa_agent_md": os.path.join(_HERE, "qa_agent.md")
    }

def copy_test_resources(paths: dict):
    """
    Copies test prompt and scenario files to their run and local destination directories.
    """
    os.makedirs(paths["run_dir"], exist_ok=True)
    shutil.copy2(paths["scenarios_json_path"], paths["scenarios_path"])
    shutil.copy2(paths["qa_prompt_path"], paths["prompt_path"])
    shutil.copy2(paths["qa_prompt_path"], paths["local_qa_agent_md"])

def setup_environment() -> dict:
    """
    Loads environment config, then builds and returns model, loader, and model name.
    """
    load_dotenv(dotenv_path=os.path.join(backend_dir, ".env"))
    api_key = os.getenv("PROVIDER_API_KEY")
    base_url = os.getenv("PROVIDER_BASE_URL")
    model_name = os.getenv("PROVIDER_MODEL_NAME")
    
    model = ChatOpenAI(
        api_key=api_key,
        base_url=base_url,
        model=model_name,
        temperature=0.0,
        max_retries=1
    )
    
    loader = DocumentAndPromptLoader(
        docs_dir=os.path.join(backend_dir, "core_agent", "docs"),
        prompts_dir=_HERE
    )
    
    return {
        "model": model,
        "loader": loader,
        "model_name": model_name
    }

def main():
    # 1. Resolve paths and copy files
    paths = find_paths()
    copy_test_resources(paths)
        
    # 2. Setup components and environment
    env = setup_environment()
    model = env["model"]
    loader = env["loader"]
    model_name = env["model_name"]
    
    # 3. Load Scenarios
    with open(paths["scenarios_json_path"], "r", encoding="utf-8") as f:
        scenarios = json.load(f)
    
    # 4. Compile the Agent Node and StateGraph
    agent = MockAgent(model, loader)
    qa_node = QAAgentNode(agent)
    graph = make_test_graph(qa_node, loader)
    
    results = []
    
    # 5. Run Scenarios
    print(f"\nStarting QA Agent Test Suite ({len(scenarios)} Scenarios)...")
    for index, scenario in enumerate(scenarios, 1):
        scenario_id = scenario.get("id")
        desc = scenario.get("description", f"Scenario {scenario_id}")
        user_input = scenario.get("user_input")
        chat_history = scenario.get("chat_history", [])
        
        print(f"Running [{index}/{len(scenarios)}] Scenario ID {scenario_id}: {desc}... ", end="", flush=True)
        
        # Convert history and append the latest user message
        messages = convert_to_langchain_messages(chat_history)
        if user_input:
            if not messages or messages[-1].content != user_input:
                messages.append(HumanMessage(content=user_input))
                
        # Prepare initial state
        initial_state: AgentState = {
            "messages": messages,
            "learned_user_info": scenario.get("learned_user_info", {}),
            "router_decision": RouterDecision(
                next_agent="qa",
                emotion=scenario.get("emotion", "neutral"),
                classification=scenario.get("classification", "General Inquery")
            ),
            "react_state": ReactState(
                missing_customer_data=scenario.get("missing_customer_data", []),
                query_rationale="",
                output=scenario.get("react_output", {}),
                status_code=scenario.get("react_status_code", "not_triggered")
            ),
            "process_state": "idle",
            "rag_output": ""
        }
        
        # Invoke Graph
        final_state = None
        start_time = time.time()
        try:
            final_state = graph.invoke(initial_state)
            
            # Extract response (last AI message in messages history)
            response_messages = final_state.get("messages", [])
            agent_output = ""
            for m in reversed(response_messages):
                if m.type == "ai":
                    agent_output = m.content
                    break
                    
            final_process_state = final_state.get("process_state", "idle")
            duration = time.time() - start_time
            print(f"DONE (process_state: {final_process_state})")
        except Exception as e:
            agent_output = f"ERROR: Execution failed: {str(e)}"
            final_process_state = "failed"
            print("FAILED")
            
        # Format the entire chat history (including the latest user input at the bottom) for CSV
        history_text = "\n".join([f"{'USER' if m.type == 'human' else 'ASSISTANT'}: {m.content}" for m in messages])
        
        # Save to list
        results.append({
            "ID": scenario_id,
            "Model": model_name,
            "Chat_History": history_text,
            "RAG_Context": final_state.get("rag_output", "") if final_state else "",
            "Final_Process_State": final_process_state,
            "Agent_Output": agent_output,
        })
        
    # 6. Save Results to CSV
    df = pd.DataFrame(results)
    df.to_csv(paths["results_csv_path"], index=False)
    
    # 7. Write Empty Audit File
    with open(paths["manual_audit_path"], "w", encoding="utf-8") as f:
        f.write("")
            
    print(f"\nTest execution complete.")
    print(f"Results CSV: {paths['results_csv_path']}")
    print(f"Audit File: {paths['manual_audit_path']}\n")

if __name__ == "__main__":
    main()
