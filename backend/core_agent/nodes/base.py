from abc import ABC, abstractmethod
from typing import Dict
from ..state import AgentState

class BaseNode(ABC):
    """
    Abstract base class for all LangGraph nodes.
    Each node receives the current AgentState and returns a dictionary of updates.
    """
    def __init__(self, agent):
        self.agent = agent  # References orchestrator CustomerServiceAgent to access models, loader, tools

    @abstractmethod
    def __call__(self, state: AgentState) -> Dict:
        pass
