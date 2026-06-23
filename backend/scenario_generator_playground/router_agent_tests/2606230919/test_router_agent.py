import os
import json
import time
import re
import pandas as pd
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

def validate_output(ai_output: str) -> str:
    ai_out_str = ai_output.strip()
    if not ai_out_str:
        return "FAIL: Empty response from AI."
    
    # 1. Check markdown wrapping ```json ... ```
    pattern = r'^```json\s*\n([\s\S]*?)\n```$'
    match = re.match(pattern, ai_out_str)
    
    if not match:
        # Check if they returned raw JSON without block
        if ai_out_str.startswith("{") and ai_out_str.endswith("}"):
            json_str = ai_out_str
            format_err = "Format issue: Output not wrapped in ```json ... ``` block."
        else:
            return "FAIL: Output not wrapped in ```json ... ``` code block."
    else:
        json_str = match.group(1).strip()
        format_err = ""
        
    # 2. Check JSON parsing
    try:
        data = json.loads(json_str)
    except Exception as e:
        return f"FAIL: Invalid JSON parsing. Error: {e}"
        
    # 3. Check keys
    required_keys = {'topic', 'unrelated_type', 'emotion', 'priority', 'critique', 'user_prompt'}
    missing = required_keys - set(data.keys())
    if missing:
        return f"FAIL: Missing keys {list(missing)}"
        
    # 4. Check permitted values
    allowed_topics = {'Return', 'Exchange', 'WISMO', 'General Info', 'Unrelated'}
    allowed_unrelated_types = {'legit', 'off-topic', None}
    allowed_emotions = {'Positive', 'Neutral', 'Negative'}
    allowed_priorities = {'Casual', 'Urgent'}

    topic = data.get('topic')
    unrelated_type = data.get('unrelated_type')
    emotion = data.get('emotion')
    priority = data.get('priority')
    
    val_issues = []
    if topic not in allowed_topics:
        val_issues.append(f"invalid topic '{topic}'")
    if unrelated_type not in allowed_unrelated_types:
        val_issues.append(f"invalid unrelated_type '{unrelated_type}'")
    if emotion not in allowed_emotions:
        val_issues.append(f"invalid emotion '{emotion}'")
    if priority not in allowed_priorities:
        val_issues.append(f"invalid priority '{priority}'")
        
    # Check conditional constraint: unrelated_type should only be filled if topic is Unrelated
    if topic != "Unrelated" and unrelated_type is not None:
        val_issues.append("unrelated_type must be null when topic is not Unrelated")
        
    if val_issues:
        return f"FAIL: Value constraints: {', '.join(val_issues)}"
        
    if format_err:
        return f"PASS with warning ({format_err})"
        
    return "PASS"

def main():
    #! ====================================================================================================
    #! a. SETUP
    #! ====================================================================================================
    script_dir = os.path.dirname(os.path.abspath(__file__))
    backend_dir = os.path.dirname(script_dir)
    load_dotenv(dotenv_path=os.path.join(backend_dir, ".env"))
    os.environ["LANGSMITH_TRACING"] = "false"
    api_key = os.getenv("PROVIDER_API_KEY")
    base_url = os.getenv("PROVIDER_BASE_URL")
    model_name = os.getenv("PROVIDER_MODEL_NAME")
    prompt_path = os.path.abspath(os.path.join(script_dir, "test_prompts", "router_agent.md"))
    with open(prompt_path, "r", encoding="utf-8") as f:
        system_prompt = f.read()

    scenarios_json_path = os.path.join(script_dir, "scenarios_25.json")
    with open(scenarios_json_path, "r", encoding="utf-8") as f:
        scenarios = json.load(f)
    
    llm = ChatOpenAI(
        api_key=api_key,
        base_url=base_url,
        model=model_name,
        temperature=0.2,
        timeout=10.0,
        max_retries=1
    )

    results = []
    rate_limit_encountered = False
    rate_limit_error_msg = ""

    #! ====================================================================================================
    #! b. PROCESS SCENARIOS
    #! ====================================================================================================

    print(f"\nStarting test of {len(scenarios)} scenarios...")
    for i, scenario in enumerate(scenarios, 1):
        user_prompt = scenario.get("user_input")
        scenario_id = scenario.get("id")
        
        print(f"[{i}/{len(scenarios)}] Processing scenario ID {scenario_id}...")

        ai_critique = ""
        ai_topic = "error"
        ai_urgency = "error"
        ai_emotion = "error"

        if rate_limit_encountered:
            ai_critique = f"Skipped: Prior request failed with rate limit. Original error: {rate_limit_error_msg}"
            print(f"  Skipping API call for scenario ID {scenario_id} due to prior rate limit.")
        else:
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]

            #? Run with rate limit & error handling
            try:
                response = llm.invoke(messages)
                ai_output = response.content
                validation_status = validate_output(ai_output)
                
                if validation_status.startswith("PASS"):
                    # Extract fields from output
                    match = re.match(r'^```json\s*\n([\s\S]*?)\n```$', ai_output.strip())
                    json_str = match.group(1).strip() if match else ai_output.strip()
                    
                    data = json.loads(json_str)
                    ai_critique = data.get("critique", "")
                    ai_topic = data.get("topic", "error")
                    ai_urgency = data.get("priority", "error")
                    ai_emotion = data.get("emotion", "error")
                else:
                    # Invalid JSON structure
                    ai_critique = f"Validation Error: {validation_status}"
            except Exception as e:
                error_msg = str(e)
                ai_critique = error_msg
                print(f"  Error processing scenario ID {scenario_id}: {error_msg}")
                
                # Check if it was a rate limit error
                rate_limit_keywords = ["ratelimit", "rate limit", "429", "resourceexhausted", "quota"]
                if any(kw in error_msg.lower() for kw in rate_limit_keywords):
                    rate_limit_encountered = True
                    rate_limit_error_msg = error_msg
                    print(f"  Rate limit detected! Skipping all future API calls.")

        results.append({
            "Model Name": model_name or "Unknown Model",
            "User Input": user_prompt,
            "Critique": ai_critique,
            "Topic": ai_topic,
            "Urgency": ai_urgency,
            "Emotion": ai_emotion
        })

        if not rate_limit_encountered:
            time.sleep(0.5)

    #! ====================================================================================================
    #! c. EXPORT RESULTS
    #! ====================================================================================================

    #? Using utf-8-sig so that Microsoft Excel opens it with correct encoding directly
    df = pd.DataFrame(results)
    output_path = os.path.join(script_dir, "router_test_results.csv")
    df.to_csv(output_path, index=False, encoding="utf-8-sig")
    
    print("\n" + "="*50)
    print(f"Execution complete!")
    print(f"Results exported successfully to spreadsheet format:")
    print(f"  {output_path}")
    print("="*50)

if __name__ == "__main__":
    main()
