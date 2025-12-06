"""
Conversation Memory - Central State Management

Stores all conversation context in one place:
- Recent messages
- Summarized older context  
- Search results
- Booking state
- Language preferences

Each agent reads from and writes to this memory.
"""
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
import json


@dataclass
class ConversationMemory:
    """
    Central memory store for a conversation session.
    
    This is the single source of truth for all context.
    Agents read from it and write back to it.
    """
    session_id: str
    
    # Message history
    messages: List[Dict[str, str]] = field(default_factory=list)  # [{role, content}]
    summary: str = ""  # Summary of older messages
    
    # Search state
    search_results: List[Dict[str, Any]] = field(default_factory=list)
    search_type: str = "unknown"  # "flight", "hotel", "train", "bus", "recommendation"
    
    # Booking state
    booking_state: Dict[str, Any] = field(default_factory=lambda: {
        "stage": None,  # None, "confirm", "details", "payment", "complete"
        "selected_item": None,
        "user_details": {},
        "confirmation_id": None
    })
    
    # Language state
    user_language: str = "English"
    language_history: List[str] = field(default_factory=list)
    locale_preferences: Dict[str, str] = field(default_factory=lambda: {
        "currency": "INR",
        "currency_symbol": "₹",
        "date_format": "DD-MM-YYYY",
        "time_format": "12hr"
    })
    
    # Metadata
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_updated: str = field(default_factory=lambda: datetime.now().isoformat())
    
    # Configuration
    max_recent_messages: int = 6  # Keep last 6 full messages
    summarize_threshold: int = 10  # Summarize when > 10 messages
    
    def add_message(self, role: str, content: str) -> None:
        """Add a message to history."""
        self.messages.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
        self.last_updated = datetime.now().isoformat()
    
    def get_recent_messages(self, n: Optional[int] = None) -> List[Dict[str, str]]:
        """Get the n most recent messages."""
        count = n or self.max_recent_messages
        return self.messages[-count:]
    
    def get_context_for_llm(self) -> str:
        """
        Format memory as context string for LLM system prompt.
        Includes summary + recent messages + current state.
        """
        parts = []
        
        # Add summary if exists
        if self.summary:
            parts.append(f"## Conversation Summary\n{self.summary}")
        
        # Add recent messages
        recent = self.get_recent_messages()
        if recent:
            msg_lines = []
            for msg in recent:
                role = "User" if msg["role"] == "user" else "Assistant"
                msg_lines.append(f"{role}: {msg['content']}")
            parts.append(f"## Recent Conversation\n" + "\n".join(msg_lines))
        
        # Add search results if any
        if self.search_results:
            parts.append(f"## Current Search Results ({self.search_type})")
            for i, item in enumerate(self.search_results[:5], 1):  # Show max 5
                parts.append(f"{i}. {self._format_search_item(item)}")
        
        # Add booking state if active
        if self.booking_state.get("stage"):
            parts.append(f"## Booking Status")
            parts.append(f"Stage: {self.booking_state['stage']}")
            if self.booking_state.get("selected_item"):
                parts.append(f"Selected: {self._format_search_item(self.booking_state['selected_item'])}")
        
        return "\n\n".join(parts) if parts else "No previous context."
    
    def _format_search_item(self, item: Dict) -> str:
        """Format a search result item as a string."""
        if "flight_number" in item:
            return f"{item.get('airline', '')} {item.get('flight_number', '')} - {item.get('origin', '')}→{item.get('destination', '')} ₹{item.get('price', 'N/A')}"
        elif "train_number" in item:
            return f"{item.get('name', '')} ({item.get('train_number', '')}) - ₹{item.get('price', 'N/A')}"
        elif "price_per_night" in item:
            return f"{item.get('name', '')} - ⭐{item.get('rating', '')} ₹{item.get('price_per_night', 'N/A')}/night"
        elif "operator" in item:
            return f"{item.get('operator', '')} - {item.get('origin', '')}→{item.get('destination', '')} ₹{item.get('price', 'N/A')}"
        else:
            return str(item)
    
    def update_search_results(self, results: List[Dict], search_type: str) -> None:
        """Update search results and clear booking state for new search."""
        self.search_results = results
        self.search_type = search_type
        # Reset booking when new search is done
        self.booking_state = {
            "stage": None,
            "selected_item": None,
            "user_details": {},
            "confirmation_id": None
        }
        self.last_updated = datetime.now().isoformat()
    
    def update_booking_state(self, updates: Dict[str, Any]) -> None:
        """Update booking state with new values."""
        self.booking_state.update(updates)
        self.last_updated = datetime.now().isoformat()
    
    def update_language(self, detected_language: str) -> None:
        """Update language and locale preferences."""
        if detected_language != self.user_language:
            self.language_history.append(self.user_language)
            self.user_language = detected_language
            self.locale_preferences = self._get_locale_for_language(detected_language)
    
    def _get_locale_for_language(self, language: str) -> Dict[str, str]:
        """Get locale preferences based on detected language."""
        # Default to Indian locale for Indian languages
        indian_languages = ["Hindi", "Tamil", "Telugu", "Bengali", "Marathi", "Gujarati", "Kannada", "Malayalam", "Punjabi"]
        
        if language in indian_languages or language == "English":
            return {
                "currency": "INR",
                "currency_symbol": "₹",
                "date_format": "DD-MM-YYYY",
                "time_format": "12hr"
            }
        else:
            return {
                "currency": "USD",
                "currency_symbol": "$",
                "date_format": "MM-DD-YYYY",
                "time_format": "12hr"
            }
    
    def needs_summarization(self) -> bool:
        """Check if we should summarize older messages."""
        return len(self.messages) > self.summarize_threshold
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "session_id": self.session_id,
            "messages": self.messages,
            "summary": self.summary,
            "search_results": self.search_results,
            "search_type": self.search_type,
            "booking_state": self.booking_state,
            "user_language": self.user_language,
            "locale_preferences": self.locale_preferences,
            "created_at": self.created_at,
            "last_updated": self.last_updated
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConversationMemory":
        """Create from dictionary."""
        memory = cls(session_id=data["session_id"])
        memory.messages = data.get("messages", [])
        memory.summary = data.get("summary", "")
        memory.search_results = data.get("search_results", [])
        memory.search_type = data.get("search_type", "unknown")
        memory.booking_state = data.get("booking_state", {})
        memory.user_language = data.get("user_language", "English")
        memory.locale_preferences = data.get("locale_preferences", {})
        memory.created_at = data.get("created_at", datetime.now().isoformat())
        memory.last_updated = data.get("last_updated", datetime.now().isoformat())
        return memory


# In-memory store for sessions (use Redis in production)
_memory_store: Dict[str, ConversationMemory] = {}


def get_memory(session_id: str) -> ConversationMemory:
    """Get or create memory for a session."""
    if session_id not in _memory_store:
        _memory_store[session_id] = ConversationMemory(session_id=session_id)
    return _memory_store[session_id]


def clear_memory(session_id: str) -> None:
    """Clear memory for a session."""
    if session_id in _memory_store:
        del _memory_store[session_id]


def get_all_sessions() -> List[str]:
    """Get all active session IDs."""
    return list(_memory_store.keys())
