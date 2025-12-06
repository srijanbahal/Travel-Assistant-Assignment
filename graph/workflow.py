"""
LangGraph Workflow for Multi-Agent Travel Assistant

Orchestrates the flow between:
1. Translation Agent (input) - detects language, translates to English
2. Router - uses LLM to classify intent
3. Travel Agent - handles search queries
4. Booking Agent - handles booking flow
5. Translation Agent (output) - translates response to user's language
"""
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from graph.state import AgentState
from agents.translation_agent import translate_to_english, translate_to_user_lang
from agents.travel_agent import run_travel_agent
from agents.booking_agent import handle_booking
from agents.a2a_schema import A2AMessage
from agents.llm_engine import get_llm
from agents.logger import log_agent_handoff, log_error
from data.chat_repo import save_chat_message
from validation.input_guards import validate_user_input, validate_message_length
from validation.output_guards import validate_agent_output
from typing import Dict, Any


# ============== Router Intent Classification ==============

ROUTER_PROMPT = """Classify the user's intent into ONE of these categories:

BOOKING - User wants to book, reserve, or confirm something from previous results
Examples: "book it", "reserve the first one", "I'll take the cheapest", "book flight 1", "yes confirm", "proceed with booking"

TRAVEL - User wants to search, find, or get information about travel options
Examples: "show me flights", "find hotels in Delhi", "when is the next train", "attractions in Goa", "restaurants near me"

Context:
- Has previous search results: {has_results}
- Current booking stage: {booking_stage}
- Search type: {search_type}

User message: "{user_message}"

Respond with ONLY one word: BOOKING or TRAVEL"""


def classify_intent(user_message: str, state: Dict[str, Any]) -> str:
    """
    Use LLM to classify user intent as 'booking_agent' or 'travel_agent'.
    
    Falls back to keyword matching if LLM fails.
    """
    has_results = len(state.get("last_search_results", [])) > 0
    booking_stage = state.get("booking_stage")
    search_type = state.get("search_context", "unknown")
    
    # If in active booking flow, continue with booking
    if booking_stage and booking_stage not in [None, "complete"]:
        return "booking_agent"
    
    try:
        llm = get_llm()
        prompt = ChatPromptTemplate.from_template(ROUTER_PROMPT)
        chain = prompt | llm | StrOutputParser()
        
        result = chain.invoke({
            "user_message": user_message,
            "has_results": has_results,
            "booking_stage": booking_stage or "none",
            "search_type": search_type
        })
        
        result = result.strip().upper()
        
        if "BOOKING" in result:
            # Validate: can only book if we have results
            if has_results:
                return "booking_agent"
            else:
                return "travel_agent"  # Redirect to search first
        else:
            return "travel_agent"
            
    except Exception as e:
        log_error("Router", f"LLM classification failed: {e}")
        # Fallback to keyword matching
        return _fallback_intent_classification(user_message, has_results)


def _fallback_intent_classification(text: str, has_results: bool) -> str:
    """Fallback keyword-based intent classification."""
    text_lower = text.lower()
    
    booking_keywords = [
        "book", "reserve", "confirm", "select", "choose",
        "go with", "take this", "i'll take", "want this",
        "first one", "second one", "third one", "cheapest",
        "proceed", "finalize", "yes"
    ]
    
    for keyword in booking_keywords:
        if keyword in text_lower:
            if has_results:
                return "booking_agent"
    
    return "travel_agent"


# ============== Workflow Nodes ==============

def translation_input_node(state: AgentState) -> Dict[str, Any]:
    """
    Entry point: Detect language and translate input to English.
    """
    messages = state["messages"]
    last_message = messages[-1]
    
    if not isinstance(last_message, HumanMessage):
        return {}
    
    text = last_message.content
    
    # GUARDRAILS: Validate input
    if not validate_message_length(text):
        return {
            "messages": [AIMessage(content="Your message is too long. Please keep it under 500 characters.")]
        }
    
    validation_result = validate_user_input(text)
    if not validation_result["valid"]:
        return {
            "messages": [AIMessage(content="I'm sorry, but I can't process that message. Please rephrase and try again.")]
        }
    
    cleaned_text = validation_result["cleaned_text"]
    
    # Save user message to DB
    session_id = state.get("booking_context", {}).get("session_id", "default")
    try:
        save_chat_message(session_id, "user", cleaned_text)
    except Exception as e:
        log_error("TranslationInput", f"Failed to save message: {e}")
    
    # Translate to English
    a2a_msg = translate_to_english(cleaned_text)
    
    log_agent_handoff("User", "TranslationAgent", cleaned_text, state)
    
    return {
        "user_language": a2a_msg.context.get("detected_language", "English"),
        "a2a_log": [a2a_msg]
    }


def router_node(state: AgentState) -> Dict[str, Any]:
    """
    Route to appropriate agent based on intent classification.
    """
    # Get the translated message
    a2a_log = state.get("a2a_log", [])
    if not a2a_log:
        return {"next_agent": "travel_agent"}
    
    last_a2a = a2a_log[-1]
    text = last_a2a.content
    
    # Classify intent using LLM
    next_agent = classify_intent(text, state)
    
    log_agent_handoff("TranslationAgent", "Router", f"Routing to {next_agent}", state)
    
    return {"next_agent": next_agent}


