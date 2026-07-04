"""
Nuit Bot v2 — CLI Chat Interface

Interactive terminal chat with UUID-based session threading.
Useful for manual testing and development.
"""

import os
import sys
import uuid

from dotenv import load_dotenv

# Ensure the backend directory is in the import path
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

load_dotenv()

from core_agent.graph import NuitBot


def _format_state_summary(state: dict) -> str:
    """Format key state fields for quick debugging."""
    parts = []

    router = state.get("router_output")
    if router:
        sentiment = getattr(router, "sentiment", None) or (router.get("sentiment") if isinstance(router, dict) else None)
        classification = getattr(router, "classification", None) or (router.get("classification") if isinstance(router, dict) else None)
        next_agent = getattr(router, "next_agent", None) or (router.get("next_agent") if isinstance(router, dict) else None)
        parts.append(f"Route: {next_agent} | Sentiment: {sentiment} | Intent: {classification}")

    directive = state.get("qa_directive")
    if directive and directive != "answer":
        parts.append(f"QA Directive: {directive}")

    react = state.get("react_result")
    if react:
        status = getattr(react, "status", None) or (react.get("status") if isinstance(react, dict) else None)
        if status:
            parts.append(f"ReAct: {status}")

    user_info = state.get("learned_user_info", {})
    if user_info:
        parts.append(f"CRM: {user_info}")

    escalation = state.get("escalation_report")
    if escalation:
        parts.append("⚠ ESCALATED")

    return " | ".join(parts) if parts else ""


def main():
    session_id = str(uuid.uuid4())

    print("=" * 60)
    print("  NUIT FRAGRANCES — Customer Support Bot v2")
    print(f"  Session: {session_id}")
    print("  Commands: 'quit' | 'state' | 'crm'")
    print("=" * 60)
    print()

    bot = NuitBot()

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n\nSession ended.")
            break

        if not user_input:
            continue

        if user_input.lower() in ("exit", "quit", "q"):
            print("\nSession ended.")
            break

        if user_input.lower() == "state":
            state = bot.get_thread_state(session_id)
            print("\n--- Thread State ---")
            for key, value in state.items():
                if key == "messages":
                    print(f"  messages: [{len(value)} messages]")
                else:
                    print(f"  {key}: {value}")
            print("-------------------\n")
            continue

        if user_input.lower() == "crm":
            from core_agent.tools import MOCK_CRM_PROFILES, ESCALATION_QUEUE
            print("\n--- Mock CRM Profiles ---")
            if MOCK_CRM_PROFILES:
                for phone, profile in MOCK_CRM_PROFILES.items():
                    print(f"  {phone}: {profile}")
            else:
                print("  (empty)")
            print(f"\n--- Escalation Queue ({len(ESCALATION_QUEUE)} items) ---")
            for i, report in enumerate(ESCALATION_QUEUE):
                print(f"  [{i}] {report.get('reason', '?')} | urgency={report.get('urgency', '?')} | {report.get('chat_summary', '')}")
            print("-------------------\n")
            continue

        response = bot.send_message(user_input, thread_id=session_id)

        # Show routing debug info
        state = bot.get_thread_state(session_id)
        debug = _format_state_summary(state)
        if debug:
            print(f"  [{debug}]")

        print(f"\nNuit: {response}\n")


if __name__ == "__main__":
    main()
