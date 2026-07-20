import asyncio
import os
import sys
import json
import datetime
import threading
import time
from typing import Dict, Any, List, Optional
import structlog
from fastapi import (
    FastAPI,
    UploadFile,
    File,
    HTTPException,
    Request,
    Response,
)
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

logger = structlog.get_logger("unified_server")

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

sys.modules["agent"] = core_agent

import core_agent.state as state
import core_agent.constants as constants
import core_agent.utils as utils
import core_agent.nodes as nodes

sys.modules["agent.state"] = state
sys.modules["agent.constants"] = constants
sys.modules["agent.utils"] = utils
sys.modules["agent.nodes"] = nodes

# Load our database helper client
from database import db

# Import NuitBot as CustomerServiceAgent for backward compatibility
from core_agent import NuitBot as CustomerServiceAgent

# Telegram Bot API client
from telegram_client import bot, send_telegram_message
from telebot import types

# HubSpot CRM integration (stubbed when HUBSPOT_ACCESS_TOKEN is absent)
from crm.hubspot_client import upsert_contact, log_note

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

                db.add_system_log(
                    logger_context,
                    "INFO",
                    f"Processing buffered message ID {msg['id']} for conversation {msg['conversation_id']}",
                )

                # Simulation output
                print(f"\n[OUTBOUND MESSAGE DISPATCHED - {msg['scheduled_for']}]")
                print(f"To Chat Thread: {msg['conversation_id']}")
                print(f"Content: {msg['content']}\n")

                try:
                    # If it's a Telegram conversation, send the message to Telegram
                    if msg["conversation_id"].startswith("tg_"):
                        chat_id = msg["conversation_id"].replace("tg_", "")
                        try:
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            res = loop.run_until_complete(send_telegram_message(chat_id, msg["content"]))
                            loop.close()
                            if res.get("status") == "error":
                                raise Exception(res.get("error"))
                        except Exception as e:
                            raise Exception(f"Telegram dispatch failed: {str(e)}")

                    # Append the message to the conversation history as 'agent'
                    db.add_message(
                        conversation_id=msg["conversation_id"],
                        sender_type="agent",
                        content=msg["content"],
                    )
                    # Mark as sent
                    db.mark_buffered_message_sent(msg["id"])
                    db.add_system_log(
                        logger_context,
                        "INFO",
                        f"Message ID {msg['id']} successfully dispatched and logged to chat history.",
                    )
                except Exception as e:
                    db.mark_buffered_message_failed(msg["id"], str(e))
                    db.add_system_log(
                        logger_context,
                        "ERROR",
                        f"Failed dispatching message ID {msg['id']}: {str(e)}",
                    )

        except Exception as err:
            db.add_system_log(
                logger_context, "ERROR", f"Error in worker loop: {str(err)}"
            )

        time.sleep(2)


from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    global is_worker_running, worker_thread
    logger.info("Initializing unified backend server lifespan resources")
    is_worker_running = True
    worker_thread = threading.Thread(target=run_outbound_queue_worker, daemon=True)
    worker_thread.start()
    db.add_system_log(
        "unified_server", "INFO", "Outbound queue worker thread started via lifespan."
    )
    yield
    logger.info("Shutting down unified backend server lifespan resources")
    is_worker_running = False
    if worker_thread:
        worker_thread.join(timeout=2.0)
    db.add_system_log("unified_server", "INFO", "Outbound queue worker thread stopped.")


