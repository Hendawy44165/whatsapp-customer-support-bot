import os
import sys
import json
import time
import shutil
import datetime
from dotenv import load_dotenv
import pandas as pd

# LangChain Imports
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage

# Local imports
_HERE = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(_HERE)
sys.path.append(backend_dir)

from core_agent.state import AgentState
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

def main():
    # 1. Load Environment Config
    load_dotenv(dotenv_path=os.path.join(backend_dir, ".env"))
    api_key = os.getenv("PROVIDER_API_KEY")
    base_url = os.getenv("PROVIDER_BASE_URL")
    model_name = os.getenv("PROVIDER_MODEL_NAME")
    
    if not api_key:
        print("Error: PROVIDER_API_KEY environment variable is missing.")
        sys.exit(1)
        
    # 2. Setup Timestamped Run Directory
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = os.path.join(_HERE, "runs", "qa_agent", timestamp)
    os.makedirs(run_dir, exist_ok=True)
    
    # Paths for snapshot files
    scenarios_json_path = os.path.join(_HERE, "brand_voice_scenarios.json")
    qa_prompt_path = os.path.abspath(os.path.join(backend_dir, "core_agent", "prompts", "qa_agent.md"))
    
    copied_script_path = os.path.join(run_dir, "test_qa_agent.py")
    copied_scenarios_path = os.path.join(run_dir, "brand_voice_scenarios.json")
    copied_prompt_path = os.path.join(run_dir, "qa_agent.md")
    results_csv_path = os.path.join(run_dir, "results.csv")
    manual_audit_path = os.path.join(run_dir, "manual_audit.md")
    
    # Copy source files for reproducibility snapshot
    shutil.copy2(__file__, copied_script_path)
    if os.path.exists(scenarios_json_path):
        shutil.copy2(scenarios_json_path, copied_scenarios_path)
    if os.path.exists(qa_prompt_path):
        shutil.copy2(qa_prompt_path, copied_prompt_path)
        
    # 3. Load Scenarios
    if not os.path.exists(scenarios_json_path):
        print(f"Error: Scenarios file not found at {scenarios_json_path}.")
        sys.exit(1)
        
    with open(scenarios_json_path, "r", encoding="utf-8") as f:
        scenarios = json.load(f)
        
    # 4. Initialize Core Components
    model = ChatOpenAI(
        api_key=api_key,
        base_url=base_url,
        model=model_name,
        temperature=0.0,
        max_retries=1
    )
    
    loader = DocumentAndPromptLoader(
        docs_dir=os.path.join(backend_dir, "core_agent", "docs"),
        prompts_dir=os.path.join(backend_dir, "core_agent", "prompts")
    )
    
    agent = MockAgent(model, loader)
    qa_node = QAAgentNode(agent)
    
    results = []
    
    # 5. Run Scenarios (Terminal Clean Log)
    print(f"\nStarting QA Agent Test Suite ({len(scenarios)} Scenarios)...")
    for index, scenario in enumerate(scenarios, 1):
        scenario_id = scenario.get("id")
        desc = scenario.get("description")
        user_input = scenario.get("user_input")
        chat_history = scenario.get("chat_history", [])
        rag_context = scenario.get("rag_context", "")
        crm_result = scenario.get("crm_result", {})
        qa_mode = scenario.get("qa_mode", "static_faq") # used to simulate the process status
        
        print(f"Running [{index}/{len(scenarios)}] Scenario ID {scenario_id}: {desc}... ", end="", flush=True)
        
        # Translate scenario mode to AgentState variables
        active_process = "WISMO" if qa_mode in ("ask_for_parameters", "present_results") else None
        process_state = "collecting" if qa_mode == "ask_for_parameters" else "completed" if qa_mode == "present_results" else "idle"
        
        # Run real RAG retrieval if it's a general FAQ (no active process)
        if not active_process:
            real_rag = loader.retrieve_context(user_input)
        else:
            real_rag = ""
        
        # Prepare state
        state: AgentState = {
            "messages": convert_to_langchain_messages(chat_history),
            "rag_context": real_rag,
            "active_process": active_process,
            "process_state": process_state,
            "extracted_parameters": {},
            "crm_result": crm_result,
            "escalation_report": {}
        }


        
        # Invoke Node
        start_time = time.time()
        try:
            node_output = qa_node(state)
            agent_output = node_output.get("response", "")
            duration = time.time() - start_time
            print("DONE")
        except Exception as e:
            agent_output = f"ERROR: Execution failed: {str(e)}"
            print("FAILED")
            
        # Format chat history for readable display in CSV
        history_text = "\n".join([f"{m['role'].upper()}: {m['content']}" for m in chat_history])
        
        # Save to list
        results.append({
            "ID": scenario_id,
            "Model": model_name,
            "User_Input": user_input,
            "Chat_History": history_text,
            "RAG_Context": real_rag,
            "Uploaded_File": "None",
            "Agent_Output": agent_output,
            "Audit_Status": "", # Left blank for user audit
            "Audit_Notes": ""   # Left blank for user notes
        })
        
    # 6. Save Results to CSV
    df = pd.DataFrame(results)
    df.to_csv(results_csv_path, index=False)
    
    # 7. Write Markdown Manual Audit Template
    with open(manual_audit_path, "w", encoding="utf-8") as f:
        f.write("# QA Agent Brand Voice Manual Audit Report\n\n")
        f.write(f"**Date:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"**Run Folder:** `runs/qa_agent/{timestamp}/`\n\n")
        f.write("## Audit Guidelines\n")
        f.write("1. **Brand Voice:** Calm, luxury tone? Under 3 sentences? No emojis?\n")
        f.write("2. **WhatsApp Formatting:** Uses `*bold*` (single asterisk)? No double asterisks `**`?\n")
        f.write("3. **Groundedness:** Matches facts in RAG Context exactly? No hallucinations?\n\n")
        f.write("## Scenario Scores\n\n")
        for res in results:
            f.write(f"### [Scenario ID {res['ID']}] {res['User_Input']}\n")
            f.write(f"- **Agent Output:** {res['Agent_Output']}\n")
            f.write("- **Audit Status:** [ ] PASS  [ ] FAIL\n")
            f.write("- **Audit Notes:** \n\n")
            
    print(f"\nTest execution complete.")
    print(f"Results CSV: {results_csv_path}")
    print(f"Manual Audit Template: {manual_audit_path}\n")

if __name__ == "__main__":
    main()
