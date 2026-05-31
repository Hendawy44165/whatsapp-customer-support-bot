from typing import Dict
from agent.nodes.base import BaseNode
from agent.state import AgentState

class IterationEnhancerNode(BaseNode):
    """
    Increments the graph iteration count during revision loops.
    """
    def __call__(self, state: AgentState) -> Dict:
        return {"iteration_count": state["iteration_count"] + 1}
