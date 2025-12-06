"""
Intent Router

Simple LLM-based classification to route messages to the appropriate agent.
Uses structured output to determine: "travel" or "booking"
"""
from agents.llm_engine import get_llm
from agents.memory import ConversationMemory
from agents.logger import log_llm_call, log_error
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser


ROUTER_PROMPT = """Classify the user's intent into ONE category.

CONTEXT:
- Has search results: {has_results}
- Current booking stage: {booking_stage}
- Search type: {search_type}

USER MESSAGE: "{message}"

CATEGORIES:
BOOKING - User wants to book, reserve, confirm, or continue a booking process.
Examples: "book it", "the first one", "the cheapest", "yes confirm", "proceed", "my name is John", "1234" (card digits)

TRAVEL - User wants to search, find, or get information about travel options.
Examples: "show flights", "find hotels", "trains to Chennai", "attractions in Goa", "weather tips"

RULES:
1. If user is in an active booking flow (stage is confirm/details/payment), classify as BOOKING
2. If user mentions booking/reserving/selecting from results, classify as BOOKING
3. For new searches or information requests, classify as TRAVEL

Respond with ONLY one word: BOOKING or TRAVEL"""


def classify_intent(message: str, memory: ConversationMemory) -> str:
    """
    Classify user intent to route to appropriate agent.
    
    Args:
        message: Translated English message
        memory: Conversation memory with context
        
    Returns:
        "travel" or "booking"
    """
    has_results = len(memory.search_results) > 0
    booking_stage = memory.booking_state.get("stage")
    search_type = memory.search_type
    
    # Quick check: if in active booking flow, continue with booking
    if booking_stage and booking_stage in ["confirm", "details", "payment"]:
        return "booking"
    
    try:
        log_llm_call("router", message[:50])
        
        llm = get_llm()
        prompt = ChatPromptTemplate.from_template(ROUTER_PROMPT)
        chain = prompt | llm | StrOutputParser()
        
        result = chain.invoke({
            "message": message,
            "has_results": has_results,
            "booking_stage": booking_stage or "none",
            "search_type": search_type
        })
        
        result = result.strip().upper()
        
        if "BOOKING" in result:
            # Validate: can only book if we have results
            if has_results or booking_stage:
                return "booking"
            else:
                return "travel"  # No results to book, redirect to search
        else:
            return "travel"
            
    except Exception as e:
        log_error("Router", f"Classification failed: {e}")
        # Fallback to keyword matching
        return _fallback_classification(message, has_results, booking_stage)


def _fallback_classification(message: str, has_results: bool, booking_stage: str) -> str:
    """Fallback keyword-based classification."""
    msg_lower = message.lower()
    
    booking_keywords = [
        "book", "reserve", "confirm", "select", "choose",
        "first one", "second one", "cheapest", "expensive",
        "proceed", "yes", "ok", "sure", "go ahead"
    ]
    
    for keyword in booking_keywords:
        if keyword in msg_lower:
            if has_results or booking_stage:
                return "booking"
    
    return "travel"
