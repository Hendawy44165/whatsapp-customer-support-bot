from typing import Dict
from langchain_core.messages import HumanMessage, AIMessage
from agent.nodes.base import BaseNode
from agent.state import AgentState
from agent.constants import DIRECT_RESPONSES

class DirectResponseNode(BaseNode):
    """
    Generates brand-compliant direct responses for simple categories,
    bypassing the main generator loop and audits.
    """
    def __call__(self, state: AgentState) -> Dict:
        category = state.get("category", "complex_uncategorized")
        user_prompt = state["user_prompt"]
        reply = DIRECT_RESPONSES.get(category, "I apologize, let me connect you with support.")
        
        return {
            "response": reply,
            "messages": [HumanMessage(content=user_prompt), AIMessage(content=reply)]
        }
