import json
from dataclasses import dataclass
from typing import Dict, Literal, List, Optional
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


class ActiveHypothesis(BaseModel):
    text: Optional[str] = Field(
        description="single sentence, or null if none warranted"
    )
    confidence: Optional[Literal["verified", "testable", "speculative", "null"]] = (
        Field(description="confidence level")
    )
    evidence_source: Optional[Literal["S1", "S2", "S3", "S4", "null"]] = Field(
        description="evidence source (S1, S2, S3, S4, or null)"
    )
    evidence: Optional[str] = Field(
        description="1 short sentence citing the specific evidence"
    )


class InvalidatedHypothesis(BaseModel):
    text: str
    reason_invalidated: str


class NextStep(BaseModel):
    directive: Literal[
        "answer_directly",
        "ask_clarifying_question",
        "recommend_solution",
        "confirm_execution",
        "escalate",
    ]
    content: str = Field(
        description="the question to ask, OR the solution to propose, OR the escalation note"
    )
    possible_solution: str = Field(
        description="the recommended realistic solution that should be offered to the client"
    )


class ChainStep(BaseModel):
    step: int
    why: str
    answer: str
    supported_by: str
    evidence_source: Literal["S1", "S2", "S3", "S4", "none"]


class AnalyzerResponse(BaseModel):
    model_config = {"extra": "forbid"}
    verified_facts: List[str] = Field(description="max 5 short items")
    policy_grounding: str = Field(
        description="1-3 sentences, quote/paraphrase from context or tools only"
    )
    pain_points: List[str] = Field(description="max 5 short pain points")
    root_cause_chain: List[ChainStep] = Field(description="5 Whys root cause chain")
    chain_status: Literal["terminated_at_root", "terminated_no_support", "max_depth_reached"]
    active_hypothesis: Optional[ActiveHypothesis] = Field(
        description="active hypothesis model"
    )
    invalidated_hypotheses: List[InvalidatedHypothesis] = Field(
        description="list of invalidated hypotheses"
    )
    next_step: NextStep = Field(description="next routing/content step")


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
    directive = analyzer_output.next_step.directive

    # Serialize the inner monologue fields into a single JSON string for state notes
    inner_monologue = {
        "verified_facts": analyzer_output.verified_facts,
        "policy_grounding": analyzer_output.policy_grounding,
        "pain_points": analyzer_output.pain_points,
        "root_cause_chain": [
            {
                "step": step.step,
                "why": step.why,
                "answer": step.answer,
                "supported_by": step.supported_by,
                "evidence_source": step.evidence_source,
            }
            for step in analyzer_output.root_cause_chain
        ],
        "chain_status": analyzer_output.chain_status,
        "active_hypothesis": (
            {
                "text": (
                    analyzer_output.active_hypothesis.text
                    if analyzer_output.active_hypothesis
                    else None
                ),
                "confidence": (
                    analyzer_output.active_hypothesis.confidence
                    if analyzer_output.active_hypothesis
                    else None
                ),
                "evidence_source": (
                    analyzer_output.active_hypothesis.evidence_source
                    if analyzer_output.active_hypothesis
                    else None
                ),
                "evidence": (
                    analyzer_output.active_hypothesis.evidence
                    if analyzer_output.active_hypothesis
                    else None
                ),
            }
            if analyzer_output.active_hypothesis
            else None
        ),
        "invalidated_hypotheses": [
            {"text": h.text, "reason_invalidated": h.reason_invalidated}
            for h in analyzer_output.invalidated_hypotheses
        ],
        "next_step": {
            "directive": analyzer_output.next_step.directive,
            "content": analyzer_output.next_step.content,
            "possible_solution": analyzer_output.next_step.possible_solution,
        },
    }
    notes_str = json.dumps(inner_monologue, indent=2)

    if directive == "escalate":
        next_agent = "escalate"
    elif directive == "answer_directly":
        return {
            "notes": notes_str,
            "messages": [AIMessage(content=state.get("simple_qa_response") or "")],
            "directive": directive,
            "next_agent": "end",
        }
    else:
        next_agent = "need_qa"

    return {
        "notes": notes_str,
        "directive": directive,
        "next_agent": next_agent,
    }
