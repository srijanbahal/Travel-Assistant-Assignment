"""
FastAPI Backend for InviGrid Travel Assistant

Orchestrates the agent flow with central memory management:
1. Translation (input) - detect language, translate to English
2. Router - classify intent (travel/booking)
3. Travel/Booking Agent - process with full memory context
4. Translation (output) - translate response back

Run with: uvicorn app.api:app --host 0.0.0.0 --port 8000 --reload
"""

import os
import sys
import uuid
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime

# Add root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Import our agents and memory
from agents.memory import get_memory, clear_memory, ConversationMemory
from agents.translation_agent import translate_input, translate_output
from agents.router import classify_intent
from agents.travel_agent import run_travel_agent
from agents.booking_agent import run_booking_agent
from agents.logger import log_error, log_agent_handoff

# Initialize database
from data.init_db import init_db
from data.chat_repo import save_chat_message, get_chat_history

try:
    init_db()
except Exception as e:
    print(f"DB Init Error: {e}")

# FastAPI App
app = FastAPI(
    title="InviGrid Travel Assistant API",
    description="Multi-lingual travel assistant with central memory management",
    version="2.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "*"],
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

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    session_id: str

class ChatResponse(BaseModel):
    message: str
    english_message: Optional[str] = None
    search_results: List[Dict[str, Any]] = Field(default_factory=list)
    search_type: str = "unknown"
    booking_stage: Optional[str] = None
    booking_context: Dict[str, Any] = Field(default_factory=dict)
    user_language: str = "English"

class SessionResponse(BaseModel):
    session_id: str
    created_at: str


# =============== Core Chat Handler ===============

def handle_chat_sync(session_id: str, user_message: str) -> Dict[str, Any]:
    """
    Synchronous chat handler that orchestrates all agents.
    
    Flow:
    1. Get/create memory for session
    2. Translate input to English
    3. Route to appropriate agent
    4. Execute agent with full memory context
    5. Update memory with results
    6. Translate output to user's language
    7. Return response with context
    """
    # 1. Get memory
    memory = get_memory(session_id)
    
    print(f"[DEBUG] Session: {session_id}")
    print(f"[DEBUG] Memory has {len(memory.search_results)} search results")
    print(f"[DEBUG] Booking stage: {memory.booking_state.get('stage')}")
    
    # 2. Translate input
    english_text, is_valid = translate_input(user_message, memory)
    
    if not is_valid:
        # Validation failed, return error message
        return {
            "message": english_text,  # Error message
            "english_message": english_text,
            "search_results": memory.search_results,
            "search_type": memory.search_type,
            "booking_stage": memory.booking_state.get("stage"),
            "booking_context": memory.booking_state,
            "user_language": memory.user_language
        }
    
    print(f"[DEBUG] Translated to English: {english_text[:50]}...")
    print(f"[DEBUG] Detected language: {memory.user_language}")
    
    # 3. Route to appropriate agent
    intent = classify_intent(english_text, memory)
    print(f"[DEBUG] Routed to: {intent}")
    
    # 4. Execute agent
    if intent == "booking":
        log_agent_handoff("Router", "BookingAgent", english_text, {})
        result = run_booking_agent(english_text, memory)
        
        # Update memory with booking state
        memory.update_booking_state(result.booking_state)
        response_text = result.response
        
    else:  # travel
        log_agent_handoff("Router", "TravelAgent", english_text, {})
        result = run_travel_agent(english_text, memory)
        
        # Update memory with search results
        if result.search_results:
            memory.update_search_results(result.search_results, result.search_type)
            print(f"[DEBUG] Updated memory with {len(result.search_results)} results")
        
        response_text = result.response
    
    # 5. Translate output
    translated_response = translate_output(response_text, memory)
    
    # 6. Update message history
    memory.add_message("user", user_message)
    memory.add_message("assistant", translated_response)
    
    # Save to database
    try:
        save_chat_message(session_id, "user", user_message)
        save_chat_message(session_id, "assistant", translated_response)
    except Exception as e:
        log_error("API", f"Failed to save messages: {e}")
    
    # 7. Return response
    return {
        "message": translated_response,
        "english_message": response_text if memory.user_language != "English" else None,
        "search_results": memory.search_results,
        "search_type": memory.search_type,
        "booking_stage": memory.booking_state.get("stage"),
        "booking_context": memory.booking_state,
        "user_language": memory.user_language
    }


# =============== REST Endpoints ===============

@app.get("/")
async def root():
    """Health check."""
    return {"status": "ok", "service": "InviGrid Travel Assistant API v2.0"}


@app.post("/api/session", response_model=SessionResponse)
async def create_session():
    """Create a new chat session."""
    session_id = str(uuid.uuid4())
    get_memory(session_id)  # Initialize memory
    return SessionResponse(
        session_id=session_id,
        created_at=datetime.now().isoformat()
    )


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Send a message and get a response."""
    try:
        # Run in executor to not block
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, 
            handle_chat_sync, 
            request.session_id, 
            request.message
        )
        return ChatResponse(**result)
    except Exception as e:
        log_error("API", f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/session/{session_id}")
async def delete_session(session_id: str):
    """Clear a session's memory."""
    clear_memory(session_id)
    return {"status": "cleared", "session_id": session_id}


@app.get("/api/session/{session_id}/context")
async def get_session_context(session_id: str):
    """Get current session context (for debugging)."""
    memory = get_memory(session_id)
    return {
        "session_id": session_id,
        "user_language": memory.user_language,
        "search_results_count": len(memory.search_results),
        "search_type": memory.search_type,
        "booking_stage": memory.booking_state.get("stage"),
        "message_count": len(memory.messages)
    }


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
    """WebSocket endpoint for real-time chat."""
    await manager.connect(websocket, session_id)
    
    try:
        while True:
            data = await websocket.receive_json()
            
            if data.get("type") == "message":
                user_content = data.get("content", "").strip()
                
                if not user_content:
                    continue
                
                # Send thinking status
                await manager.send_message(session_id, {
                    "type": "thinking",
                    "message": "Processing your request..."
                })
                
                try:
                    # Process message
                    loop = asyncio.get_event_loop()
                    result = await loop.run_in_executor(
                        None,
                        handle_chat_sync,
                        session_id,
                        user_content
                    )
                    
                    # Send response
                    await manager.send_message(session_id, {
                        "type": "response",
                        **result
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
