from typing import Dict, Any, Optional, List, Literal
from pydantic import BaseModel, Field
import datetime

class AgentCard(BaseModel):
    """
    Metadata defining an agent's capabilities.
    """
    name: str
    description: str
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    version: str = "1.0.0"
    capabilities: List[str] = []

class A2AMessage(BaseModel):
    """
    Standardized message format for Agent-to-Agent communication.
    """
    message_id: str = Field(default_factory=lambda: datetime.datetime.now().isoformat())
    timestamp: str = Field(default_factory=lambda: datetime.datetime.now().isoformat())
    sender: str
    receiver: str
    message_type: Literal["TASK", "RESPONSE", "ERROR", "INFO"]
    content: str
    context: Dict[str, Any] = {}
    
    def to_dict(self):
        return self.model_dump()
