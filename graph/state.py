from typing import TypedDict, Annotated, List, Union, Dict, Any
from langchain_core.messages import BaseMessage
import operator
from agents.a2a_schema import A2AMessage

class AgentState(TypedDict):
    # We keep 'messages' for LangChain internal history if needed, 
    # but 'a2a_log' will track the official protocol exchange.
    messages: Annotated[List[BaseMessage], operator.add] 
    a2a_log: Annotated[List[A2AMessage], operator.add]
    user_language: str
    next_agent: str
    booking_context: Dict[str, Any]
    last_search_results: List[Dict[str, Any]] # Phase 2: Context Tracking
    search_context: str # flight, hotel, train, bus
