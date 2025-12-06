"""
Logging utility for agent handoffs and debugging.
"""
import logging
from datetime import datetime
from typing import Any, Dict, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%H:%M:%S'
)

logger = logging.getLogger("travel_assistant")

def log_agent_handoff(
    from_agent: str, 
    to_agent: str, 
    message: str, 
    context: Optional[Dict[str, Any]] = None
) -> None:
    """
    Log an agent handoff with context information.
    
    Args:
        from_agent: Name of the sending agent
        to_agent: Name of the receiving agent  
        message: The message being passed (truncated for display)
        context: Optional context dictionary with state info
    """
    ctx = context or {}
    search_count = len(ctx.get("last_search_results", []))
    booking_stage = ctx.get("booking_stage", "none")
    language = ctx.get("user_language", "unknown")
    
    logger.info(f"[HANDOFF] {from_agent} → {to_agent}")
    logger.info(f"  Language: {language} | Search Results: {search_count} | Booking: {booking_stage}")
    logger.debug(f"  Message: {message[:150]}..." if len(message) > 150 else f"  Message: {message}")

def log_tool_call(tool_name: str, params: Dict[str, Any], result_count: int) -> None:
    """Log a tool invocation."""
    logger.info(f"[TOOL] {tool_name}({params}) → {result_count} results")

def log_llm_call(purpose: str, input_preview: str) -> None:
    """Log an LLM invocation."""
    logger.debug(f"[LLM] {purpose}: {input_preview[:100]}...")

def log_error(agent: str, error: str, context: Optional[Dict] = None) -> None:
    """Log an error with context."""
    logger.error(f"[ERROR] {agent}: {error}")
    if context:
        logger.error(f"  Context: {context}")
