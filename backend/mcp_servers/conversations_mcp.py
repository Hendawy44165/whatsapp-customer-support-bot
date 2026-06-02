import os
import sys
import time
import threading
import datetime
from typing import List, Dict, Any, Optional
from mcp.server.fastmcp import FastMCP

# Add parent directory to path to import database
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import db

# Create FastMCP server
mcp = FastMCP("Nuit Customer Conversations")

# Lock for queue worker
worker_lock = threading.Lock()
is_worker_running = True

def run_outbound_queue_worker():
    """
    Background worker thread polling the Supabase / SQLite message_buffer table.
    Dispatches pending messages when scheduled_for is reached.
    """
    global is_worker_running
    logger_context = "outbound_worker"
    db.add_system_log(logger_context, "INFO", "Outbound queue worker started.")
    
    while is_worker_running:
        try:
            # Query pending messages to send
            pending = db.get_pending_buffered_messages()
            for msg in pending:
                with worker_lock:
                    db.add_system_log(logger_context, "INFO", f"Processing buffered message ID {msg['id']} for conversation {msg['conversation_id']}")
                    
                    # Simulation: Print to console and insert as historical chat record
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
            # Prevent thread crash
            db.add_system_log(logger_context, "ERROR", f"Error in worker loop: {str(err)}")
            
        # Poll interval: 2 seconds
        time.sleep(2)

@mcp.tool()
def get_chat_history(conversation_id: str) -> str:
    """
    Retrieves the chronological text history of messages for context analysis.
    """
    try:
        messages = db.get_messages(conversation_id)
        if not messages:
            return "No previous message logs recorded for this conversation."

        history = []
        for m in messages:
            sender = "Customer" if m["sender_type"] == "customer" else "Nuit Concierge" if m["sender_type"] == "agent" else f"Human Expert"
            history.append(f"[{m['created_at']}] {sender}: {m['content']}")
        return "\n".join(history)
    except Exception as e:
        return f"Error retrieving history: {str(e)}"

@mcp.tool()
def queue_immediate_message(conversation_id: str, content: str) -> str:
    """
    Queues a message in the outbound buffer to be sent immediately.
    The agent must call this to respond to the customer.
    """
    try:
        msg_id = db.queue_outbound_message(conversation_id, content)
        db.add_system_log("conversations_mcp", "INFO", f"Queued immediate message ID: {msg_id}")
        return f"Message queued successfully (ID: {msg_id}). Worker will dispatch it shortly."
    except Exception as e:
        return f"Error queueing message: {str(e)}"

@mcp.tool()
def queue_scheduled_followup(conversation_id: str, content: str, delay_seconds: int) -> str:
    """
    Schedules an outbound follow-up message to the customer after a specific delay.
    Accepts 'delay_seconds' (e.g. 60 for 1 minute, 3600 for 1 hour).
    """
    try:
        # Calculate future timestamp
        import datetime
        future_time = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=delay_seconds)
        future_iso = future_time.isoformat()

        msg_id = db.queue_outbound_message(conversation_id, content, scheduled_for=future_iso)
        db.add_system_log("conversations_mcp", "INFO", f"Scheduled follow-up message ID {msg_id} in {delay_seconds}s")
        return f"Follow-up scheduled successfully (ID: {msg_id}, Dispatch at: {future_iso})."
    except Exception as e:
        return f"Error scheduling message: {str(e)}"

# Start the background polling worker
worker_thread = threading.Thread(target=run_outbound_queue_worker, daemon=True)
worker_thread.start()

if __name__ == "__main__":
    import uvicorn
    try:
        uvicorn.run(mcp.asgi_app, host="0.0.0.0", port=8013)
    finally:
        is_worker_running = False
        worker_thread.join(timeout=1.0)
