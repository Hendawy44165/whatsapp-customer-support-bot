from typing import Annotated, List, Dict, Literal
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage
from pydantic import BaseModel, Field

class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]  # Pure User-Agent Chat History
    active_process: str                                   # None | "WISMO" | "Return" | "Exchange"
    process_state: str                                    # "idle" | "collecting" | "completed" | "failed"
    extracted_parameters: dict                            # Collected parameters, e.g. {"phone": "010..."}
    crm_result: dict                                      # Output of mock CRM tool lookup
    rag_context: str                                      # RAG context (Isolated for QA Agent)
    escalation_report: dict                               # Structured JSON for human handoff

class RouterResult(BaseModel):
    decision: Literal["qa", "react", "escalate"] = Field(
        ..., description="The next agent to route the query to."
    )

class EscalationReport(BaseModel):
    reason: str = Field(
        ..., description="The reason for human handoff (e.g. anger, failure, stalling)."
    )
    chat_summary: str = Field(
        ..., description="A short summary of the user's inquiry."
    )
    urgency: float = Field(
        ..., description="Urgency priority level from 0.0 to 1.0."
    )