def travel_agent_node(state: AgentState) -> Dict[str, Any]:
    """
    Handle travel search queries.
    """
    a2a_log = state.get("a2a_log", [])
    if not a2a_log:
        return {}
    
    last_a2a = a2a_log[-1]
    chat_history = state["messages"][:-1]  # Exclude current message
    
    # Pass context to travel agent
    context = {
        "last_search_results": state.get("last_search_results", []),
        "search_context": state.get("search_context", "unknown"),
        "booking_context": state.get("booking_context", {}),
    }
    
    log_agent_handoff("Router", "TravelAgent", last_a2a.content, state)
    
    # Run travel agent
    response_msg = run_travel_agent(last_a2a, chat_history, context)
    
    # Validate output
    validation_result = validate_agent_output(response_msg.content)
    if not validation_result["valid"]:
        response_msg.content = "I apologize, but I couldn't verify the results. Please try searching again."
    
    # Extract search results from response
    last_results = response_msg.context.get("search_results", [])
    search_type = response_msg.context.get("search_type", "unknown")
    
    # CRITICAL: Proper state update
    # If we got new search results, update them
    # If not, preserve the old ones
    new_results = last_results if last_results else state.get("last_search_results", [])
    new_type = search_type if last_results else state.get("search_context", "unknown")
    
    # When doing a new search, reset booking context (keep session_id)
    session_id = state.get("booking_context", {}).get("session_id")
    new_booking_context = {"session_id": session_id} if last_results else state.get("booking_context", {})
    
    return {
        "a2a_log": [response_msg],
        "last_search_results": new_results,
        "search_context": new_type,
        "booking_context": new_booking_context,
        "booking_stage": None if last_results else state.get("booking_stage"),
    }


def booking_agent_node(state: AgentState) -> Dict[str, Any]:
    """
    Handle booking workflow.
    """
    a2a_log = state.get("a2a_log", [])
    if not a2a_log:
        return {}
    
    last_a2a = a2a_log[-1]
    
    log_agent_handoff("Router", "BookingAgent", last_a2a.content, state)
    
    # Run booking agent
    response_msg = handle_booking(state, last_a2a)
    
    # Extract updated booking context
    updated_context = response_msg.context.get("updated_booking_context", {})
    new_stage = response_msg.context.get("booking_stage")
    
    # Merge with existing context
    current_context = state.get("booking_context", {}).copy()
    current_context.update(updated_context)
    
    return {
        "a2a_log": [response_msg],
        "booking_context": current_context,
        "booking_stage": new_stage,
        # CRITICAL: Preserve search results for potential re-booking
        "last_search_results": state.get("last_search_results", []),
        "search_context": state.get("search_context", "unknown"),
    }


def translation_output_node(state: AgentState) -> Dict[str, Any]:
    """
    Translate AI response back to user's language.
    """
    a2a_log = state.get("a2a_log", [])
    if not a2a_log:
        return {}
    
    last_a2a = a2a_log[-1]
    user_lang = state.get("user_language", "English")
    
    log_agent_handoff("Agent", "TranslationOutput", f"Translating to {user_lang}", state)
    
    # Translate response
    translated_msg = translate_to_user_lang(last_a2a.content, user_lang)
    
    # Save AI message to DB
    session_id = state.get("booking_context", {}).get("session_id", "default")
    try:
        save_chat_message(session_id, "assistant", translated_msg.content)
    except Exception as e:
        log_error("TranslationOutput", f"Failed to save message: {e}")
    
    # Return with original English in metadata for UI toggle
    return {
        "a2a_log": [translated_msg],
        "messages": [
            AIMessage(
                content=translated_msg.content, 
                additional_kwargs={"original_english": last_a2a.content}
            )
        ]
    }


# ============== Conditional Edges ==============

def check_input_validity(state: AgentState) -> str:
    """
    Check if input validation passed.
    If validation failed, translation_input_node returns an AIMessage directly.
    """
    last_msg = state["messages"][-1]
    if isinstance(last_msg, AIMessage):
        return "end"  # Validation failed, error message already set
    return "continue"


def route_decision(state: AgentState) -> str:
    """Return the next agent from router decision."""
    return state.get("next_agent", "travel_agent")


# ============== Build Graph ==============

workflow = StateGraph(AgentState)

# Add nodes
workflow.add_node("translation_input", translation_input_node)
workflow.add_node("router", router_node)
workflow.add_node("travel_agent", travel_agent_node)
workflow.add_node("booking_agent", booking_agent_node)
workflow.add_node("translation_output", translation_output_node)

# Set entry point
workflow.set_entry_point("translation_input")

# Add edges
workflow.add_conditional_edges(
    "translation_input",
    check_input_validity,
    {
        "continue": "router",
        "end": END
    }
)

workflow.add_conditional_edges(
    "router",
    route_decision,
    {
        "travel_agent": "travel_agent",
        "booking_agent": "booking_agent"
    }
)

workflow.add_edge("travel_agent", "translation_output")
workflow.add_edge("booking_agent", "translation_output")
workflow.add_edge("translation_output", END)

# Compile
app_graph = workflow.compile()
