from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage
from graph.state import AgentState
from agents.translation_agent import translate_to_english, translate_to_user_lang
from agents.travel_agent import run_travel_agent
from agents.booking_agent import handle_booking
from agents.a2a_schema import A2AMessage
from data.chat_repo import save_chat_message
from validation.input_guards import validate_user_input, validate_message_length
from validation.output_guards import validate_agent_output
import streamlit as st # Access session state for ID

# --- Nodes ---

def translation_input_node(state: AgentState):
    """
    Detects language and translates input to English.
    """
    messages = state['messages']
    last_message = messages[-1]
    
    if isinstance(last_message, HumanMessage):
        text = last_message.content
        
        # GUARDRAILS: Validate input
        if not validate_message_length(text):
            return {
                "messages": [AIMessage(content="Your message is too long. Please keep it under 500 characters.")]
            }
        
        validation_result = validate_user_input(text)
        if not validation_result['valid']:
            error_msg = f"I'm sorry, but I can't process that message. Please rephrase and try again."
            return {
                "messages": [AIMessage(content=error_msg)]
            }
        
        # Use cleaned text from guardrails
        cleaned_text = validation_result['cleaned_text']
        
        # PERSISTENCE: Save User Message
        session_id = state.get("booking_context", {}).get("session_id", "default")
        save_chat_message(session_id, "user", cleaned_text)
        
        a2a_msg = translate_to_english(cleaned_text)
        
        return {
            "user_language": a2a_msg.context.get("detected_language", "English"),
            "a2a_log": [a2a_msg]
        }
    return {}

def router_node(state: AgentState):
    """
    Decides which agent to route to based on intent.
    """
    # Look at the last A2A message (which is the translated one)
    last_a2a = state['a2a_log'][-1]
    text = last_a2a.content.lower()
    
    if "book" in text or "reserve" in text or "confirm" in text:
        return {"next_agent": "booking_agent"}
    else:
        return {"next_agent": "travel_agent"}

def travel_agent_node(state: AgentState):
    """
    Invokes the Travel Services Agent.
    """
    last_a2a = state['a2a_log'][-1]
    # Pass history (excluding the last message which is the current user input)
    # The agent will see the translated current input as 'input'
    chat_history = state['messages'][:-1]
    
    response_msg = run_travel_agent(last_a2a, chat_history)
    
    # GUARDRAILS: Validate Output
    # (Optional: Pass search results in context if we had them available here)
    validation_result = validate_agent_output(response_msg.content)
    
    if not validation_result['valid']:
        # If toxic or hallucinated, replace with safe message
        safe_response = "I apologize, but I couldn't verify the results. Please try searching again."
        response_msg.content = safe_response
        
    # Phase 2: Context Tracking
    # Extract search context from message
    last_results = response_msg.context.get("search_results", [])
    search_type = response_msg.context.get("search_type", "unknown")
    
    return {
        "a2a_log": [response_msg],
        "last_search_results": last_results,
        "search_context": search_type
    }

def booking_agent_node(state: AgentState):
    """
    Invokes the Booking Agent.
    """
    last_a2a = state['a2a_log'][-1]
    response_msg = handle_booking(state.get("booking_context", {}), last_a2a)
    return {"a2a_log": [response_msg]}

def translation_output_node(state: AgentState):
    """
    Translates the AI response back to the user's language.
    """
    last_a2a = state['a2a_log'][-1]
    user_lang = state.get("user_language", "English")
    
    translated_msg = translate_to_user_lang(last_a2a.content, user_lang)
    
    # PERSISTENCE: Save AI Message
    session_id = state.get("booking_context", {}).get("session_id", "default")
    save_chat_message(session_id, "assistant", translated_msg.content)
    
    # Update LangChain history for the UI
    return {
        "a2a_log": [translated_msg],
        "messages": [AIMessage(content=translated_msg.content)]
    }

# --- Graph Construction ---

workflow = StateGraph(AgentState)

workflow.add_node("translation_input", translation_input_node)
workflow.add_node("router", router_node)
workflow.add_node("travel_agent", travel_agent_node)
workflow.add_node("booking_agent", booking_agent_node)
workflow.add_node("translation_output", translation_output_node)

workflow.set_entry_point("translation_input")

workflow.add_edge("translation_input", "router")

def route_decision(state):
    return state["next_agent"]

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

app_graph = workflow.compile()
