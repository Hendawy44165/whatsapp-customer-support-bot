from dataclasses import dataclass
from typing import Any, Dict, Literal, Optional
from langchain_core.messages import SystemMessage, AIMessage, ToolMessage
from langsmith import traceable
from langchain.agents import create_agent
from langchain.agents.middleware import after_agent
from langchain.tools import tool, ToolRuntime
from pydantic import BaseModel
from langchain.agents.structured_output import ProviderStrategy
from langgraph.checkpoint.memory import InMemorySaver

from ..state import ServiceBotState
from ..config import get_model, load_prompt
from langchain.agents.middleware import dynamic_prompt, ModelRequest


@dataclass
class QaContext:
    react_result: str | None
    missing_params: list | None
    emotion: str
    classification: str


class QaResponse(BaseModel):
    qa_directive: Literal[
        "answer", "delegate_to_react", "ask_for_params", "present_results", "escalate"
    ]
    react_request: str | None
    next_agent: Literal["react", "end"]
    user_response: str | None


@dynamic_prompt
def inject_context(request: ModelRequest) -> str:
    ctx = request.runtime.context
    base = load_prompt("qa_agent.md")
    return f"""{base}

    <context>
    emotion: {ctx.emotion}
    classification: {ctx.classification}
    react_result: {ctx.react_result}
    missing_params: {ctx.missing_params}
    </context>
    """


@after_agent
def clear_react_result(state: ServiceBotState, runtime):
    return {"react_result": None, "missing_params": []}


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
    Generates a brand-voice response for the customer.

    Handles:
    - Direct FAQ/policy answers (knowledge hardcoded in system prompt)
    - Querying product details via query_products tool
    - Parameter collection for ReAct delegation
    - Presenting ReAct tool results in brand voice
    - Escalation when unable to resolve
    """
    model = get_model()
    qa_agent = create_agent(
        model=model,
        tools=[get_products],
        checkpointer=InMemorySaver(),
        middleware=[clear_react_result, inject_context],
        response_format=QaResponse,
        context_schema=QaContext,
    )

    context = QaContext(
        react_result=state["react_result"] if "react_result" in state else None,
        missing_params=state["missing_params"] if "missing_params" in state else None,
        emotion=state["sentiment"],
        classification=state["classification"],
    )

    response = qa_agent.invoke(
        {"messages": state["messages"]},
        context=context,
    )

    qa_output = response["structured_response"]

    output = {
        "qa_directive": qa_output.qa_directive,
        "react_request": qa_output.react_request,
        "next_agent": qa_output.next_agent,
    }

    if qa_output.user_response and qa_output.user_response is not None:
        output["messages"] = [AIMessage(content=qa_output.user_response)]

    return output
