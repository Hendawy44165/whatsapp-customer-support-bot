"""
AgentState and Pydantic structured output models for the Nuit Bot v2 graph.
"""

from typing import Annotated, Literal
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Structured Outputs (Pydantic) — used with model.with_structured_output()
# ---------------------------------------------------------------------------

class RouterOutput(BaseModel):
    """Structured output from the Router agent."""
    next_agent: Literal["qa", "escalate", "block"] = Field(
        description="Which agent should handle this message."
    )
    sentiment: Literal["neutral", "positive", "frustrated", "angry"] = Field(
        description="Detected user sentiment."
    )
    classification: Literal[
        "general_inquiry", "order_tracking", "return_exchange",
        "product_question", "billing", "unrelated", "greeting"
    ] = Field(
        description="Intent classification of the user message."
    )
    reasoning: str = Field(
        description="Brief explanation of the routing decision for tracing."
    )


class ReactResult(BaseModel):
    """Structured output from the ReAct agent back to the QA agent."""
    status: Literal["success", "need_info", "failed"] = Field(
        description="Outcome of the ReAct agent's execution."
    )
    tool_output: dict | None = Field(
        default=None,
        description="Raw CRM tool result if status is success."
    )
    missing_params: list[str] | None = Field(
        default=None,
        description="Parameters still needed from the user."
    )
    reasoning: str = Field(
        description="Step-by-step reasoning plan for LangSmith tracing."
    )
    failure_reason: str | None = Field(
        default=None,
        description="Why the operation failed, if applicable."
    )


class EscalationReport(BaseModel):
    """Structured output from the Human Escalation agent."""
    reason: Literal[
        "customer_anger", "react_failure", "direct_request",
        "user_stalling", "repeated_failure"
    ] = Field(
        description="Why the conversation is being escalated."
    )
    chat_summary: str = Field(
        description="1-2 sentence recap of the conversation."
    )
    urgency: float = Field(
        ge=0.0, le=1.0,
        description="Urgency score from 0.0 (low) to 1.0 (critical)."
    )
    collected_metadata: dict = Field(
        default_factory=dict,
        description="Any user info collected: phone, order_id, name, etc."
    )
    recommended_actions: list[str] = Field(
        default_factory=list,
        description="Suggested next steps for the human agent."
    )



class ExtractedUserInfo(BaseModel):
    """Structured output from the CRM extraction LLM call."""
    name: str | None = Field(
        default=None,
        description="Customer's name if mentioned in the conversation.",
    )
    phone: str | None = Field(
        default=None,
        description="Customer's phone number if mentioned.",
    )
    delivery_zone: str | None = Field(
        default=None,
        description="Customer's delivery governorate/area if mentioned.",
    )
    order_ids: list[str] = Field(
        default_factory=list,
        description="Any order IDs the customer mentioned.",
    )
    product_preferences: list[str] = Field(
        default_factory=list,
        description="Fragrance names or product types the customer showed interest in.",
    )
    has_new_info: bool = Field(
        default=False,
        description="True if ANY of the above fields contain real new information from this conversation.",
    )


class QAOutput(BaseModel):
    """Structured output from the QA Agent."""
    message: str = Field(
        description="The response message to the user, styled for WhatsApp directly. Do NOT include markdown headers."
    )
    qa_directive: Literal["answer", "delegate_to_react", "present_results", "ask_for_params", "escalate"] = Field(
        description="Routing directive."
    )
    react_request: str | None = Field(
        default=None,
        description="The request description for the ReAct agent if delegating."
    )


# ---------------------------------------------------------------------------
# Graph State
# ---------------------------------------------------------------------------

class AgentState(TypedDict):
    """Shared state passed through all nodes in the LangGraph."""

    # Conversation history — auto-merged via add_messages reducer
    messages: Annotated[list[BaseMessage], add_messages]

    # Router output
    router_output: RouterOutput | None

    # QA <-> ReAct coordination
    qa_directive: str   # "answer" | "delegate_to_react" | "present_results" | "ask_for_params" | "escalate"
    react_request: str | None        # what QA wants ReAct to do
    react_result: ReactResult | None

    # Escalation
    escalation_report: EscalationReport | None

    # CRM auto-update tracking
    learned_user_info: dict   # {name, phone, zone, preferences...}

    # Guardrails
    react_turn_count: int     # max 3 per user turn

    # Final output
    final_response: str       # the WhatsApp-formatted message to send to the user