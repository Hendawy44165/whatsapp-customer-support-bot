from dataclasses import dataclass
from typing import Dict, Literal
from langchain_core.messages import AIMessage
from langsmith import traceable
from langchain.agents import create_agent
from langchain.tools import tool
from pydantic import BaseModel, Field
from langgraph.checkpoint.memory import InMemorySaver
from langchain.agents.middleware import dynamic_prompt, ModelRequest

from ..state import ServiceBotState
from ..config import get_model, load_prompt


@dataclass
class QaContext:
    sentiment: str
    classification: str


class QaResponse(BaseModel):
    model_config = {"extra": "forbid"}
    user_response: str = Field(
        description="The response message to send to the customer on WhatsApp."
    )
    next_agent: Literal["end"] = Field(description="Always set to end.")


@dynamic_prompt
def inject_context(request: ModelRequest) -> str:
    ctx = request.runtime.context
    base = load_prompt("qa_agent.md")
    return f"""{base}

    <context>
    Sentiment: {ctx.sentiment}
    Classification: {ctx.classification}
    </context>
    """


@tool
def get_products() -> dict:
    """Tool to query product details."""
    return {
        "flagship_edp_50ml": {
            "name": "Flagship Eau de Parfum (EDP) — 50ml",
            "standard_price": "EGP 855.00",
            "promo_price": "EGP 599.00",
            "variants": [
                "Rum",
                "Dulce de Leche",
                "Head Turner",
                "Born in Milano",
                "Born in Vegas",
                "Bounty Hunter",
                "Red Flag",
                "Green Flag",
                "Espresso Martini",
                "Forbidden Fruit",
                "Casa Di Rosa",
                "Lindo Día",
                "Monroe",
                "Warm Vanilla",
                "French Foulard",
                "True Hipster",
                "Leather Jacket",
                "Cappuccina",
                "Choco Frappe",
                "Hazelwood",
                "Heritage",
                "I am Harvey",
            ],
        },
        "luxury_collaboration": {
            "name": "Avec Hatshepsut (Nuit X Temraza)",
            "price": "EGP 1,950.00",
            "notes": "exclusive art flacon, NOT eligible for standard EDP discounts",
        },
        "perfume_oils_shots_khamrias": {
            "name": "Concentrated Perfume Oils (Shots) & Khamrias",
            "price": "EGP 475.00",
            "examples": [
                "Vanilla Shot",
                "Born in Milano Shot",
                "Caramel Shot",
                "Head Turner Shot",
            ],
        },
        "body_splash_mists": {
            "name": "Body Splash & Mists",
            "price": "EGP 315.00",
            "examples": [
                "Soft Cloud Heart",
                "Very Delicate Vanilla",
                "The Harvey Splash",
            ],
        },
    }


@traceable(name="qa_agent_node")
def qa_agent_node(state: ServiceBotState) -> Dict:
    """
    Generates a brand-voice response for the customer answering simple policy,
    product, or brand questions.
    """
    model = get_model()
    qa_agent = create_agent(
        model=model,
        tools=[get_products],
        checkpointer=InMemorySaver(),
        middleware=[inject_context],
        response_format=QaResponse,
        context_schema=QaContext,
    )

    context = QaContext(
        sentiment=state.get("sentiment", "neutral"),
        classification=state.get("classification", "general_inquiry"),
    )

    response = qa_agent.invoke(
        {"messages": state["messages"]},
        context=context,
    )

    qa_output = response["structured_response"]

    output = {
        "next_agent": qa_output.next_agent,
    }

    if qa_output.user_response:
        output["messages"] = [AIMessage(content=qa_output.user_response)]

    return output
