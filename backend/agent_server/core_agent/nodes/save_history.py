from typing import Dict
from langchain_core.messages import HumanMessage, AIMessage
from agent.nodes.base import BaseNode
from agent.state import AgentState


class SaveHistoryNode(BaseNode):
    """
    Appends the current turn's HumanMessage and the finalized audited response
    to the state's message list.
    """

    def __call__(self, state: AgentState) -> Dict:
        user_prompt = state.get("user_prompt", "")
        response = state.get("response", "")

        return {
            "messages": [
                HumanMessage(content=user_prompt),
                AIMessage(content=response)
            ]
        }
