from typing import Dict
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage
from agent.nodes.base import BaseNode
from agent.state import AgentState, AuditCheckResult

class AuditorNode(BaseNode):
    """
    Runs Brand, Fact, Emotional, and Output Guardrail evaluations on candidate output.
    """
    def _run_single_audit(self, audit_type: str, system_prompt: str, evaluation_payload: str, use_tools: bool = True) -> AuditCheckResult:
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=evaluation_payload)
        ]
        
        if use_tools:
            model_with_tools = self.agent.model.bind_tools([self.agent.retrieve_tool])
            for _ in range(3):
                res = model_with_tools.invoke(messages)
                if not res.tool_calls:
                    break
                messages.append(res)
                for tool_call in res.tool_calls:
                    tool_name = tool_call["name"]
                    tool_args = tool_call["args"]
                    if tool_name == "retrieve_document_content":
                        content = self.agent.retrieve_tool.invoke(tool_args)
                    else:
                        content = f"Unknown tool: {tool_name}"
                    messages.append(ToolMessage(content=content, tool_call_id=tool_call["id"]))
                    
        structured_model = self.agent.model.with_structured_output(AuditCheckResult)
        result = structured_model.invoke(messages + [
            SystemMessage(content=(
                f"You are evaluating the candidate response for a '{audit_type}' audit. "
                "Output the final schema-compliant AuditCheckResult now."
            ))
        ])
        return result

    def __call__(self, state: AgentState) -> Dict:
        candidate = state.get("response", "")
        if isinstance(candidate, list):
            texts = []
            for block in candidate:
                if isinstance(block, dict) and "text" in block:
                    texts.append(block["text"])
                elif isinstance(block, str):
                    texts.append(block)
            candidate = "".join(texts)
            
        failed_checks = []
        audit_logs = list(state.get("audit_logs", []))
        
        # Guard against empty candidate responses
        if not candidate or not candidate.strip():
            failed_checks.append("Generation Audit: Candidate response is empty.")
            audit_logs.append(f"Iteration {state['iteration_count']} - Generation Audit: Failed: Response is empty.")
            return {
                "failed_checks": failed_checks,
                "audit_logs": audit_logs,
                "audit_results": []
            }
            
        # Run all 4 audits using the structured helper
        brand_result = self._run_single_audit("brand", self.agent.loader.brand_audit_prompt, candidate)
        fact_result = self._run_single_audit("fact", self.agent.loader.fact_audit_prompt, candidate)
        
        emotion_payload = (
            f"User Vibe: {state['emotion_signals'].get('vibe', 'calm')}\n"
            f"User Intent: {state['emotion_signals'].get('intent', 'browsing')}\n\n"
            f"Candidate Response:\n{candidate}"
        )
        emotional_result = self._run_single_audit("emotional", self.agent.loader.emotional_audit_prompt_template, emotion_payload)
        
        security_result = self._run_single_audit("security", self.agent.loader.output_guardrail_prompt, candidate, use_tools=False)
        
        # Collect results
        audit_results = [
            brand_result.model_dump(),
            fact_result.model_dump(),
            emotional_result.model_dump(),
            security_result.model_dump()
        ]
        
        # Process hard errors
        for res in [brand_result, fact_result, emotional_result, security_result]:
            if res.status_code == "hard_error":
                failed_checks.append(f"{res.type.upper()} AUDIT FAILURE: {res.description} (Rec: {res.recommendation})")
                audit_logs.append(f"Iteration {state['iteration_count']} - {res.type.upper()} Audit Failed: {res.description}")
            else:
                status_label = "Passed" if res.status_code == "pass" else "Warning"
                audit_logs.append(f"Iteration {state['iteration_count']} - {res.type.upper()} Audit {status_label}")
                
        return {
            "failed_checks": failed_checks,
            "audit_logs": audit_logs,
            "audit_results": audit_results
        }
