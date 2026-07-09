from typing import Annotated, Any, Literal, Optional
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage
from langchain.agents import AgentState


class ServiceBotState(AgentState):
    """Shared state passed through all nodes in the LangGraph."""

    messages: Annotated[list[BaseMessage], add_messages]
    next_agent: Literal["router", "qa", "planner", "executor", "escalator", "blocker", "end"]
    sentiment: str
    classification: str
    
    # Communication channel between Planner and Executor
    planner_command: str
    executor_report: str
    required_docs: list[str]
    
    # Private executor state
    gathered_parameters: dict[str, Any]
    gathered_information: list[str]
    extracted_parameters: dict[str, Any]

    # Legacy fields kept temporarily to avoid import / runtime failures during transition
    qa_directive: Optional[Literal[
        "answer", "delegate_to_react", "ask_for_params", "present_results", "escalate"
    ]]
    react_request: Optional[Any]
    react_result: Optional[str]
    missing_params: Optional[list]
