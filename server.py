import os
import shutil
from typing import Optional
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

# Load env variables before importing agent
load_dotenv()

from agent import CustomerServiceAgent

app = FastAPI(
    title="Nuit Fragrances Agentic Support Backend",
    description="V1 Agent Portfolio Backend with order tracking, strict guardrails, smart handoffs, and document ingestion.",
    version="1.0.0"
)

# Enable CORS for the frontend portfolio dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global agent instance
agent = CustomerServiceAgent()


class ChatRequest(BaseModel):
    message: str
    thread_id: Optional[str] = "default-thread"


class ChatResponse(BaseModel):
    response: str
    is_handoff: bool
    handoff_summary: Optional[str] = ""


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        # Run agent on message thread
        response_text = agent.send_message(request.message, thread_id=request.thread_id)

        # Query final thread state
        state = agent.get_thread_state(request.thread_id)
        is_handoff = state.get("is_handoff", False)
        handoff_summary = state.get("handoff_summary", "")

        return ChatResponse(
            response=response_text,
            is_handoff=is_handoff,
            handoff_summary=handoff_summary
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/upload")
async def upload_document(file: UploadFile = File(...)):
    # Validate extension
    filename = file.filename
    if not (filename.endswith(".md") or filename.endswith(".txt")):
        raise HTTPException(
            status_code=400,
            detail="Invalid file format. Only Markdown (.md) and text (.txt) files are supported."
        )

    try:
        # Ensure target folder exists
        os.makedirs(agent.docs_dir, exist_ok=True)
        save_path = os.path.join(agent.docs_dir, filename)

        with open(save_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Trigger reload of the document registry
        agent.loader.reload_documents()

        return {
            "status": "success",
            "message": f"Successfully ingested document '{filename}'. Knowledge base reloaded.",
            "available_documents": list(agent.loader.doc_registry.keys())
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/documents")
async def list_documents():
    """Returns lists of currently loaded knowledge documents."""
    return {
        "static_permanent_context": ["brand_identity.md", "customer_service_sop.md"],
        "dynamic_rag_documents": list(agent.loader.doc_registry.keys())
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
