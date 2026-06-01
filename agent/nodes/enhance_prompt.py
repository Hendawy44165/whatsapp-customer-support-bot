from typing import Dict
from agent.nodes.base import BaseNode
from agent.state import AgentState

class EnhancePromptNode(BaseNode):
    """
    Assembles contextual metadata and preloaded brand guidelines into a single instruction set.
    """
    def __call__(self, state: AgentState) -> Dict:
        system_prompt = self.agent.loader.load_system_prompt()
        doc_list_str = "\n".join(self.agent.loader.doc_descriptions)
        
        signals = state.get("emotion_signals", {})
        emotion = signals.get("vibe", "calm")
        intent = signals.get("intent", "browsing")
        reason = signals.get("reason", "")
        
        enhanced_prompt = (
            f"{system_prompt}\n\n"
            f"=== PERMANENT CONTEXT ===\n{self.agent.loader.permanent_context}\n\n"
            f"=== KNOWLEDGE DOCUMENTS AVAILABLE VIA TOOL ===\n"
            f"You have access to a tool `retrieve_document_content` which can fetch details for:\n"
            f"{doc_list_str}\n\n"
            f"=== ORDER TRACKING DATABASE TOOL ===\n"
            f"You have access to a tool `look_up_order` which can fetch live tracking and shipment details for an order ID or phone number.\n\n"
            f"=== EMOTIONAL & INTENT CONTEXT ===\n"

            f"- User emotional state: {emotion} (Reason: {reason})\n"
            f"- User buying intent level: {intent}\n"
            f"Instruction: Adapt your tone and response format to match the customer's emotional state. "
            f"If the user is anxious or frustrated, address their concern directly and reassuringly."
        )
        
        return {"enhanced_prompt": enhanced_prompt}
