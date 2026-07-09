from typing import Dict, Any
from langchain_core.messages import SystemMessage, HumanMessage
from langsmith import traceable
from langchain.agents import create_agent
from langgraph.checkpoint.memory import InMemorySaver
from pydantic import BaseModel
from langchain.agents.structured_output import ProviderStrategy

from ..state import ServiceBotState
from ..config import get_model, load_prompt, THREAD_ID


class RouterResponse(BaseModel):
    next_agent: str
    sentiment: str
    classification: str
    extracted_parameters: dict


@traceable(name="router_node")
def router_node(state: ServiceBotState) -> Dict:
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
        "classification": router_output.classification,
        "extracted_parameters": router_output.extracted_parameters,
    }
