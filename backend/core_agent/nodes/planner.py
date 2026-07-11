import os
from typing import Dict, Any
from dataclasses import dataclass
from pydantic import BaseModel, Field
from typing import Literal
from langsmith import traceable
from langchain.agents import create_agent
from langgraph.checkpoint.memory import InMemorySaver
from langchain.agents.middleware import dynamic_prompt, ModelRequest

from ..state import ServiceBotState
from ..config import get_model, load_prompt, parse_frontmatter


@dataclass
class PlannerContext:
    sop_name: str
    sop_body: str
    required_docs: list[str]
    required_tools: list[str]
    sentiment: str
    classification: str
    executer_report: str


class PlannerResponse(BaseModel):
    model_config = {"extra": "forbid"}
    planner_command: str = Field(
        description=(
            "The plain text diagnosis, gathered details, overall strategy, "
            "and active step-by-step instructions for the executer to perform in this turn."
        )
    )
    required_docs: list[str] = Field(description="Required SOP documents to load.")
    next_agent: Literal["executer"] = Field(description="Always set to executer.")


@dynamic_prompt
def inject_planner_context(request: ModelRequest) -> str:
    ctx = request.runtime.context
    base = load_prompt("planner.md")
    return f"""{base}

<active_framework>
<sop_name>{ctx.sop_name}</sop_name>
<required_docs>{ctx.required_docs}</required_docs>
<required_tools>{ctx.required_tools}</required_tools>
<sop_body>
{ctx.sop_body}
</sop_body>
</active_framework>

<current_state>
<sentiment>{ctx.sentiment}</sentiment>
<intent_classification>{ctx.classification}</intent_classification>
<executer_report>
{ctx.executer_report or "No report from previous executer node execution."}
</executer_report>
</current_state>
"""


@traceable(name="planner_node")
def planner_node(state: ServiceBotState) -> Dict:
    # 1. Resolve framework file based on router classification
    classification = state.get("classification", "").lower()

    if "return" in classification or "exchange" in classification:
        filename = "return_exchange_framework.md"
    elif (
        "tracking" in classification
        or "shipping" in classification
        or "wismo" in classification
    ):
        filename = "order_tracking_framework.md"
    else:
        filename = "general_support_framework.md"

    # Load framework file, parse frontmatter, and extract SOP body
    docs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "docs")
    framework_path = os.path.join(docs_dir, filename)

    sop_name = "Unknown Framework"
    sop_body = ""
    required_docs = []
    required_tools = []

    if os.path.exists(framework_path):
        with open(framework_path, "r", encoding="utf-8") as f:
            content = f.read()
        metadata = parse_frontmatter(content)
        sop_name = metadata.get("sop_name", sop_name)
        required_docs = metadata.get("required_docs", required_docs)
        required_tools = metadata.get("required_tools", required_tools)
        # Extract body — everything after the closing frontmatter ---
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                sop_body = parts[2].strip()

    # 2. Build model and Planner agent
    model = get_model()
    planner_agent = create_agent(
        model=model,
        checkpointer=InMemorySaver(),
        response_format=PlannerResponse,
        middleware=[inject_planner_context],
        context_schema=PlannerContext,
    )

    # Prepare context dataclass
    context = PlannerContext(
        sop_name=sop_name,
        sop_body=sop_body,
        required_docs=required_docs,
        required_tools=required_tools,
        sentiment=state.get("sentiment", "neutral"),
        classification=state.get("classification", "general_inquiry"),
        executer_report=state.get("executer_report", ""),
    )

    # Invoke agent
    response = planner_agent.invoke(
        {"messages": state["messages"]},
        context=context,
    )

    planner_output = response["structured_response"]

    # Initialize gathered parameters/info if empty
    gathered_params = state.get("gathered_parameters") or {}
    # Merge newly extracted parameters from router into gathered parameters
    extracted_params = state.get("extracted_parameters") or {}
    for k, v in extracted_params.items():
        if v:
            gathered_params[k] = v

    # Return planner command and clear executer_report (acting as post-planner middleware)
    return {
        "planner_command": planner_output.planner_command,
        "required_docs": planner_output.required_docs,
        "next_agent": planner_output.next_agent,
        "executer_report": "",  # Clear the report to avoid infinite loop
    }
