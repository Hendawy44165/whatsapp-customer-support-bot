from typing import Dict
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage
from .base import BaseNode
from ..state import AgentState

class GeneratorNode(BaseNode):
    """
    Executes a dynamic tool-calling React loop to generate a candidate response.
    """
    def __call__(self, state: AgentState) -> Dict:
        # TODO: split to response creator, w/o markdown, and the main agent that does the actions
        user_prompt = state["user_prompt"]
        
        model_with_tools = self.agent.model.bind_tools(self.agent.tools)
        
        signals = state.get("emotion_signals", {})
        emotion = signals.get("vibe", "calm")
        intent = signals.get("intent", "browsing")
        reason = signals.get("reason", "")
        
        dynamic_context = (
            f"=== EMOTIONAL & INTENT CONTEXT ===\n"
            f"- User emotional state: {emotion} (Reason: {reason})\n"
            f"- User buying intent level: {intent}\n"
            f"Instruction: Adapt your tone and response format to match the customer's emotional state. "
            f"If the user is anxious or frustrated, address their concern directly and reassuringly."
        )
        
        full_system = f"{self.agent.loader.static_prompt_content}\n\n{dynamic_context}"
        messages = [
            SystemMessage(content=full_system)
        ]
            
        if state.get("iteration_count", 0) > 0:
            revision_feedback = (
                f"CRITICAL: The previous response failed verification audits.\n"
                f"Failed Checks:\n" + "\n".join([f"- {err}" for err in state["failed_checks"]]) + "\n\n"
                f"Please rewrite the response to resolve these violations. Do not repeat the same errors."
            )
            messages.append(SystemMessage(content=revision_feedback))
            
        messages.extend(state.get("messages", [])[-5:])
        messages.append(HumanMessage(content=user_prompt))
        
        # Initialize default response
        response = None
        for _ in range(5):
            response = model_with_tools.invoke(messages)
                 
            messages.append(response)
            
            if not response.tool_calls:
                content = response.content
                if isinstance(content, list):
                    texts = []
                    for block in content:
                        if isinstance(block, dict) and "text" in block:
                            texts.append(block["text"])
                        elif isinstance(block, str):
                            texts.append(block)
                    content = "".join(texts)
                return {
                    "response": content
                }
                
            for tool_call in response.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]
                if tool_name in self.agent.tools_by_name:
                    content = self.agent.tools_by_name[tool_name].invoke(tool_args)
                else:
                    content = f"Unknown tool: {tool_name}"
                
                tool_msg = ToolMessage(content=content, tool_call_id=tool_call["id"])
                messages.append(tool_msg)
                
        if response is not None:
            content = response.content
            if isinstance(content, list):
                texts = []
                for block in content:
                    if isinstance(block, dict) and "text" in block:
                        texts.append(block["text"])
                    elif isinstance(block, str):
                        texts.append(block)
                content = "".join(texts)
        else:
            content = ""
            
        return {
            "response": content
        }

