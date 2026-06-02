import os
import shutil
from typing import Dict, Any, List
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Add parent dir to path to import database
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import db

app = FastAPI(
    title="Nuit Fragrances Dashboard API Server",
    description="Backend service managing settings, analytical aggregations, document uploads, and syncing for the admin panel.",
    version="1.0.0"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class SettingUpdateRequest(BaseModel):
    value: Dict[str, Any]

@app.get("/api/documents")
async def list_documents():
    """List both preloaded brand guides and user-uploaded custom docs from the database."""
    try:
        docs = db.get_documents()
        custom_docs = [doc["filename"] for doc in docs]
        
        # Hardcoded default brand specs
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
    """Ingest reference documents (.md / .txt) into Supabase / local registry."""
    filename = file.filename
    if not (filename.endswith(".md") or filename.endswith(".txt")):
        raise HTTPException(
            status_code=400,
            detail="Invalid file format. Only Markdown (.md) and text (.txt) files are supported."
        )

    try:
        # Read file content
        content = await file.read()
        content_str = content.decode("utf-8")
        
        # Save to database
        # Determine category based on filename or default to general
        category = "faq"
        if "product" in filename.lower():
            category = "products"
        elif "policy" in filename.lower() or "sop" in filename.lower():
            category = "sop"

        db.add_document(filename, category, content_str)
        db.add_system_log("dashboard_server", "INFO", f"Ingested reference document: {filename}")

        # Return updated list of custom documents
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
                from datetime import datetime
                try:
                    dt = datetime.fromisoformat(m["created_at"].replace("Z", "+00:00"))
                    time_str = dt.strftime("%I:%M:%S %p")
                except:
                    time_str = str(m["created_at"])
                
                formatted_msgs.append({
                    "sender": sender,
                    "text": m["content"],
                    "timestamp": time_str
                })

            # Retrieve intent, emotion, failed checks from latest message or logs if needed
            intent = "general_faq"
            emotion = "neutral"
            failed_checks = []
            audit_logs = []

            # If messages exist, inspect the latest metadata
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

            # Load logs if any (mock or real)
            # In a full trace, we can load LangSmith or system logs. For formatting:
            audit_logs = [
                f"Sync: Conversation sync channel via {c['platform']}",
                f"Status: Current conversation status is {c['status']}"
            ]
            if c["assigned_expert_id"]:
                expert = db.get_expert(c["assigned_expert_id"])
                expert_name = expert["name"] if expert else "Unknown Expert"
                audit_logs.append(f"Assignment: Handed off to {expert_name}")

            # Map DB status (active, pending_handoff, handed_off, resolved) to frontend status
            # React Frontend uses: 'purchased', 'escalated', 'resolved', 'active'
            status_map = {
                "active": "active",
                "pending_handoff": "escalated",
                "handed_off": "escalated",
                "resolved": "resolved"
            }
            fe_status = status_map.get(c["status"], c["status"])

            # Read token counts from database messages
            total_input = sum(m.get("tokens_used", 0) for m in messages if m["sender_type"] == "customer")
            total_output = sum(m.get("tokens_used", 0) for m in messages if m["sender_type"] in ["agent", "human"])
            
            # Fallback counts if zero
            if total_input == 0 and total_output == 0 and len(messages) > 0:
                total_input = 1200
                total_output = 400

            # Calculate cost (using DeepSeek-style rates)
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
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8001, reload=True)
