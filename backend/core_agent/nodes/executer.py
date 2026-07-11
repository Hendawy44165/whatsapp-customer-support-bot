import os
from typing import Dict, Any
from dataclasses import dataclass
from pydantic import BaseModel, Field
from typing import Literal
from langsmith import traceable
from langchain.agents import create_agent
from langchain.tools import tool
from langgraph.checkpoint.memory import InMemorySaver
from langchain.agents.middleware import dynamic_prompt, ModelRequest
from langchain_core.messages import AIMessage

from ..state import ServiceBotState
from ..config import get_model, load_prompt, parse_frontmatter
from ..tools import query_products, lookup_order, register_return, register_exchange


@dataclass
class executerContext:
    required_docs: list[str]
    planner_command: str
    gathered_parameters: dict[str, Any]
    gathered_information: list[str]


class GatheredParameters(BaseModel):
    model_config = {"extra": "forbid"}
    order_id: str | None = None
    phone: str | None = None
    email: str | None = None
    product_name: str | None = None
    product_size: str | None = None
    reason: str | None = None
    new_item: str | None = None


class executerResponse(BaseModel):
    model_config = {"extra": "forbid"}
    executer_report: str = Field(
        description="A plain text report summarizing what you did, what tools you called, what you found, and what parameters you updated/saved."
    )
    gathered_parameters: GatheredParameters = Field(
        description="All gathered parameters so far."
    )
    gathered_information: list[str] = Field(
        description="Key verified facts or information gathered."
    )
    next_agent: Literal["planner", "escalate", "end"] = Field(
        description="Routing choice: 'planner' to advance, 'escalate' to handoff, 'end' to pause/finish."
    )
    new_message: str = Field(
        description="The message to send to the customer on WhatsApp (leave empty if no message is to be sent)."
    )
    missing_params: list[str] | None = Field(
        default=None,
        description="List of parameters currently missing and being asked for in this turn (e.g. ['order_id']).",
    )


@dynamic_prompt
def inject_executer_context(request: ModelRequest) -> str:
    ctx = request.runtime.context
    base_prompt = load_prompt("executer.md")

    # Loader Middleware: load SOP documents dynamically
    injected_docs = []
    docs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "docs")
    for doc_name in ctx.required_docs:
        doc_path = os.path.join(docs_dir, doc_name)
        if os.path.exists(doc_path):
            try:
                with open(doc_path, "r", encoding="utf-8") as f:
                    content = f.read()
                # Clean out YAML frontmatter if present
                if content.startswith("---"):
                    parts = content.split("---", 2)
                    if len(parts) >= 3:
                        content = parts[2]
                injected_docs.append(f"### DOCUMENT: {doc_name}\n{content.strip()}")
            except Exception as e:
                injected_docs.append(f"### DOCUMENT: {doc_name} (Failed to load: {e})")
        else:
            injected_docs.append(f"### DOCUMENT: {doc_name} (Not found on disk)")

    docs_injection = "\n\n".join(injected_docs)

    return f"""{base_prompt}

    ## DYNAMIC CONTEXT
    <injected_sop_documents>
    {docs_injection}
    </injected_sop_documents>

    <active_plan>
    {ctx.planner_command or "No active instructions from planner."}
    </active_plan>

    <gathered_data>
    Gathered Parameters: {ctx.gathered_parameters}
    Gathered Information: {ctx.gathered_information}
    </gathered_data>
    """


@traceable(name="executer_node")
def executer_node(state: ServiceBotState) -> Dict:
    # 1. Resolve framework file based on router classification to get SOP details
    classification = state.get("classification", "").lower()

    # Read required_docs from state if planner populated it; fallback to resolved file
    required_docs = state.get("required_docs") or []
    if not required_docs:
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

        docs_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "..", "docs"
        )
        framework_path = os.path.join(docs_dir, filename)

        if os.path.exists(framework_path):
            with open(framework_path, "r", encoding="utf-8") as f:
                content = f.read()
            metadata = parse_frontmatter(content)
            required_docs = metadata.get("required_docs", required_docs)

    # 2. Build model and executer agent
    model = get_model()

    # executer has access to all CRM tools
    all_tools = [query_products, lookup_order, register_return, register_exchange]

    executer_agent = create_agent(
        model=model,
        tools=all_tools,
        checkpointer=InMemorySaver(),
        response_format=executerResponse,
        middleware=[inject_executer_context],
        context_schema=executerContext,
    )

    # Prepare context dataclass
    context = executerContext(
        required_docs=required_docs,
        planner_command=state.get("planner_command", ""),
        gathered_parameters=state.get("gathered_parameters", {}),
        gathered_information=state.get("gathered_information", []),
    )

    # Invoke agent
    response = executer_agent.invoke(
        {"messages": state["messages"]},
        context=context,
    )

    executer_output = response["structured_response"]

    gathered_params_dict = executer_output.gathered_parameters.model_dump()
    clean_params = {k: v for k, v in gathered_params_dict.items() if v is not None}

    output = {
        "executer_report": executer_output.executer_report,
        "gathered_parameters": clean_params,
        "gathered_information": executer_output.gathered_information,
        "next_agent": executer_output.next_agent,
        "planner_command": "",  # Clear the planner command to avoid loop (post-executer middleware)
        "missing_params": executer_output.missing_params or [],
    }

    if executer_output.new_message:
        output["messages"] = [AIMessage(content=executer_output.new_message)]

    return output