app = FastAPI(
    title="Nuit Fragrances Unified Backend Server",
    description="Unified backend server combining agent, admin dashboard, human experts console, and background queue workers.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

agent_runner = CustomerServiceAgent()


async def handle_telegram_message(message: types.Message):
    """Process a Telegram message update through the existing customer support agent."""
    message_id = getattr(message, "message_id", None)
    if message_id is not None:
        message_id = str(message_id)

    chat_id = str(message.chat.id)
    message_body = message.text or ""
    conversation_id = f"tg_{chat_id}"
    customer_phone = f"tg_{chat_id}"
    first_name = getattr(message.from_user, "first_name", "") or ""
    last_name = getattr(message.from_user, "last_name", "") or ""
    contact_name = f"{first_name} {last_name}".strip() or ""

    if message_id and is_duplicate_telegram_message(message_id):
        db.add_system_log(
            "telegram_webhook",
            "INFO",
            f"Ignored duplicate Telegram webhook retry for message_id {message_id}",
        )
        return

    db.add_system_log(
        "telegram_webhook", "INFO", f"Received message from chat {chat_id}"
    )

    # Check for /clear command
    if message_body.strip().lower() in ["/clear", "/clear_all", "/reset"]:
        asyncio.create_task(
            handle_telegram_clear_command(
                chat_id=chat_id,
                conversation_id=conversation_id,
                cmd_message_id=message_id,
            )
        )
        return

    try:
        conv = db.get_conversation(conversation_id)
        if not conv:
            conv = db.create_conversation(conversation_id, customer_phone, "telegram")

        # Save customer message to DB so human agents can view it in dashboard/console
        db.add_message(
            conversation_id=conversation_id,
            sender_type="customer",
            content=message_body,
        )

        # Reopen resolved conversations as active AI sessions if customer writes again
        if conv and conv.get("status") == "resolved":
            db.update_conversation(conversation_id, {"status": "active", "assigned_expert_id": None})
            conv["status"] = "active"

        # If conversation is under human review, skip AI agent and redirect to human dashboard
        if conv and conv.get("status") in ["escalated", "pending_handoff", "handed_off"]:
            db.add_system_log(
                "telegram_webhook",
                "INFO",
                f"Customer message from chat {chat_id} saved to DB and redirected to human review (status={conv.get('status')}).",
            )
            return

        asyncio.create_task(
            process_telegram_message_async(
                chat_id=chat_id,
                message_body=message_body,
                conversation_id=conversation_id,
                customer_phone=customer_phone,
                contact_name=contact_name,
            )
        )

    except Exception as e:
        db.add_system_log(
            "telegram_webhook",
            "ERROR",
            f"Failed queueing message from chat {chat_id}: {str(e)}",
        )


async def handle_telegram_clear_command(
    chat_id: str, conversation_id: str, cmd_message_id: Optional[str] = None
):
    """Handle /clear command: delete database conversation history, reset agent state, and delete Telegram UI messages."""
    try:
        from telegram_client import clear_telegram_chat_messages

        db.add_system_log(
            "telegram_webhook", "INFO", f"Executing /clear command for chat {chat_id}"
        )

        # 1. Reset AI agent memory saver checkpoint
        agent_runner.reset_thread(conversation_id)

        # 2. Delete database records (conversations, messages, tickets, message_buffer)
        db.delete_conversation(conversation_id)

        # 3. Delete messages from Telegram UI
        numeric_msg_id = int(cmd_message_id) if cmd_message_id and cmd_message_id.isdigit() else None
        await clear_telegram_chat_messages(
            chat_id=chat_id,
            last_message_id=numeric_msg_id,
            depth=150,
        )

        # 4. Send clean confirmation message
        await send_telegram_message(
            chat_id,
            "🧹 Conversation history and memory have been completely cleared!",
        )

        db.add_system_log(
            "telegram_webhook",
            "INFO",
            f"Completed /clear command for chat {chat_id}",
        )
    except Exception as e:
        db.add_system_log(
            "telegram_webhook",
            "ERROR",
            f"Failed executing /clear command for chat {chat_id}: {str(e)}",
        )


if bot is not None:
    bot.register_message_handler(
        handle_telegram_message,
        func=lambda message: getattr(message, "text", None) is not None,
    )


class SettingUpdateRequest(BaseModel):
    value: Dict[str, Any]


class ClaimRequest(BaseModel):
    expert_id: str


# --- 2. Admin Dashboard Endpoints ---


# --- Telegram Bot Webhook ---

# In-memory sliding window cache for Telegram message IDs to prevent duplicates
processed_telegram_messages = {}
processed_telegram_messages_lock = threading.Lock()


def is_duplicate_telegram_message(message_id: str) -> bool:
    """Check if message_id has already been processed within the last 10 minutes."""
    if not message_id:
        return False

    now = time.time()
    with processed_telegram_messages_lock:
        expired = [
            msg_id
            for msg_id, ts in processed_telegram_messages.items()
            if now - ts > 600
        ]
        for msg_id in expired:
            del processed_telegram_messages[msg_id]

        if message_id in processed_telegram_messages:
            return True
        processed_telegram_messages[message_id] = now
        return False


async def process_telegram_message_async(
    chat_id: str,
    message_body: str,
    conversation_id: str,
    customer_phone: str,
    contact_name: str,
):
    """Asynchronously runs the agent loop and sends the reply to Telegram."""
    try:
        # Call AI agent — returns a structured JSON dict
        agent_output = agent_runner.send_message(
            message_body, thread_id=conversation_id
        )

        # Route based on the agent output type
        output_type = agent_output.get("type", "error")
        reply_message = agent_output.get("message", "")

        if output_type == "ai_reply":
            db.add_message(
                conversation_id=conversation_id,
                sender_type="agent",
                content=reply_message,
            )
            await send_telegram_message(chat_id, reply_message)
            db.add_system_log(
                "telegram_webhook", "INFO", f"ai_reply sent to chat {chat_id}"
            )

        elif output_type == "escalation_ticket":
            db.add_message(
                conversation_id=conversation_id,
                sender_type="agent",
                content=reply_message,
            )
            await send_telegram_message(chat_id, reply_message)
            # Sync escalation note to HubSpot using Telegram username/identifier
            try:
                contact_id = upsert_contact(customer_phone, name=contact_name)
                if contact_id:
                    log_note(
                        contact_id, f'Escalation: {agent_output.get("summary", "")}'
                    )
            except Exception as crm_e:
                db.add_system_log(
                    "telegram_webhook", "WARNING", f"HubSpot sync failed: {crm_e}"
                )
            db.add_system_log(
                "telegram_webhook",
                "INFO",
                f"Escalation ticket created for chat {chat_id}",
            )

        elif output_type == "blocked":
            db.add_message(
                conversation_id=conversation_id,
                sender_type="agent",
                content=reply_message,
            )
            await send_telegram_message(chat_id, reply_message)
            db.add_system_log(
                "telegram_webhook", "INFO", f"Blocked message from chat {chat_id}"
            )

        else:  # error or unknown type
            fallback = agent_output.get(
                "message", "Sorry, something went wrong. A team member will follow up."
            )
            db.add_message(
                conversation_id=conversation_id, sender_type="agent", content=fallback
            )
            await send_telegram_message(chat_id, fallback)
            db.add_system_log(
                "telegram_webhook",
                "ERROR",
                f'Agent error for chat {chat_id}: {agent_output.get("error", "unknown")}',
            )

        # Always upsert HubSpot contact (fire-and-forget; failures are non-fatal)
        try:
            upsert_contact(customer_phone, name=contact_name)
        except Exception:
            pass

    except Exception as e:
        db.add_system_log(
            "telegram_webhook",
            "ERROR",
            f"Failed processing message from chat {chat_id}: {str(e)}",
        )


@app.post("/webhook/telegram")
async def telegram_webhook(request: Request):
    """
    Telegram Bot API update webhook.
    Receives incoming updates and forwards them into AsyncTeleBot's update processor.
    Always returns HTTP 200 so Telegram knows the webhook was received.
    """
    try:
        payload = await request.json()
    except Exception:
        return {"status": "ok"}

    if bot is None:
        db.add_system_log(
            "telegram_webhook",
            "WARNING",
            "Telegram bot not configured; webhook received but cannot process updates.",
        )
        return {"status": "ok"}

    try:
        update = types.Update.de_json(payload)
        await bot.process_new_updates([update])
    except Exception as e:
        db.add_system_log(
            "telegram_webhook",
            "ERROR",
            f"Failed processing Telegram webhook update: {str(e)}",
        )

    return {"status": "ok"}


# --- Admin Dashboard Endpoints ---
@app.get("/api/documents")
async def list_documents():
    """List both preloaded brand guides and user-uploaded custom docs from the database."""
    try:
        docs = db.get_documents()
        custom_docs = [doc["filename"] for doc in docs]
        static_docs = ["brand_identity.md", "customer_service_sop.md"]
        return {
            "static_permanent_context": static_docs,
            "dynamic_rag_documents": custom_docs,
        }
    except Exception as e:
        db.add_system_log(
            "dashboard_server", "ERROR", f"Failed to retrieve documents: {str(e)}"
        )
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/upload")
async def upload_document(file: UploadFile = File(...)):
    """Ingest reference documents (.md / .txt) into Supabase / local SQLite registry."""
    filename = file.filename
    if not (filename.endswith(".md") or filename.endswith(".txt")):
        raise HTTPException(
            status_code=400,
            detail="Invalid file format. Only Markdown (.md) and text (.txt) files are supported.",
        )

    try:
        logger.info("Uploading reference document", filename=filename)
        content = await file.read()
        content_str = content.decode("utf-8")

        category = "faq"
        if "product" in filename.lower():
            category = "products"
        elif "policy" in filename.lower() or "sop" in filename.lower():
            category = "sop"

        db.add_document(filename, category, content_str)
        db.add_system_log(
            "dashboard_server", "INFO", f"Ingested reference document: {filename}"
        )

        all_docs = db.get_documents()
        custom_docs = [doc["filename"] for doc in all_docs]

        return {
            "status": "success",
            "message": f"Successfully ingested '{filename}'.",
            "available_documents": custom_docs,
        }
    except Exception as e:
        db.add_system_log(
            "dashboard_server",
            "ERROR",
            f"Failed to upload document {filename}: {str(e)}",
        )
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/documents/{filename}")
async def delete_document(filename: str):
    """Remove a reference document from the registry."""
    try:
        logger.info("Deleting reference document", filename=filename)
        db.delete_document(filename)
        db.add_system_log(
            "dashboard_server", "INFO", f"Deleted reference document: {filename}"
        )
        return {
            "status": "success",
            "message": f"Document '{filename}' deleted successfully.",
        }
    except Exception as e:
        db.add_system_log(
            "dashboard_server",
            "ERROR",
            f"Failed to delete document {filename}: {str(e)}",
        )
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/settings/{key}")
async def get_setting(key: str):
    """Retrieve system configuration parameter."""
    try:
        val = db.get_setting(key)
        if val is None:
            raise HTTPException(
                status_code=404, detail=f"Setting with key '{key}' not found."
            )
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
        return {
            "status": "success",
            "message": f"Setting '{key}' updated successfully.",
        }
    except Exception as e:
        db.add_system_log(
            "dashboard_server", "ERROR", f"Failed to update setting {key}: {str(e)}"
        )
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/conversations")
async def get_conversations(search: Optional[str] = None):
    """
    Fetch and format active conversation data from the database.
    Formats the rows to perfectly match the React client dashboard expectations.
    """
    try:
        convs = db.get_conversations(search_query=search)
        formatted_list = []


        for c in convs:
            messages = db.get_messages(c["id"])
            formatted_msgs = []
            for m in messages:
                # Map sender type
                sender = "bot" if m["sender_type"] in ["agent", "human"] else "user"
                # Map date to a string time
                try:
                    dt = datetime.datetime.fromisoformat(
                        m["created_at"].replace("Z", "+00:00")
                    )
                    time_str = dt.strftime("%I:%M:%S %p")
                except:
                    time_str = str(m["created_at"])

                formatted_msgs.append(
                    {"sender": sender, "text": m["content"], "timestamp": time_str}
                )

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
                f"Status: Current conversation status is {c['status']}",
            ]
            if c["assigned_expert_id"]:
                expert = db.get_expert(c["assigned_expert_id"])
                expert_name = expert["name"] if expert else "Unknown Expert"
                audit_logs.append(f"Assignment: Handed off to {expert_name}")

            status_map = {
                "active": "active",
                "pending_handoff": "escalated",
                "handed_off": "escalated",
                "resolved": "resolved",
            }
            fe_status = status_map.get(c["status"], c["status"])

            total_input = sum(
                m.get("tokens_used", 0)
                for m in messages
                if m["sender_type"] == "customer"
            )
            total_output = sum(
                m.get("tokens_used", 0)
                for m in messages
                if m["sender_type"] in ["agent", "human"]
            )

            if total_input == 0 and total_output == 0 and len(messages) > 0:
                total_input = 1200
                total_output = 400

            cost = (total_input * 0.00000015) + (total_output * 0.00000060)
            if c.get("cost_usd") and c["cost_usd"] > 0:
                cost = float(c["cost_usd"])

            formatted_list.append(
                {
                    "id": c["id"],
                    "customerName": (
                        f"Customer {c['customer_phone'][-4:]}"
                        if len(c["customer_phone"]) >= 4
                        else "Client"
                    ),
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
                    "handoffSummary": c.get("handoff_summary") or "",
                }
            )

        return formatted_list
    except Exception as e:
        db.add_system_log(
            "dashboard_server",
            "ERROR",
            f"Failed to retrieve conversations list: {str(e)}",
        )
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
            "shared_pending_queue": pending_queue,
        }
    except Exception as e:
        db.add_system_log(
            "expert_server", "ERROR", f"Failed to list expert conversations: {str(e)}"
        )
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/expert/claim/{conversation_id}")
async def claim_conversation(conversation_id: str, request: ClaimRequest):
    """
    Manually claim a conversation from the pending queue.
    """
    try:
        logger.info(
            "Expert claiming conversation",
            conversation_id=conversation_id,
            expert_id=request.expert_id,
        )
        conv = db.get_conversation(conversation_id)
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")

        if conv["status"] != "pending_handoff":
            return {
                "status": "error",
                "message": f"Conversation is already {conv['status']}",
            }

        expert = db.get_expert(request.expert_id)
        if not expert:
            raise HTTPException(status_code=404, detail="Expert profile not found")

        db.update_conversation(
            conversation_id,
            {"status": "handed_off", "assigned_expert_id": request.expert_id},
        )

        db.add_system_log(
            "expert_server",
            "INFO",
            f"Expert {expert['name']} manually claimed conversation {conversation_id}",
        )
        return {
            "status": "success",
            "message": "Successfully claimed conversation",
            "chat_redirect_url": expert["chat_redirect_url"],
        }
    except HTTPException:
        raise
    except Exception as e:
        db.add_system_log(
            "expert_server",
            "ERROR",
            f"Failed to claim conversation {conversation_id}: {str(e)}",
        )
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/expert/resolve/{conversation_id}")
async def resolve_conversation(conversation_id: str):
    """
    Mark conversation as resolved, freeing up expert capacity.
    """
    try:
        logger.info("Expert resolving conversation", conversation_id=conversation_id)
        conv = db.get_conversation(conversation_id)
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")

        db.update_conversation(conversation_id, {"status": "resolved"})

        db.add_system_log(
            "expert_server",
            "INFO",
            f"Conversation {conversation_id} resolved by expert.",
        )
        return {"status": "success", "message": "Conversation resolved successfully."}
    except HTTPException:
        raise
    except Exception as e:
        db.add_system_log(
            "expert_server",
            "ERROR",
            f"Failed to resolve conversation {conversation_id}: {str(e)}",
        )
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/expert/profiles")
async def list_experts():
    """Retrieve lists of experts and their current loads."""
    try:
        return db.get_experts()
    except Exception as e:
        db.add_system_log(
            "expert_server", "ERROR", f"Failed to retrieve expert profiles: {str(e)}"
        )
        raise HTTPException(status_code=500, detail=str(e))


