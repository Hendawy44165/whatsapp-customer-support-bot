from dataclasses import dataclass
from typing import Dict, Literal
from pydantic import BaseModel, field_validator
from langsmith import traceable
from langchain.agents import create_agent
from langchain.agents.middleware import after_agent
from langgraph.checkpoint.memory import InMemorySaver
from langchain.agents.middleware import dynamic_prompt, ModelRequest

from ..state import ServiceBotState
from ..config import get_model, load_prompt
from ..tools import lookup_order, register_return, register_exchange


@dataclass
class ReactContext:
    react_request: str | None


class ReactResponse(BaseModel):
    next_agent: Literal["qa", "escalate"]
    missing_params: list[str]
    result: str | None

    @field_validator("missing_params", mode="before")
    @classmethod
    def coerce_missing_params(cls, v):
        if v is None or v == "":
            return []
        if isinstance(v, str):
            return [v]  # single stray string -> wrap it, don't reject it
        return v


@dynamic_prompt
def inject_context(request: ModelRequest) -> str:
    ctx = request.runtime.context
    base = load_prompt("react_agent.md")
    return f"""{base}

    <context>
    react_request: {ctx.react_request}
    </context>
    """


@after_agent
def clear_qa_request(state: ServiceBotState, runtime):
    return {"react_request": None}


@traceable
def react_agent_node(state: ServiceBotState) -> Dict:
    """
    Executes CRM operations using tool calling.

    Flow:
    1. Receives task from QA via react_request
    2. Plans what tools to call and estimates execution steps
    3. Calculates dynamic max_steps (estimated_steps * 2, default to 10 if not decided)
    4. If params missing → returns need_info with missing_params
    5. If params present → calls tool → returns success/failed with result
    """
    model = get_model()

    agent = create_agent(
        model=model,
        tools=[lookup_order, register_return, register_exchange],
        checkpointer=InMemorySaver(),
        response_format=ReactResponse,
        middleware=[clear_qa_request, inject_context],
        context_schema=ReactContext,
    )

    context = ReactContext(
        react_request=state["react_request"] if "react_request" in state else None
    )

    response = agent.invoke({"messages": state["messages"]}, context=context)

    react_output = response["structured_response"]

    return {
        "next_agent": react_output.next_agent,
        "missing_params": react_output.missing_params,
        "react_result": react_output.result,
    }
