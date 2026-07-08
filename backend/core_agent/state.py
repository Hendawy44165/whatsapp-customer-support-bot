from typing import Annotated, Any, Literal, Optional
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage
from langchain.agents import AgentState


class ServiceBotState(AgentState):
    """Shared state passed through all nodes in the LangGraph."""

    messages: Annotated[list[BaseMessage], add_messages]
    next_agent: Literal["router", "qa", "react", "escalator", "block", "end"]
    sentiment: str
    classification: str
    qa_directive: Literal[
        "answer", "delegate_to_react", "ask_for_params", "present_results", "escalate"
    ]
    react_request: Optional[Any]
    react_result: str | None
    missing_params: list | None
