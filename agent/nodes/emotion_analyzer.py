from typing import Dict
from langchain_core.messages import SystemMessage, HumanMessage
from agent.nodes.base import BaseNode
from agent.state import AgentState, EmotionAnalysisResult

class EmotionAnalyzerNode(BaseNode):
    """
    Extracts customer sentiment patterns and intent level from conversation history.
    """
    def __call__(self, state: AgentState) -> Dict:
        user_prompt = state["user_prompt"]
        history = state.get("messages", [])
        history_text = "\n".join([f"{m.type}: {m.content}" for m in history[-5:]])
        
        prompt = f"Chat History:\n{history_text}\n\nUser Prompt: {user_prompt}"
        structured_model = self.agent.model.with_structured_output(EmotionAnalysisResult)
        result = structured_model.invoke([
            SystemMessage(content=self.agent.loader.emotion_analysis_prompt),
            HumanMessage(content=prompt)
        ])
        
        signals = {
            "vibe": result.vibe,
            "intent": result.intent,
            "reason": result.reason
        }
        return {"emotion_signals": signals}
