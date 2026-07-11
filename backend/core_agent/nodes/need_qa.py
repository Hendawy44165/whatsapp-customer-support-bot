from dataclasses import dataclass
from typing import Dict, Literal
from langchain_core.messages import AIMessage
from langsmith import traceable
from langchain.agents import create_agent
from pydantic import BaseModel, Field
from langgraph.checkpoint.memory import InMemorySaver
from langchain.agents.middleware import dynamic_prompt, ModelRequest

from ..state import ServiceBotState, AnalyzerMetadata
from ..config import get_model, load_prompt


@dataclass
class NeedQaContext:
    simple_qa_response: str
    directive: str
    notes: str


class NeedQaResponse(BaseModel):
    user_response: str = Field(
        description="The response message to send to the customer on WhatsApp."
    )
    next_agent: Literal["end"] = Field(description="Always set to end.")


@dynamic_prompt
def inject_need_qa_context(request: ModelRequest) -> str:
    ctx = request.runtime.context
    base = load_prompt("need_qa.md")
    return f"""{base}

    <context>
    Direct QA Response: {ctx.simple_qa_response or "None"}
    Analyzer Notes: {ctx.notes or "None"}
    Active Directive: {ctx.directive}
    </context>
    """


@traceable(name="need_qa_node")
def need_qa_node(state: ServiceBotState) -> Dict:
    """
    Combines the direct QA answer and the analyzer's workaround or clarifying questions
    into a single cohesive brand-voice message.
    """
    model = get_model()
    need_qa_agent = create_agent(
        model=model,
        checkpointer=InMemorySaver(),
        middleware=[inject_need_qa_context],
        response_format=NeedQaResponse,
        context_schema=NeedQaContext,
    )

    directive = state.get("directive", "")
    if directive == "" or directive == "answer_directly":
        return {
            "next_agent": "end",
            "messages": [AIMessage(content=state.get("simple_qa_response", ""))],
        }

    context = NeedQaContext(
        simple_qa_response=state.get("simple_qa_response", ""),
        directive=state.get("directive", "answer_directly"),
        notes=state.get("notes", ""),
    )

    response = need_qa_agent.invoke(
        {"messages": state["messages"]},
        context=context,
    )

    structured_output = response["structured_response"]

    output = {
        "next_agent": structured_output.next_agent,
    }

    if structured_output.user_response:
        output["messages"] = [AIMessage(content=structured_output.user_response)]

    return output