# --- 4. Tickets Endpoints ---
@app.get("/api/tickets")
async def get_tickets():
    """Retrieve all escalation tickets for the dashboard."""
    try:
        return db.get_tickets()
    except Exception as e:
        db.add_system_log(
            "dashboard_server", "ERROR", f"Failed to retrieve tickets: {str(e)}"
        )
        raise HTTPException(status_code=500, detail=str(e))


@app.patch("/api/tickets/{ticket_id}/resolve")
async def resolve_ticket(ticket_id: int):
    """Mark an escalation ticket as resolved and sync status to conversation."""
    try:
        logger.info("Resolving escalation ticket", ticket_id=ticket_id)
        updated_ticket = db.update_ticket(
            ticket_id,
            {
                "status": "resolved",
                "resolved_at": datetime.datetime.utcnow().isoformat(),
            },
        )
        if updated_ticket and updated_ticket.get("conversation_id"):
            db.update_conversation(
                updated_ticket["conversation_id"], {"status": "resolved"}
            )
        db.add_system_log("dashboard_server", "INFO", f"Ticket {ticket_id} resolved.")
        return {"status": "success", "message": f"Ticket {ticket_id} resolved."}
    except Exception as e:
        db.add_system_log(
            "dashboard_server",
            "ERROR",
            f"Failed to resolve ticket {ticket_id}: {str(e)}",
        )
        raise HTTPException(status_code=500, detail=str(e))


