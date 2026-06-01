from typing import Dict
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from agent.nodes.base import BaseNode
from agent.state import AgentState


class HumanHandoffNode(BaseNode):
    """
    Handles escalation to a human agent, generating a structured 3-bullet
    summary of intent, actions, and reason for handoff.
    """

    def __call__(self, state: AgentState) -> Dict:
        history = state.get("messages", [])
        user_prompt = state.get("user_prompt", "")

        # Format recent history
        history_text = "\n".join([f"{m.type.upper()}: {m.content}" for m in history[-6:]])
        history_text += f"\nUSER: {user_prompt}"

        failed_checks_str = "\n".join(state.get("failed_checks", [])) if state.get("failed_checks") else "None"

        handoff_instruction = (
            "You are a Support Lead supervisor at Nuit Fragrances.\n"
            "An automated customer service agent has failed validation or reached its limit, and we must route the customer to a human.\n"
            "Based on the conversation history and audit logs, generate a concise **3-bullet summary** for the human agent:\n"
            "1. **Customer Intent**: (Single-sentence summary of what the customer wants, e.g. 'Wants to dispute a shipping charge')\n"
            "2. **Actions Attempted**: (What the chatbot or database lookup tried to do, e.g. 'Checked faq docs but could not find international return rules')\n"
            "3. **Reason for Handoff**: (Why the bot is escalating, e.g. 'Verification audit loop threshold exceeded' or 'Low RAG search confidence')\n"
            "\n"
            "Format the output strictly as a markdown list with these 3 bullet points."
        )

        try:
            summary = self.agent.model.invoke([
                SystemMessage(content=handoff_instruction),
                HumanMessage(content=f"Conversation History:\n{history_text}\n\nFailed Verification Audit Checks:\n{failed_checks_str}")
            ]).content.strip()
        except Exception:
            summary = (
                "1. **Customer Intent**: Query about order status or policy.\n"
                "2. **Actions Attempted**: Processed through LangGraph concierge flow.\n"
                "3. **Reason for Handoff**: Automatic escalation triggered."
            )

        fallback_reply = (
            "I want to ensure you receive completely accurate details on that matter. "
            "Let me verify our specific inventory files or connect you directly with a specialist from our care team. "
            "May I please have your phone number to look up your order profile?"
        )

        new_messages = [
            HumanMessage(content=user_prompt),
            AIMessage(content=fallback_reply)
        ]

        return {
            "is_handoff": True,
            "handoff_summary": summary,
            "response": fallback_reply,
            "messages": new_messages
        }
