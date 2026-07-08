import os
import sys
import json
import uuid
import datetime
import threading
import time
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

# Ensure backend folder is in path
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# Load env variables from backend folder
load_dotenv(os.path.join(backend_dir, ".env"))

# Setup dynamic path redirection for backward compatibility of 'agent' imports
core_agent_dir = os.path.join(backend_dir, "core_agent")
if core_agent_dir not in sys.path:
    sys.path.insert(0, core_agent_dir)

import core_agent
sys.modules['agent'] = core_agent

import core_agent.state as state
import core_agent.constants as constants
import core_agent.utils as utils
import core_agent.nodes as nodes
sys.modules['agent.state'] = state
sys.modules['agent.constants'] = constants
sys.modules['agent.utils'] = utils
sys.modules['agent.nodes'] = nodes

# Load our database helper client
from database import db

# Import NuitBot as CustomerServiceAgent for backward compatibility
from core_agent import NuitBot as CustomerServiceAgent

# --- LifeSpan Manager for background Outbound queue worker thread ---
is_worker_running = True
worker_thread = None

def run_outbound_queue_worker():
    """
    Background worker thread polling the message_buffer table.
    Dispatches pending messages when scheduled_for is reached.
    """
    global is_worker_running
    logger_context = "outbound_worker"
    db.add_system_log(logger_context, "INFO", "Outbound queue worker started.")
    
    while is_worker_running:
        try:
            pending = db.get_pending_buffered_messages()
            for msg in pending:
                if not is_worker_running:
                    break
                
                db.add_system_log(logger_context, "INFO", f"Processing buffered message ID {msg['id']} for conversation {msg['conversation_id']}")
                
                # Simulation output
                print(f"\n[OUTBOUND MESSAGE DISPATCHED - {msg['scheduled_for']}]")
                print(f"To Chat Thread: {msg['conversation_id']}")
                print(f"Content: {msg['content']}\n")
                
                try:
                    # Append the message to the conversation history as 'agent'
                    db.add_message(
                        conversation_id=msg['conversation_id'],
                        sender_type="agent",
                        content=msg['content']
                    )
                    # Mark as sent
                    db.mark_buffered_message_sent(msg['id'])
                    db.add_system_log(logger_context, "INFO", f"Message ID {msg['id']} successfully dispatched and logged to chat history.")
                except Exception as e:
                    db.mark_buffered_message_failed(msg['id'], str(e))
                    db.add_system_log(logger_context, "ERROR", f"Failed dispatching message ID {msg['id']}: {str(e)}")
                    
        except Exception as err:
            db.add_system_log(logger_context, "ERROR", f"Error in worker loop: {str(err)}")
            
        time.sleep(2)

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    global is_worker_running, worker_thread
    is_worker_running = True
    worker_thread = threading.Thread(target=run_outbound_queue_worker, daemon=True)
    worker_thread.start()
    db.add_system_log("unified_server", "INFO", "Outbound queue worker thread started via lifespan.")
    yield
    is_worker_running = False
    if worker_thread:
        worker_thread.join(timeout=2.0)
    db.add_system_log("unified_server", "INFO", "Outbound queue worker thread stopped.")

