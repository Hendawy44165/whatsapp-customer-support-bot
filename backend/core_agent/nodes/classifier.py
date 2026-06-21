from typing import Dict
from langchain_core.messages import SystemMessage, HumanMessage
from .base import BaseNode
from ..state import AgentState, ClassifierResult
from ..constants import VALID_CATEGORIES

class ClassifierNode(BaseNode):
    """
    Classifies the incoming user prompt to determine if it can be routed directly
    or requires the main complex agent workflow.
    """
    def __call__(self, state: AgentState) -> Dict:
        user_prompt = state["user_prompt"]
        structured_model = self.agent.model.with_structured_output(ClassifierResult)
        result = structured_model.invoke([
            SystemMessage(content=self.agent.loader.classifier_prompt),
            HumanMessage(content=user_prompt)
        ])
        
        category = result.category
        if category not in VALID_CATEGORIES:
            category = "complex_uncategorized"
            
        return {"category": category}
