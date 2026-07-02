from typing import Annotated, List, Dict, Literal
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage

class RouterDecision(TypedDict):
    next_agent: Literal["qa", "react", "escalate"]
    emotion : str
    classification : Literal["WISMO", "Return", "Exchange", "Billing", "General Inquery", "Other"]

class EscalationReport(TypedDict):
    report : str
    customer_emotion : Literal["anger", "joy", "sadness", "fear", "surprise", "disgust", "neutral", "frustration"]
    urgency : Literal["low", "medium", "high", "critical"]
    customer_name : str
    customer_age : int

class ReactState(TypedDict):
    missing_customer_data : List[str]
    query_rationale : str
    output : dict
    status_code : Literal["success", "incomplete_input", "failure", "not_triggered"]

class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]  # Pure User-Agent Chat History
    process_state: str                                    # "idle" | "collecting" | "completed" | "failed" | "no_info_found"
    learned_user_info : dict
    router_decision : RouterDecision
    escalation_report : EscalationReport
    react_state : ReactState
    rag_output : str