import os
import sys
from dotenv import load_dotenv

# Ensure the backend directory is in the import path
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from core_agent.chatbot import CustomerServiceAgent

load_dotenv()



def main():
    agent = CustomerServiceAgent()

    while True:
        user_input = input().strip()
        if not user_input:
            continue
        if user_input.lower() in ["exit", "quit", "q"]:
            break

        response = agent.send_message(user_input)
        print(response)


if __name__ == "__main__":
    main()
