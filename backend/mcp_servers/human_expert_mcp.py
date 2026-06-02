import os
import sys
from typing import Dict, Any, List
from pydantic import BaseModel
from mcp.server.fastmcp import FastMCP

# Add parent directory to path to import database
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import db

# Create FastMCP instance
mcp = FastMCP("Nuit Human Expert Routing")

# Access the underlying ASGI / FastAPI app
app = mcp.asgi_app

# --- Models ---
class HandoffRequest(BaseModel):
    conversation_id: str
    handoff_summary: str

class ClaimRequest(BaseModel):
    expert_id: str

# --- MCP Tool ---
@mcp.tool()
def request_human_handoff(conversation_id: str, handoff_summary: str) -> str:
    """
    Triggers the handoff pipeline for a conversation thread.
    Saves the summary, sets status to pending_handoff, and attempts automatic routing.
    """
    try:
        db.add_system_log("human_expert_mcp", "INFO", f"Handoff requested for conversation {conversation_id}")
        
        # 1. Update conversation status to pending_handoff and save summary
        db.update_conversation(conversation_id, {
            "status": "pending_handoff",
            "handoff_summary": handoff_summary
        })

        # 2. Attempt automatic load-based assignment
        experts = db.get_experts()
        online_experts = [e for e in experts if e["status"] == "online"]

        if online_experts:
            # Sort by current_load ascending (least loaded first)
            online_experts.sort(key=lambda x: x["current_load"])
            assigned_expert = online_experts[0]
            
            # Update conversation to handed_off and assign to the expert
            db.update_conversation(conversation_id, {
                "status": "handed_off",
                "assigned_expert_id": assigned_expert["id"]
            })
            
            db.add_system_log(
                "human_expert_mcp", 
                "INFO", 
                f"Conversation {conversation_id} automatically assigned to expert {assigned_expert['name']} (Load: {assigned_expert['current_load']})"
            )
            
            return (
                f"Handoff success!\n"
                f"- Assigned Expert: {assigned_expert['name']}\n"
                f"- Deep Link Redirect: {assigned_expert['chat_redirect_url']}\n"
                f"Customer chat has been locked for the expert."
            )
        else:
            db.add_system_log("human_expert_mcp", "WARNING", f"No online experts available. Conversation {conversation_id} added to the pending queue.")
            return "No online support experts are currently active. Conversation has been placed in the Shared Pending Queue."
            
    except Exception as e:
        db.add_system_log("human_expert_mcp", "ERROR", f"Error in handoff execution for {conversation_id}: {str(e)}")
        return f"Error executing handoff routing: {str(e)}"

# --- REST Endpoints for the Human Expert Frontend ---

@app.get("/api/expert/conversations")
async def get_expert_conversations(expert_id: str = None):
    """
    Retrieve conversations:
    - If expert_id is provided, returns their active assigned chats.
    - Also returns the shared pending queue (chats in 'pending_handoff' status).
    """
    try:
        all_convs = db.get_conversations()
        assigned_chats = []
        pending_queue = []

        for c in all_convs:
            if c["status"] == "pending_handoff":
                pending_queue.append(c)
            elif c["status"] == "handed_off" and c["assigned_expert_id"] == expert_id:
                assigned_chats.append(c)

        return {
            "assigned_conversations": assigned_chats,
            "shared_pending_queue": pending_queue
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/expert/claim/{conversation_id}")
async def claim_conversation(conversation_id: str, request: ClaimRequest):
    """
    Manually claim a conversation from the pending queue.
    """
    try:
        conv = db.get_conversation(conversation_id)
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        if conv["status"] != "pending_handoff":
            return {"status": "error", "message": f"Conversation is already {conv['status']}"}

        expert = db.get_expert(request.expert_id)
        if not expert:
            raise HTTPException(status_code=404, detail="Expert profile not found")

        # Assign the conversation to this expert and change status to handed_off
        db.update_conversation(conversation_id, {
            "status": "handed_off",
            "assigned_expert_id": request.expert_id
        })

        db.add_system_log("human_expert_mcp", "INFO", f"Expert {expert['name']} manually claimed conversation {conversation_id}")
        return {
            "status": "success", 
            "message": f"Successfully claimed conversation",
            "chat_redirect_url": expert["chat_redirect_url"]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/expert/resolve/{conversation_id}")
async def resolve_conversation(conversation_id: str):
    """
    Mark conversation as resolved, freeing up expert capacity.
    """
    try:
        conv = db.get_conversation(conversation_id)
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")

        db.update_conversation(conversation_id, {
            "status": "resolved"
        })

        db.add_system_log("human_expert_mcp", "INFO", f"Conversation {conversation_id} resolved by expert.")
        return {"status": "success", "message": "Conversation resolved successfully."}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/expert/profiles")
async def list_experts():
    """Retrieve lists of experts and their current loads."""
    try:
        return db.get_experts()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8014)
