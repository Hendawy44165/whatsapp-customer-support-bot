from typing import Literal

from langsmith import traceable
from langchain.agents import create_agent
from langgraph.checkpoint.memory import InMemorySaver
from pydantic import BaseModel

from ..state import ServiceBotState
from ..config import get_model, load_prompt


class RouterResponse(BaseModel):
    next_agent: Literal[
        "simple_qa",
        "executer",
        "escalate",
        "blocker",
        "end",
        "analyzer",
        "need_qa",
    ]
    sentiment: str


@traceable
def router_node(state: ServiceBotState) -> dict:
    model = get_model()
    system_prompt = load_prompt("router.md")

    router_agent = create_agent(
        model=model,
        system_prompt=system_prompt,
        checkpointer=InMemorySaver(),
        response_format=RouterResponse,
    )

    response = router_agent.invoke({"messages": state["messages"]})

    router_output = response["structured_response"]

    return {
        "next_agent": router_output.next_agent,
        "sentiment": router_output.sentiment,
    }
