import os
import sys
import json
import time
from typing import List, Literal, Dict
from pydantic import BaseModel, Field
from dotenv import load_dotenv
import pandas as pd

# LangChain Imports
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

# Define the expected QA Output Schema
class QAOutput(BaseModel):
    reasoning: str = Field(..., description="Short explanation of the state evaluation and decision.")
    response_text: str = Field(..., description="The luxury, brand-voice response text for the user.")
    process_instruction: Literal["request_info", "proceed_to_process", "complete", "escalate_to_human", "none"] = Field(
        ..., description="Action instruction for the orchestrator."
    )
    missing_parameters: List[str] = Field(
        default_factory=list, description="Fields currently missing and required from the customer."
    )

def evaluate_with_judge(judge_llm: ChatOpenAI, latest_user_message: str, response_text: str, RAG_context: str, router_decision: str) -> str:
    """Invokes the LLM-as-a-judge to evaluate tone and factuality."""
    system_prompt = (
        "You are an objective QA evaluator judge for Nuit Fragrances customer support.\n"
        "Your task is to evaluate the AI customer support response against the following criteria:\n\n"
        "1. BRAND TONE: Is it calm, polite, luxury, and professional? (It must NOT sound defensive, robotic, or overly casual).\n"
        "2. FACTUALITY: Are all prices, policies, and timelines stated in the response completely true and grounded in the RAG Context? If the RAG Context does not mention a detail, the AI response must NOT invent it.\n"
        "3. RELEVANCE & REFUSAL: If the router decision is 'Unrelated', did the response politely refuse to answer while staying within Nuit Fragrances' domain?\n\n"
        "You must output your evaluation in this exact format:\n"
        "TONE: [PASS/FAIL] - Reason\n"
        "FACTUALITY: [PASS/FAIL] - Reason\n"
        "SCOPE: [PASS/FAIL] - Reason"
    )
    
    human_content = (
        f"=== EVALUATION DETAILS ===\n"
        f"- Router Decision: {router_decision}\n"
        f"- RAG Context: {RAG_context}\n"
        f"- User Input: {latest_user_message}\n"
        f"- AI Response: {response_text}"
    )
    
    try:
        response = judge_llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=human_content)
        ])
        return response.content.strip()
    except Exception as e:
        return f"Judge evaluation failed. Error: {e}"