class ReplyRequest(BaseModel):
    message: str


@app.post("/api/conversations/{conversation_id}/reply")
async def reply_to_conversation(conversation_id: str, request: ReplyRequest):
    """
    Send a manual response to a customer conversation from the admin dashboard.
    """
    try:
        logger.info("Human replying to conversation", conversation_id=conversation_id, message=request.message)
        conv = db.get_conversation(conversation_id)
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")

        # Save manual reply to database as "human"
        db.add_message(
            conversation_id=conversation_id,
            sender_type="human",
            content=request.message,
        )

        # Mark conversation as under active human handoff
        if conv.get("status") != "resolved":
            db.update_conversation(conversation_id, {"status": "handed_off"})

        # Dispatch via Telegram if conversation channel is Telegram
        if conversation_id.startswith("tg_"):
            chat_id = conversation_id.replace("tg_", "")
            res = await send_telegram_message(chat_id, request.message)
            if res.get("status") == "error":
                db.add_system_log(
                    "dashboard_server", "ERROR", f"Failed to send Telegram message: {res.get('error')}"
                )
                raise HTTPException(status_code=500, detail=f"Telegram send failed: {res.get('error')}")

        db.add_system_log(
            "dashboard_server",
            "INFO",
            f"Manual reply sent to conversation {conversation_id}"
        )
        return {"status": "success", "message": "Reply sent successfully."}
    except HTTPException:
        raise
    except Exception as e:
        db.add_system_log(
            "dashboard_server",
            "ERROR",
            f"Failed to reply to conversation {conversation_id}: {str(e)}",
        )
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
