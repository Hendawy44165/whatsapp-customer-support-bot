"""
CRM auto-update node — extracts user info from conversation and updates CRM.
Runs after QA produces final response, before END.
Only fires an LLM call if the conversation has enough substance to extract from.
"""

from typing import Dict
from langchain_core.messages import SystemMessage, HumanMessage
from langsmith import traceable

from ..state import AgentState, ExtractedUserInfo
from ..config import get_model, load_prompt
from ..tools import update_crm_profile


def _has_human_messages(state: AgentState) -> bool:
    """Check if the conversation has any human messages worth extracting from."""
    messages = state.get("messages", [])
    human_msgs = [m for m in messages if isinstance(m, HumanMessage)]
    if not human_msgs:
        return False

    # Skip if all human messages are very short (greetings, single words)
    total_chars = sum(len(m.content) for m in human_msgs)
    return total_chars > 15


def _merge_user_info(existing: dict, new_info: ExtractedUserInfo) -> dict:
    """
    Merge newly extracted info into existing learned_user_info.
    Only adds genuinely new data — does not overwrite with None.
    """
    merged = dict(existing)

    if new_info.name and new_info.name != merged.get("name"):
        merged["name"] = new_info.name

    if new_info.phone and new_info.phone != merged.get("phone"):
        merged["phone"] = new_info.phone

    if new_info.delivery_zone and new_info.delivery_zone != merged.get("delivery_zone"):
        merged["delivery_zone"] = new_info.delivery_zone

    # Append new order IDs (deduplicate)
    existing_orders = set(merged.get("order_ids", []))
    for oid in new_info.order_ids:
        existing_orders.add(oid)
    if existing_orders:
        merged["order_ids"] = sorted(existing_orders)

    # Append new product preferences (deduplicate)
    existing_prefs = set(merged.get("product_preferences", []))
    for pref in new_info.product_preferences:
        existing_prefs.add(pref)
    if existing_prefs:
        merged["product_preferences"] = sorted(existing_prefs)

    return merged


@traceable(name="crm_updater_node")
def crm_updater_node(state: AgentState) -> Dict:
    """
    Extracts new user info from the conversation and updates the mock CRM.
    
    Skips the LLM call entirely if:
    - No human messages in the conversation
    - Messages are too short to contain useful info
    """
    # Skip if no meaningful human messages
    if not _has_human_messages(state):
        return {}

    model = get_model()
    system_prompt = load_prompt("crm_extractor.md")

    # Build messages for extraction
    messages = state.get("messages", [])
    llm_messages = [SystemMessage(content=system_prompt)] + list(messages)

    # Structured output extraction
    structured_model = model.with_structured_output(ExtractedUserInfo)

    try:
        extracted = structured_model.invoke(llm_messages)
    except Exception:
        # If extraction fails, silently skip — CRM update is not critical
        return {}

    # Only update if there's genuinely new info
    if not extracted.has_new_info:
        return {}

    # Merge with existing info
    existing_info = state.get("learned_user_info", {})
    merged = _merge_user_info(existing_info, extracted)

    # Check if anything actually changed
    if merged == existing_info:
        return {}

    # Write to mock CRM
    phone = merged.get("phone")
    if phone:
        update_crm_profile(phone, merged)

    return {"learned_user_info": merged}
