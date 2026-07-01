from typing import Dict
from langchain_core.messages import SystemMessage
from .base import BaseNode
from ..state import AgentState

class QAAgentNode(BaseNode):
    """
    Formulates a luxury brand-voice response for the customer.
    Follows WhatsApp formatting constraints and grounds output in RAG/CRM context.
    """
    def __call__(self, state: AgentState) -> Dict:
        # Load system instructions from qa_agent.md prompt
        system_prompt = self.agent.loader.load_prompt("qa_agent.md")
        
        # Extract inputs from graph state
        active_process = state.get("active_process")
        process_state = state.get("process_state", "idle")
        crm_result = state.get("crm_result") or {}
        rag_context = state.get("rag_context", "")
        
        # Construct dynamic context based on state
        state_context_lines = ["=== CONTEXT VARIABLES ==="]
        if active_process:
            state_context_lines.append(f"Active Process: {active_process}")
            state_context_lines.append(f"Process State: {process_state}")
        if crm_result:
            state_context_lines.append(f"CRM Lookup Output: {crm_result}")
        if rag_context:
            state_context_lines.append(f"RAG Context (Policies/FAQs):\n{rag_context}")
            
        state_context = "\n".join(state_context_lines)
        
        # Prepare inputs
        messages = [
            SystemMessage(content=system_prompt),
            SystemMessage(content=state_context)
        ]
        
        # Include recent message history
        history = state.get("messages", [])
        messages.extend(history)
        
        # Invoke model directly for raw text output
        response = self.agent.model.invoke(messages)
        
        return {
            "response": response.content.strip()
        }
