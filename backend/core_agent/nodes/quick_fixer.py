from typing import Dict
from langchain_core.messages import SystemMessage, HumanMessage
from .base import BaseNode
from ..state import AgentState

class QuickFixerNode(BaseNode):
    """
    Applies a lightweight style/format correction to the candidate response
    based on styling audit feedback.
    """
    def __call__(self, state: AgentState) -> Dict:
        candidate = state.get("response", "")
        failed_checks_str = "\n".join([f"- {err}" for err in state.get("failed_checks", [])])
        
        prompt = (
            f"Candidate Response:\n{candidate}\n\n"
            f"Failed Checks:\n{failed_checks_str}"
        )
        
        res = self.agent.model.invoke([
            SystemMessage(content=self.agent.loader.quick_fix_prompt),
            HumanMessage(content=prompt)
        ]).content.strip()
        
        # Clean any accidental markdown output wrappers
        if res.startswith("```"):
            lines = res.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            res = "\n".join(lines).strip()
            
        return {
            "response": res,
            "iteration_count": state["iteration_count"] + 1
        }
