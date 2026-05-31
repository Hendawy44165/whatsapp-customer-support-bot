from typing import Annotated, TypedDict, List, Dict
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage

class AgentState(TypedDict):
    """
    Represents the operational state of the Customer Service Agent.
    
    Attributes:
        messages: The accumulated chat history including user messages, tool outputs, and assistant responses.
        user_prompt: The latest query input by the user.
        category: The classified category of the user query.
        is_safe: Flag determined by input guardrail to filter out malicious or unrelated queries.
        emotion_signals: Extracted signals containing vibration/vibe, intent, and reasoning.
        enhanced_prompt: System instructions and preloaded context merged with emotional cues.
        response: The current candidate response text.
        audit_logs: Historical log entries of all validation audits run across loops.
        failed_checks: List of specific violations identified during the current iteration.
        iteration_count: Counter tracking the loops run inside the self-correction cycle.
    """
    messages: Annotated[List[BaseMessage], add_messages]
    user_prompt: str
    category: str
    is_safe: bool
    emotion_signals: Dict[str, str]
    enhanced_prompt: str
    response: str
    audit_logs: List[str]
    failed_checks: List[str]
    iteration_count: int
