import os
from dataclasses import dataclass
from typing import Literal
from langsmith import traceable
from langchain.agents import create_agent
from langchain.tools import tool
from pydantic import BaseModel, Field
from langgraph.checkpoint.memory import InMemorySaver
from langchain.agents.middleware import dynamic_prompt, ModelRequest

from langchain_core.messages import AIMessage
from ..state import ServiceBotState
from ..config import get_model, load_prompt
from ..tools import query_products_sql, get_product_details, search_products_by_description, lookup_order


@dataclass
class QaContext:
    sentiment: str
    kb_context: str = ""


def load_all_documents() -> str:
    """Read and combine all 3 brand policies and information documents."""
    docs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "docs")
    filenames = ["terms_of_conditions_and_policies.md", "faq.md", "brand_identity.md"]
    combined = []

    for filename in filenames:
        doc_path = os.path.join(docs_dir, filename)
        if os.path.exists(doc_path):
            try:
                with open(doc_path, "r", encoding="utf-8") as f:
                    content = f.read()
                # Clean out YAML frontmatter if present
                if content.startswith("---"):
                    parts = content.split("---", 2)
                    if len(parts) >= 3:
                        content = parts[2]
                content = content.strip()
                combined.append(f'<document name="{filename}">\n{content}\n</document>')
            except Exception as e:
                combined.append(
                    f'<document name="{filename}">\nFailed to load: {e}\n</document>'
                )

    return "\n\n".join(combined)


class QaResponse(BaseModel):
    model_config = {"extra": "forbid"}
    user_response: str = Field(
        description="The response message to send to the customer on WhatsApp."
    )
    next_agent: Literal["end"] = Field(description="Always set to end.")


@dynamic_prompt
def inject_context(request: ModelRequest) -> str:
    ctx = request.runtime.context
    base = load_prompt("simple_qa.md")

    injected = f"""{base}

    <context>
    Sentiment: {ctx.sentiment}
    </context>
    """

    if getattr(ctx, "kb_context", None):
        injected += f"""
    <retrieved_document>
    {ctx.kb_context}
    </retrieved_document>
    """
    return injected


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


@traceable
def simple_qa_node(state: ServiceBotState) -> dict:
    kb_context = load_all_documents()

    model = get_model()
    qa_agent = create_agent(
        model=model,
        tools=[query_products_sql, get_product_details, search_products_by_description, lookup_order],
        checkpointer=InMemorySaver(),
        middleware=[inject_context],
        response_format=QaResponse,
        context_schema=QaContext,
    )

    context = QaContext(
        sentiment=state.get("sentiment", "neutral"),
        kb_context=kb_context,
    )

    response = qa_agent.invoke(
        {"messages": state["messages"]},
        context=context,
    )

    qa_output = response["structured_response"]

    return {
        "messages": [AIMessage(content=qa_output.user_response or "")],
        "next_agent": "end",
    }
