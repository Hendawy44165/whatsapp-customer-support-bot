import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from agent import CustomerServiceAgent

def main():
    agent = CustomerServiceAgent()
        
    while True:
        user_input = input().strip()
        if not user_input:
            continue
        if user_input.lower() in ['exit', 'quit', 'q']:
            break
            
        response = agent.send_message(user_input)
        print(response)

if __name__ == "__main__":
    main()
