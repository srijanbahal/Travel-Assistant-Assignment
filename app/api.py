"""
FastAPI Backend Routes for InviGrid Travel Assistant

This file provides REST and WebSocket endpoints for the frontend without modifying
the existing Streamlit main.py or any backend logic. It reuses the existing:
- graph/workflow.py (app_graph)
- data/chat_repo.py (chat history)
- data/init_db.py (database initialization)

Run with: uvicorn app.api:app --host 0.0.0.0 --port 8000 --reload
"""

import os
import sys
import uuid
import json
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime

# Add root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from graph.workflow import app_graph
from langchain_core.messages import HumanMessage, AIMessage
from data.init_db import init_db
from data.chat_repo import save_chat_message, get_chat_history
from agents.logger import log_error

# Initialize database
try:
    init_db()
except Exception as e:
    print(f"DB Init Error: {e}")

# FastAPI App
app = FastAPI(
    title="InviGrid Travel Assistant API",
    description="REST and WebSocket API for the multi-lingual travel assistant",
    version="1.0.0"
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============== Pydantic Models ===============

class ChatMessage(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000)
    

class ChatContext(BaseModel):
    session_id: str
    user_language: str = "English"
    booking_context: Dict[str, Any] = Field(default_factory=dict)
    booking_stage: Optional[str] = None
    search_results: List[Dict[str, Any]] = Field(default_factory=list)
    search_context: str = "unknown"


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    context: ChatContext


class ChatResponse(BaseModel):
    message: str
    english_message: Optional[str] = None
    search_results: List[Dict[str, Any]] = Field(default_factory=list)
    search_context: str = "unknown"
    booking_stage: Optional[str] = None
    booking_context: Dict[str, Any] = Field(default_factory=dict)
    user_language: str = "English"


class SessionResponse(BaseModel):
    session_id: str
    created_at: str


class HistoryMessage(BaseModel):
    role: str
    content: str
    timestamp: Optional[str] = None


class HistoryResponse(BaseModel):
    session_id: str
    messages: List[HistoryMessage]


# =============== Session Management ===============

# In-memory session storage (for demo; use Redis in production)
sessions: Dict[str, Dict[str, Any]] = {}


def get_or_create_session(session_id: str) -> Dict[str, Any]:
    """Get existing session or create a new one."""
    if session_id not in sessions:
        sessions[session_id] = {
            "messages": [],
            "user_language": "English",
            "booking_context": {"session_id": session_id},
            "booking_stage": None,
            "last_search_results": [],
            "search_context": "unknown",
            "created_at": datetime.now().isoformat()
        }
    return sessions[session_id]


# =============== REST Endpoints ===============

@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "service": "InviGrid Travel Assistant API"}


@app.post("/api/session", response_model=SessionResponse)
async def create_session():
    """Create a new chat session."""
    session_id = str(uuid.uuid4())
    get_or_create_session(session_id)
    return SessionResponse(
        session_id=session_id,
        created_at=datetime.now().isoformat()
    )


@app.get("/api/session/{session_id}/history", response_model=HistoryResponse)
async def get_session_history(session_id: str):
    """Get chat history for a session."""
    try:
        db_history = get_chat_history(session_id)
        messages = [
            HistoryMessage(
                role="user" if msg.sender == "user" else "assistant",
                content=msg.message,
                timestamp=msg.timestamp
            )
            for msg in db_history
        ]
        return HistoryResponse(session_id=session_id, messages=messages)
    except Exception as e:
        log_error("API", f"Failed to get history: {e}")
        return HistoryResponse(session_id=session_id, messages=[])


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Send a message and get a response.
    
    This is the main REST endpoint for chat. For real-time updates,
    use the WebSocket endpoint instead.
    """
    session = get_or_create_session(request.context.session_id)
    
    try:
        # Build LangChain message history (last 10 messages)
        history = []
        for m in session["messages"][-10:]:
            if m["role"] == "user":
                history.append(HumanMessage(content=m["content"]))
            else:
                history.append(AIMessage(content=m["content"]))
        
        # Add current message
        history.append(HumanMessage(content=request.message))
        
        # Prepare graph inputs
        inputs = {
            "messages": history,
            "user_language": request.context.user_language or session["user_language"],
            "booking_context": request.context.booking_context or session["booking_context"],
            "last_search_results": request.context.search_results or session["last_search_results"],
            "search_context": request.context.search_context or session["search_context"],
            "booking_stage": request.context.booking_stage or session["booking_stage"],
            "a2a_log": [],
            "next_agent": "travel_agent",
        }
        
        # Invoke the graph
        result = app_graph.invoke(inputs)
        
        # Update session state
        new_results = result.get("last_search_results", [])
        if new_results:
            session["last_search_results"] = new_results
        
        session["search_context"] = result.get("search_context", session["search_context"])
        session["booking_context"] = result.get("booking_context", session["booking_context"]) 
        session["booking_stage"] = result.get("booking_stage")
        session["user_language"] = result.get("user_language", session["user_language"])
        
        # Get the response
        last_msg = result["messages"][-1]
        response_text = last_msg.content
        
        # Extract English original if available
        english_text = None
        if hasattr(last_msg, 'additional_kwargs') and "original_english" in last_msg.additional_kwargs:
            english_text = last_msg.additional_kwargs["original_english"]
        
        # Store message in session
        session["messages"].append({"role": "user", "content": request.message})
        session["messages"].append({"role": "assistant", "content": response_text})
        
        return ChatResponse(
            message=response_text,
            english_message=english_text,
            search_results=session["last_search_results"],
            search_context=session["search_context"],
            booking_stage=session["booking_stage"],
            booking_context=session["booking_context"],
            user_language=session["user_language"]
        )
        
    except Exception as e:
        log_error("API", f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/session/{session_id}")
async def clear_session(session_id: str):
    """Clear a session's state."""
    if session_id in sessions:
        sessions[session_id] = {
            "messages": [],
            "user_language": "English",
            "booking_context": {"session_id": session_id},
            "booking_stage": None,
            "last_search_results": [],
            "search_context": "unknown",
            "created_at": datetime.now().isoformat()
        }
    return {"status": "cleared", "session_id": session_id}


