from typing import Annotated, TypedDict, List, Dict, Literal
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage
from pydantic import BaseModel, Field

class ClassifierResult(BaseModel):
    category: Literal[
        "unrelated_or_harmful",
        "greeting_or_chitchat",
        "order_tracking",
        "faq_shipping_egypt",
        "faq_shipping_intl",
        "faq_returns_refunds",
        "faq_discovery_box",
        "complex_uncategorized"
    ] = Field(..., description="The classified category of the user prompt.")

class EmotionAnalysisResult(BaseModel):
    vibe: Literal["calm", "frustrated", "anxious", "angry", "satisfied", "neutral"] = Field(
        ..., description="The user's emotional state."
    )
    intent: Literal["browsing", "searching", "buying", "complaining", "neutral"] = Field(
        ..., description="The user's intent."
    )
    reason: str = Field(..., description="The short rationale for this emotional classification.")

class AuditCheckResult(BaseModel):
    type: Literal["brand", "fact", "emotional", "security"] = Field(
        ..., description="Type of the audit run."
    )
    status_code: Literal["pass", "soft_warning", "hard_error"] = Field(
        ..., description="Status category. 'pass' means compliant. 'soft_warning' is minor. 'hard_error' requires correction."
    )
    description: str = Field(
        ..., description="Detailed explanation of the violation or issue. Empty if passed."
    )
    recommendation: str = Field(
        ..., description="Specific recommended instructions to resolve this error."
    )
    action_type: Literal["quick_fix", "full_iteration"] = Field(
        ..., description="Recommended fix pathway."
    )

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
        audit_results: The list of Pydantic-structured check results from evaluation runs.
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
    audit_results: List[Dict]
    audit_logs: List[str]
    failed_checks: List[str]
    iteration_count: int
    is_handoff: bool
    handoff_summary: str

