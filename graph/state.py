from typing import TypedDict, Annotated, List, Union, Dict, Any
from langchain_core.messages import BaseMessage
import operator

class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], operator.add]
    user_language: str
    next_agent: str
    booking_context: Dict[str, Any]