# =============== WebSocket Endpoint ===============

class ConnectionManager:
    """Manage WebSocket connections."""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        self.active_connections[session_id] = websocket
        
    def disconnect(self, session_id: str):
        if session_id in self.active_connections:
            del self.active_connections[session_id]
    
    async def send_message(self, session_id: str, message: dict):
        if session_id in self.active_connections:
            await self.active_connections[session_id].send_json(message)


manager = ConnectionManager()


@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint for real-time chat.
    
    Message format (client -> server):
    {
        "type": "message",
        "content": "user message text"
    }
    
    Response format (server -> client):
    {
        "type": "thinking" | "response" | "error",
        "message": "...",
        "english_message": "...",
        "search_results": [...],
        "booking_stage": "...",
        "booking_context": {...}
    }
    """
    await manager.connect(websocket, session_id)
    session = get_or_create_session(session_id)
    
    try:
        while True:
            # Receive message
            data = await websocket.receive_json()
            
            if data.get("type") == "message":
                user_content = data.get("content", "").strip()
                
                if not user_content:
                    continue
                
                # Send "thinking" status
                await manager.send_message(session_id, {
                    "type": "thinking",
                    "message": "Processing your request..."
                })
                
                try:
                    # Build history
                    history = []
                    for m in session["messages"][-10:]:
                        if m["role"] == "user":
                            history.append(HumanMessage(content=m["content"]))
                        else:
                            history.append(AIMessage(content=m["content"]))
                    
                    history.append(HumanMessage(content=user_content))
                    
                    # Prepare inputs
                    inputs = {
                        "messages": history,
                        "user_language": session["user_language"],
                        "booking_context": session["booking_context"],
                        "last_search_results": session["last_search_results"],
                        "search_context": session["search_context"],
                        "booking_stage": session["booking_stage"],
                        "a2a_log": [],
                        "next_agent": "travel_agent",
                    }
                    
                    # Run in thread pool to not block
                    loop = asyncio.get_event_loop()
                    result = await loop.run_in_executor(None, app_graph.invoke, inputs)
                    
                    # Update session
                    new_results = result.get("last_search_results", [])
                    if new_results:
                        session["last_search_results"] = new_results
                    
                    session["search_context"] = result.get("search_context", session["search_context"])
                    session["booking_context"] = result.get("booking_context", session["booking_context"])
                    session["booking_stage"] = result.get("booking_stage")
                    session["user_language"] = result.get("user_language", session["user_language"])
                    
                    # Get response
                    last_msg = result["messages"][-1]
                    response_text = last_msg.content
                    
                    english_text = None
                    if hasattr(last_msg, 'additional_kwargs') and "original_english" in last_msg.additional_kwargs:
                        english_text = last_msg.additional_kwargs["original_english"]
                    
                    # Store messages
                    session["messages"].append({"role": "user", "content": user_content})
                    session["messages"].append({"role": "assistant", "content": response_text})
                    
                    # Send response
                    await manager.send_message(session_id, {
                        "type": "response",
                        "message": response_text,
                        "english_message": english_text,
                        "search_results": session["last_search_results"],
                        "search_context": session["search_context"],
                        "booking_stage": session["booking_stage"],
                        "booking_context": session["booking_context"],
                        "user_language": session["user_language"]
                    })
                    
                except Exception as e:
                    log_error("WebSocket", f"Processing error: {e}")
                    await manager.send_message(session_id, {
                        "type": "error",
                        "message": f"An error occurred: {str(e)}"
                    })
            
            elif data.get("type") == "ping":
                await manager.send_message(session_id, {"type": "pong"})
                
    except WebSocketDisconnect:
        manager.disconnect(session_id)
    except Exception as e:
        log_error("WebSocket", f"Connection error: {e}")
        manager.disconnect(session_id)


# =============== Main ===============

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
