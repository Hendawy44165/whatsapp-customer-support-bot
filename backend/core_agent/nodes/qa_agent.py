from typing import Dict
from langchain_core.messages import SystemMessage
from pydantic import BaseModel
from .base import BaseNode
from ..state import AgentState

class QAAgentNode(BaseNode):
    """
    Formulates a luxury brand-voice response for the customer.
    Follows WhatsApp formatting constraints and grounds output in RAG/CRM context.
    """
    def __call__(self, state: AgentState) -> Dict:
        system_prompt = self.agent.loader.load_prompt("qa_agent.md")
        
        rag_context = state.get("rag_output")
        learned_user_info = state.get("learned_user_info")
        router_decision = state.get("router_decision")
        react_state = state.get("react_state")
        emotion = router_decision.get("emotion")
        classification = router_decision.get("classification")
        
        state_context_lines = []
        if rag_context:
            state_context_lines.append(f"RAG Context: {rag_context}")
        if learned_user_info:
            state_context_lines.append(f"Learned User Info: {learned_user_info}")

        if emotion:
            state_context_lines.append(f"Detected Emotion: {emotion}")
        if classification:
            state_context_lines.append(f"Message Classification: {classification}")
            
        if react_state:
            status_code = react_state.get("status_code", "not_triggered")
            if status_code and status_code != "failure":
                state_context_lines.append(f"React Status Code: {status_code}")
                
                if status_code == "success":
                    output = react_state.get("output")
                    if output:
                        state_context_lines.append(f"React Output: {output}")
                elif status_code == "incomplete_input":
                    missing_customer_data = react_state.get("missing_customer_data")
                    if missing_customer_data:
                        state_context_lines.append(f"Missing Customer Data: {missing_customer_data}")
                    query_rationale = react_state.get("query_rationale")
                    if query_rationale:
                        state_context_lines.append(f"Query Rationale: {query_rationale}")

        state_context = ""
        if state_context_lines:
            state_context = "#CONTEXT VARIABLES\n" + "".join(state_context_lines)
            
        # Prepare inputs
        messages = [SystemMessage(content=system_prompt)]
        if state_context:
            messages.append(SystemMessage(content=state_context))
            
        # Include recent message history
        history = state.get("messages", [])
        messages.extend(history)
        
        # Invoke model directly for raw text output
        response = self.agent.model.invoke(messages)
        
        updates = { "messages": [response] }
        if not rag_context or not rag_context.strip():
            updates["process_state"] = "no_info_found"
            
        return updates
