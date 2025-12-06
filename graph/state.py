"""
Enhanced State Definition for LangGraph Workflow.
Properly typed state with all context fields.
"""
from typing import TypedDict, Annotated, List, Dict, Any, Optional, Literal
from langchain_core.messages import BaseMessage
import operator
from agents.a2a_schema import A2AMessage

# Allowed values for booking stage
BookingStage = Literal[None, "confirm", "details", "payment", "complete"]

# Allowed values for search context
SearchContext = Literal["unknown", "flight", "hotel", "train", "bus", "recommendation"]


class AgentState(TypedDict):
    """
    Unified state that flows through all nodes in the LangGraph.
    
    Attributes:
        messages: LangChain message history for the conversation
        a2a_log: Agent-to-Agent communication log (our protocol)
        user_language: Detected language of the user (e.g., "Hindi", "English")
        next_agent: Which agent to route to next
        booking_context: Booking state including selected_item, user_details, etc.
        last_search_results: Results from the most recent search (flights/hotels/etc)
        search_context: Type of the last search performed
        booking_stage: Current stage in the booking flow
    """
    # Message history (appends with operator.add)
    messages: Annotated[List[BaseMessage], operator.add]
    
    # A2A protocol log (appends with operator.add)
    a2a_log: Annotated[List[A2AMessage], operator.add]
    
    # User's detected language
    user_language: str
    
    # Router decision
    next_agent: str
    
    # Booking workflow state
    booking_context: Dict[str, Any]
    
    # Search results from travel agent - CRITICAL for multi-turn
    last_search_results: List[Dict[str, Any]]
    
    # Type of search performed
    search_context: str
    
    # Current booking stage
    booking_stage: Optional[str]


def create_initial_state(session_id: str) -> AgentState:
    """
    Create a fresh initial state for a new conversation.
    
    Args:
        session_id: Unique identifier for this conversation session
        
    Returns:
        AgentState with default values
    """
    return {
        "messages": [],
        "a2a_log": [],
        "user_language": "English",
        "next_agent": "travel_agent",
        "booking_context": {"session_id": session_id},
        "last_search_results": [],
        "search_context": "unknown",
        "booking_stage": None,
    }