def convert_to_langchain_messages(chat_history: List[Dict[str, str]]) -> List:
    """Converts a standard list of message dicts into LangChain message objects."""
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
    script_dir = os.path.dirname(os.path.abspath(__file__))
    backend_dir = os.path.dirname(script_dir)
    
    # Load environment variables
    load_dotenv(dotenv_path=os.path.join(backend_dir, ".env"))
    api_key = os.getenv("PROVIDER_API_KEY")
    base_url = os.getenv("PROVIDER_BASE_URL")
    model_name = os.getenv("PROVIDER_MODEL_NAME")
    
    # Read prompt
    prompt_path = os.path.abspath(os.path.join(backend_dir, "core_agent", "prompts", "qa_agent.md"))
    with open(prompt_path, "r", encoding="utf-8") as f:
        qa_system_prompt = f.read()

    # Load scenarios
    scenarios_json_path = os.path.join(script_dir, "qa_scenarios.json")
    if not os.path.exists(scenarios_json_path):
        print(f"Error: Scenarios file not found at {scenarios_json_path}. Please create it first.")
        sys.exit(1)
        
    with open(scenarios_json_path, "r", encoding="utf-8") as f:
        scenarios = json.load(f)
        
    # Initialize LLMs
    llm = ChatOpenAI(
        api_key=api_key,
        base_url=base_url,
        model=model_name,
        temperature=0.2,
        max_retries=1
    )
    structured_qa_agent = llm.with_structured_output(QAOutput)
    
    # Initialize a separate LLM for the judge with temperature 0.0
    judge_llm = ChatOpenAI(
        api_key=api_key,
        base_url=base_url,
        model=model_name,
        temperature=0.0,
        max_retries=1
    )

    results = []

    print(f"\nStarting QA Agent test suite for {len(scenarios)} scenarios...")
    for index, scenario in enumerate(scenarios, 1):
        scenario_id = scenario.get("id")
        description = scenario.get("description")
        user_message = scenario.get("user_input")
        router_decision = scenario.get("router_decision")
        chat_history_raw = scenario.get("chat_history")
        
        print(f"\n--------------------------------------------------")
        print(f"[{index}/{len(scenarios)}] ID {scenario_id}: {description}")
        print(f"User Input: '{user_message}'")
        
        # --- Simulating Turn 1 (Initial Call) ---
        process_state = "idle"
        initial_params = scenario.get("initial_parameters", {})
        initial_rag = scenario.get("initial_rag_context", "")
        
        input_payload_1 = (
            f"=== STRUCTURED INPUT ===\n"
            f"- Router Decision: {router_decision}\n"
            f"- Process State: {process_state}\n"
            f"- Extracted Parameters: {json.dumps(initial_params)}\n"
            f"- RAG Context: {initial_rag}\n"
            f"- Latest User Message: {user_message}"
        )
        
        # Parse history into LangChain messages
        langchain_history = convert_to_langchain_messages(chat_history_raw)
        
        # Build messages block: [SystemPrompt, History..., LatestUserMessage]
        messages_1 = [SystemMessage(content=qa_system_prompt)]
        messages_1.extend(langchain_history)
        messages_1.append(HumanMessage(content=input_payload_1))
        
        t1_start = time.time()
        try:
            qa_out_1 = structured_qa_agent.invoke(messages_1)
            t1_duration = time.time() - t1_start
        except Exception as e:
            print(f"  Execution failed at Turn 1: {e}")
            results.append({
                "Model Name": model_name or "Unknown Model",
                "User Input": user_message,
                "Critique": f"Turn 1 Error: {e}",
                "Topic": router_decision,
                "Instruction": "error",
                "Response": "error",
                "Status": "FAIL"
            })
            continue

        print(f"  Turn 1 Output [Instruction: {qa_out_1.process_instruction}]:")
        print(f"    Reasoning: {qa_out_1.reasoning}")
        print(f"    Response:  '{qa_out_1.response_text}'")

        final_response_text = qa_out_1.response_text
        final_instruction = qa_out_1.process_instruction
        final_reasoning = qa_out_1.reasoning
        final_rag_context_used = initial_rag
        turn_count = 1
        
        # --- Simulating Turn 2 (Background task completed, if applicable) ---
        if qa_out_1.process_instruction == "proceed_to_process":
            print(f"  --> Simulating background process execution...")
            process_state_2 = "finished"
            
            # Merge mock process results into parameters and RAG context
            finished_params = {**initial_params, **scenario.get("background_process_mock_parameters", {})}
            finished_rag = scenario.get("background_process_result_rag", "")
            
            input_payload_2 = (
                f"=== STRUCTURED INPUT ===\n"
                f"- Router Decision: {router_decision}\n"
                f"- Process State: {process_state_2}\n"
                f"- Extracted Parameters: {json.dumps(finished_params)}\n"
                f"- RAG Context: {finished_rag}\n"
                f"- Latest User Message: {user_message}"
            )
            
            # For turn 2, append the intermediate agent response to the history simulation
            langchain_history_t2 = list(langchain_history)
            langchain_history_t2.append(HumanMessage(content=user_message))
            langchain_history_t2.append(AIMessage(content=qa_out_1.response_text))
            
            messages_2 = [SystemMessage(content=qa_system_prompt)]
            messages_2.extend(langchain_history_t2)
            messages_2.append(HumanMessage(content=input_payload_2))
            
            try:
                qa_out_2 = structured_qa_agent.invoke(messages_2)
                turn_count = 2
            except Exception as e:
                print(f"    Execution failed at Turn 2: {e}")
                results.append({
                    "Model Name": model_name or "Unknown Model",
                    "User Input": user_message,
                    "Critique": f"Turn 2 Error: {e}",
                    "Topic": router_decision,
                    "Instruction": "error",
                    "Response": "error",
                    "Status": "FAIL"
                })
                continue
                
            print(f"    Turn 2 Output [Instruction: {qa_out_2.process_instruction}]:")
            print(f"      Reasoning: {qa_out_2.reasoning}")
            print(f"      Response:  '{qa_out_2.response_text}'")
            
            final_response_text = qa_out_2.response_text
            final_instruction = qa_out_2.process_instruction
            final_reasoning = qa_out_2.reasoning
            final_rag_context_used = finished_rag
            
        # --- Run Judge Evaluation ---
        judge_output = evaluate_with_judge(
            judge_llm=judge_llm,
            latest_user_message=user_message,
            response_text=final_response_text,
            RAG_context=final_rag_context_used,
            router_decision=router_decision
        )
        print(f"    Judge Verdict:\n      " + "\n      ".join(judge_output.split("\n")))
        
        # Check overall status
        failed_tests = []
        if "FAIL" in judge_output:
            judge_fails = [line for line in judge_output.split("\n") if "FAIL" in line]
            failed_tests.extend(judge_fails)
            
        # Verify expected instruction matches
        expected_final_instr = scenario.get("expected_final_instruction")
        if expected_final_instr and final_instruction != expected_final_instr:
            failed_tests.append(f"Instruction mismatch: got '{final_instruction}', expected '{expected_final_instr}'.")

        status = "PASS" if not failed_tests else "FAIL"
        critique_log = f"Agent reasoning: {final_reasoning} | Judge verdict: {judge_output}"
        
        results.append({
            "Model Name": model_name or "Unknown Model",
            "User Input": user_message,
            "Critique": critique_log,
            "Topic": router_decision,
            "Instruction": final_instruction,
            "Response": final_response_text,
            "Status": status
        })
        
        time.sleep(0.5)

    # Export results to CSV
    df = pd.DataFrame(results)
    output_path = os.path.join(script_dir, "qa_agent_test_results.csv")
    df.to_csv(output_path, index=False, encoding="utf-8-sig")
    
    print("\n" + "="*50)
    print(f"Execution complete!")
    print(f"Results exported successfully to:")
    print(f"  {output_path}")
    print("="*50)

if __name__ == "__main__":
    main()
