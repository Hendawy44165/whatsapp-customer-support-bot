import os
import sys
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

# Load env variables
load_dotenv()

# Setup absolute path imports redirection for modularity (redirects 'agent' to local 'core_agent')
current_dir = os.path.dirname(os.path.abspath(__file__))
core_agent_dir = os.path.join(current_dir, "core_agent")
sys.path.insert(0, core_agent_dir)

import core_agent
sys.modules['agent'] = core_agent

# Dynamically import nested submodules so internal nodes can find absolute imports
import core_agent.state as state
import core_agent.constants as constants
import core_agent.utils as utils
import core_agent.nodes as nodes
sys.modules['agent.state'] = state
sys.modules['agent.constants'] = constants
sys.modules['agent.utils'] = utils
sys.modules['agent.nodes'] = nodes
sys.modules['agent.nodes.base'] = nodes.base

# Load our database helper client
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend.database import db

# Import CustomerServiceAgent
from core_agent.chatbot import CustomerServiceAgent

app = FastAPI(
    title="Nuit Fragrances Agent Server",
    description="Agent execution server running LangGraph state machines in isolated customer thread environments.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize global agent
agent_runner = CustomerServiceAgent()

class ChatRequest(BaseModel):
    message: str
    thread_id: str
    customer_phone: str
    platform: Optional[str] = "whatsapp"

class ChatResponse(BaseModel):
    status: str
    message: str
    is_handoff: bool
    handoff_summary: Optional[str] = ""

@app.post("/api/chat", response_model=ChatResponse)
async def execute_agent_loop(request: ChatRequest):
    """
    Simulates incoming client request (social media messages ingress hook).
    """
    conversation_id = request.thread_id

    try:
        db.add_system_log("agent_server", "INFO", f"Ingress message received from {request.customer_phone} via {request.platform}")

        # 1. Register/Load conversation in DB
        conv = db.get_conversation(conversation_id)
        if not conv:
            conv = db.create_conversation(conversation_id, request.customer_phone, request.platform)

        # Ensure conversation is not locked by human handoff
        if conv["status"] in ["handed_off"]:
            db.add_system_log("agent_server", "WARNING", f"Rejected message: Thread {conversation_id} is currently handed off to human expert.")
            return ChatResponse(
                status="ignored",
                message="Thread is currently handled by a human expert. Agent bypassed.",
                is_handoff=True,
                handoff_summary=conv.get("handoff_summary") or ""
            )

        # 2. Add customer message to read-only social messages history table
        db.add_message(
            conversation_id=conversation_id,
            sender_type="customer",
            content=request.message
        )

        # 3. Execute the isolated agent loop
        response_text = agent_runner.send_message(request.message, thread_id=conversation_id)

        # 4. Check final thread state to determine if handoff occurred
        final_state = agent_runner.get_thread_state(conversation_id)
        is_handoff = final_state.get("is_handoff", False)
        handoff_summary = final_state.get("handoff_summary", "")

        # 5. Output response securely: write to message buffer (queue)
        # In a real environment, the conversations_mcp worker polls this table and sends it to the customer.
        if is_handoff:
            # Trigger expert assignment tool dynamically
            db.queue_outbound_message(conversation_id, "Connecting you to a support specialist right away. Please hold...")
        else:
            db.queue_outbound_message(conversation_id, response_text)

        # Update conversation status if handoff occurred
        if is_handoff:
            # We also execute the handoff tool via client manager
            from backend.agent_server.mcp_client import mcp_client
            mcp_client.call_tool("human_expert", "request_human_handoff", {
                "conversation_id": conversation_id,
                "handoff_summary": handoff_summary
            })

        return ChatResponse(
            status="processed",
            message="Agent process completed successfully. Output response buffered.",
            is_handoff=is_handoff,
            handoff_summary=handoff_summary
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        db.add_system_log("agent_server", "ERROR", f"Failed executing agent loop for {conversation_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8010, reload=True)
