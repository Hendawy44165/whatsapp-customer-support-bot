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


def main():
    session_id = str(uuid.uuid4())

    print("=" * 60)
    print("  NUIT FRAGRANCES — Customer Support Bot v2")
    print(f"  Session: {session_id}")
    print("  Type 'quit' to exit | 'state' to inspect thread state")
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

        response = bot.send_message(user_input, thread_id=session_id)
        print(f"\nNuit: {response}\n")


if __name__ == "__main__":
    main()
