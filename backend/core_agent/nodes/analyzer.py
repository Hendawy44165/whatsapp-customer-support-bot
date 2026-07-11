from dataclasses import dataclass
from typing import Dict, Literal, List
from langsmith import traceable
from langchain_core.messages import AIMessage
from langchain.agents import create_agent
from langgraph.checkpoint.memory import InMemorySaver
from langchain.agents.middleware import dynamic_prompt, ModelRequest
from pydantic import BaseModel, Field

from ..state import ServiceBotState
from ..config import get_model, load_prompt
from ..tools import (
    lookup_crm_profile,
    lookup_order,
    query_products,
    register_return,
    register_exchange,
)


@dataclass
class AnalyzerContext:
    simple_qa_response: str | None
    old_notes: str | None


class AnalyzerResponse(BaseModel):
    notes: str = Field(
        description="Unstructured bullet points tracking client variables/needs."
    )
    directive: Literal[
        "answer_directly",
        "ask_clarifying_question",
        "recommend_solution",
        "confirm_execution",
        "escalate",
    ] = Field(description="The next logical action step.")


@dynamic_prompt
def inject_analyzer_context(request: ModelRequest) -> str:
    ctx = request.runtime.context
    base = load_prompt("analyzer.md")
    return f"""{base}

    <context>
    Direct QA Response Cache: {ctx.simple_qa_response or "None"}
    Old Notes: {ctx.old_notes or "None"}
    </context>
    """


@traceable(name="analyzer_node")
def analyzer_node(state: ServiceBotState) -> Dict:
    model = get_model()

    # Expose tools for the analyzer to query CRM details and execute orders
    analyzer_agent = create_agent(
        model=model,
        tools=[
            lookup_crm_profile,
            lookup_order,
            query_products,
            register_return,
            register_exchange,
        ],
        checkpointer=InMemorySaver(),
        middleware=[inject_analyzer_context],
        response_format=AnalyzerResponse,
        context_schema=AnalyzerContext,
    )

    context = AnalyzerContext(
        simple_qa_response=state.get("simple_qa_response", ""),
        old_notes=state.get("notes", ""),
    )

    response = analyzer_agent.invoke(
        {"messages": state["messages"]},
        context=context,
    )

    analyzer_output = response["structured_response"]
    directive = analyzer_output.directive

    if directive == "escalate":
        next_agent = "escalate"
    elif directive == "answer_directly":
        return {
            "notes": analyzer_output.notes,
            "messages": [AIMessage(content=state.get("simple_qa_response") or "")],
            "directive": directive,
            "next_agent": "end",
        }
    else:
        next_agent = "need_qa"

    return {
        "notes": analyzer_output.notes or None,
        "directive": directive,
        "next_agent": next_agent,
    }