app = FastAPI(
    title="Nuit Fragrances Unified Backend Server",
    description="Unified backend server combining agent, admin dashboard, human experts console, and background queue workers.",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize global agent runner
agent_runner = CustomerServiceAgent()

# --- Request/Response Models ---
class ChatRequest(BaseModel):
    message: str
    thread_id: Optional[str] = None
    customer_phone: Optional[str] = None
    platform: Optional[str] = "whatsapp"

class ChatResponse(BaseModel):
    status: str
    message: str
    is_handoff: bool
    handoff_summary: Optional[str] = ""

class SettingUpdateRequest(BaseModel):
    value: Dict[str, Any]

class ClaimRequest(BaseModel):
    expert_id: str

# --- 1. Customer Chat Ingress Endpoint ---
@app.post("/api/chat", response_model=ChatResponse)
async def execute_agent_loop(request: ChatRequest):
    """
    Ingress endpoint simulating customer social media channel webhook callback.
    """
    conversation_id = request.thread_id or str(uuid.uuid4())
    customer_phone = request.customer_phone or "+201000000000"
    platform = request.platform or "whatsapp"

    try:
        db.add_system_log("agent_server", "INFO", f"Ingress message received from {customer_phone} via {platform}")

        # 1. Load or register conversation in database
        conv = db.get_conversation(conversation_id)
        if not conv:
            conv = db.create_conversation(conversation_id, customer_phone, platform)

        # 2. Check if conversation is locked by active expert handoff
        if conv["status"] in ["handed_off"]:
            db.add_system_log("agent_server", "WARNING", f"Rejected message: Thread {conversation_id} is currently handed off to human expert.")
            return ChatResponse(
                status="ignored",
                message="Thread is currently handled by a human expert. Agent bypassed.",
                is_handoff=True,
                handoff_summary=conv.get("handoff_summary") or ""
            )

        # 3. Add customer message to historical messages table
        db.add_message(
            conversation_id=conversation_id,
            sender_type="customer",
            content=request.message
        )

        # 4. Invoke LangGraph customer service state machine
        response_text = agent_runner.send_message(request.message, thread_id=conversation_id)

        # 5. Check final thread state to see if handoff occurred
        final_state = agent_runner.get_thread_state(conversation_id)
        is_handoff = final_state.get("is_handoff", False)
        handoff_summary = final_state.get("handoff_summary", "")

        # 6. Queue outbound response message securely in message buffer
        if is_handoff:
            db.queue_outbound_message(conversation_id, "Connecting you to a support specialist right away. Please hold...")
            # Execute direct Python routing tool
            from core_agent.tools import request_human_handoff
            request_human_handoff.invoke({"conversation_id": conversation_id, "handoff_summary": handoff_summary})
        else:
            db.queue_outbound_message(conversation_id, response_text)

        return ChatResponse(
            status="processed",
            message="Agent process completed successfully. Output response buffered.",
            is_handoff=is_handoff,
            handoff_summary=handoff_summary
        )

    except Exception as e:
        db.add_system_log("agent_server", "ERROR", f"Failed executing agent loop for {conversation_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# --- 2. Admin Dashboard Endpoints ---
@app.get("/api/documents")
async def list_documents():
    """List both preloaded brand guides and user-uploaded custom docs from the database."""
    try:
        docs = db.get_documents()
        custom_docs = [doc["filename"] for doc in docs]
        static_docs = ["brand_identity.md", "customer_service_sop.md"]
        return {
            "static_permanent_context": static_docs,
            "dynamic_rag_documents": custom_docs
        }
    except Exception as e:
        db.add_system_log("dashboard_server", "ERROR", f"Failed to retrieve documents: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/upload")
async def upload_document(file: UploadFile = File(...)):
    """Ingest reference documents (.md / .txt) into Supabase / local SQLite registry."""
    filename = file.filename
    if not (filename.endswith(".md") or filename.endswith(".txt")):
        raise HTTPException(
            status_code=400,
            detail="Invalid file format. Only Markdown (.md) and text (.txt) files are supported."
        )

    try:
        content = await file.read()
        content_str = content.decode("utf-8")
        
        category = "faq"
        if "product" in filename.lower():
            category = "products"
        elif "policy" in filename.lower() or "sop" in filename.lower():
            category = "sop"

        db.add_document(filename, category, content_str)
        db.add_system_log("dashboard_server", "INFO", f"Ingested reference document: {filename}")

        all_docs = db.get_documents()
        custom_docs = [doc["filename"] for doc in all_docs]

        return {
            "status": "success",
            "message": f"Successfully ingested '{filename}'.",
            "available_documents": custom_docs
        }
    except Exception as e:
        db.add_system_log("dashboard_server", "ERROR", f"Failed to upload document {filename}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/documents/{filename}")
async def delete_document(filename: str):
    """Remove a reference document from the registry."""
    try:
        db.delete_document(filename)
        db.add_system_log("dashboard_server", "INFO", f"Deleted reference document: {filename}")
        return {"status": "success", "message": f"Document '{filename}' deleted successfully."}
    except Exception as e:
        db.add_system_log("dashboard_server", "ERROR", f"Failed to delete document {filename}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/settings/{key}")
async def get_setting(key: str):
    """Retrieve system configuration parameter."""
    try:
        val = db.get_setting(key)
        if val is None:
            raise HTTPException(status_code=404, detail=f"Setting with key '{key}' not found.")
        return {"key": key, "value": val}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/settings/{key}")
async def update_setting(key: str, request: SettingUpdateRequest):
    """Modify system configuration parameters (e.g. LLM models, prompts)."""
    try:
        db.update_setting(key, request.value)
        db.add_system_log("dashboard_server", "INFO", f"Updated setting: {key}")
        return {"status": "success", "message": f"Setting '{key}' updated successfully."}
    except Exception as e:
        db.add_system_log("dashboard_server", "ERROR", f"Failed to update setting {key}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/conversations")
async def get_conversations():
    """
    Fetch and format active conversation data from the database.
    Formats the rows to perfectly match the React client dashboard expectations.
    """
    try:
        convs = db.get_conversations()
        formatted_list = []

        for c in convs:
            messages = db.get_messages(c["id"])
            formatted_msgs = []
            for m in messages:
                # Map sender type
                sender = "bot" if m["sender_type"] in ["agent", "human"] else "user"
                # Map date to a string time
                try:
                    dt = datetime.datetime.fromisoformat(m["created_at"].replace("Z", "+00:00"))
                    time_str = dt.strftime("%I:%M:%S %p")
                except:
                    time_str = str(m["created_at"])
                
                formatted_msgs.append({
                    "sender": sender,
                    "text": m["content"],
                    "timestamp": time_str
                })

            intent = "general_faq"
            emotion = "neutral"
            failed_checks = []

            if messages:
                latest_msg = messages[-1]
                if latest_msg.get("sentiment_data"):
                    s_data = latest_msg["sentiment_data"]
                    if isinstance(s_data, str):
                        try:
                            s_data = json.loads(s_data)
                        except:
                            pass
                    if isinstance(s_data, dict):
                        emotion = s_data.get("vibe", "neutral")
                        intent = s_data.get("intent", "general_faq")

            audit_logs = [
                f"Sync: Conversation sync channel via {c['platform']}",
                f"Status: Current conversation status is {c['status']}"
            ]
            if c["assigned_expert_id"]:
                expert = db.get_expert(c["assigned_expert_id"])
                expert_name = expert["name"] if expert else "Unknown Expert"
                audit_logs.append(f"Assignment: Handed off to {expert_name}")

            status_map = {
                "active": "active",
                "pending_handoff": "escalated",
                "handed_off": "escalated",
                "resolved": "resolved"
            }
            fe_status = status_map.get(c["status"], c["status"])

            total_input = sum(m.get("tokens_used", 0) for m in messages if m["sender_type"] == "customer")
            total_output = sum(m.get("tokens_used", 0) for m in messages if m["sender_type"] in ["agent", "human"])
            
            if total_input == 0 and total_output == 0 and len(messages) > 0:
                total_input = 1200
                total_output = 400

            cost = (total_input * 0.00000015) + (total_output * 0.00000060)
            if c.get("cost_usd") and c["cost_usd"] > 0:
                cost = float(c["cost_usd"])

            formatted_list.append({
                "id": c["id"],
                "customerName": f"Customer {c['customer_phone'][-4:]}" if len(c['customer_phone']) >= 4 else "Client",
                "phoneNumber": c["customer_phone"],
                "status": fe_status,
                "emotion": emotion,
                "intent": intent,
                "channel": c["platform"],
                "timestamp": c["created_at"],
                "tokens": {"input": total_input, "output": total_output},
                "cost": cost,
                "messages": formatted_msgs,
                "auditLogs": audit_logs,
                "failedChecks": failed_checks,
                "handoffSummary": c.get("handoff_summary") or ""
            })

        return formatted_list
    except Exception as e:
        db.add_system_log("dashboard_server", "ERROR", f"Failed to retrieve conversations list: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# --- 3. Expert Console REST Endpoints ---
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
        db.add_system_log("expert_server", "ERROR", f"Failed to list expert conversations: {str(e)}")
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

        db.update_conversation(conversation_id, {
            "status": "handed_off",
            "assigned_expert_id": request.expert_id
        })

        db.add_system_log("expert_server", "INFO", f"Expert {expert['name']} manually claimed conversation {conversation_id}")
        return {
            "status": "success", 
            "message": "Successfully claimed conversation",
            "chat_redirect_url": expert["chat_redirect_url"]
        }
    except HTTPException:
        raise
    except Exception as e:
        db.add_system_log("expert_server", "ERROR", f"Failed to claim conversation {conversation_id}: {str(e)}")
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

        db.add_system_log("expert_server", "INFO", f"Conversation {conversation_id} resolved by expert.")
        return {"status": "success", "message": "Conversation resolved successfully."}
    except HTTPException:
        raise
    except Exception as e:
        db.add_system_log("expert_server", "ERROR", f"Failed to resolve conversation {conversation_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/expert/profiles")
async def list_experts():
    """Retrieve lists of experts and their current loads."""
    try:
        return db.get_experts()
    except Exception as e:
        db.add_system_log("expert_server", "ERROR", f"Failed to retrieve expert profiles: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
