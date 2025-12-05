from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage
from graph.state import AgentState
from agents.translation_agent import translate_to_english, translate_to_user_lang
from agents.travel_agent import travel_agent_executor
from agents.booking_agent import handle_booking
from agents.llm_engine import get_llm
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# --- Nodes ---

def translation_input_node(state: AgentState):
    """
    Detects language and translates input to English.
    """
    messages = state['messages']
    last_message = messages[-1]
    
    if isinstance(last_message, HumanMessage):
        text = last_message.content
        lang, translated_text = translate_to_english(text)
        
        # Update state with detected language and translated message
        # We replace the last message content with English for the agents to understand
        # But we might want to keep the original for display? 
        # For simplicity, we'll append a system message or just update the content.
        # Let's update the content in a new message to keep history clean?
        # Actually, standard practice is to just pass the translated text to the agent.
        
        return {
            "user_language": lang,
            "messages": [HumanMessage(content=translated_text)] 
        }
    return {}

def router_node(state: AgentState):
    """
    Decides which agent to route to based on intent.
    """
    messages = state['messages']
    last_message = messages[-1]
    text = last_message.content.lower()
    
    # Simple keyword routing for MVP
    if "book" in text or "reserve" in text or "confirm" in text:
        return {"next_agent": "booking_agent"}
    else:
        return {"next_agent": "travel_agent"}

def travel_agent_node(state: AgentState):
    """
    Invokes the Travel Services Agent.
    """
    messages = state['messages']
    # We need to pass the conversation history to the agent
    # The agent executor expects 'input' or 'chat_history'
    
    # Extract the last user message
    last_user_msg = messages[-1].content
    
    response = travel_agent_executor.invoke({"input": last_user_msg})
    return {"messages": [AIMessage(content=response['output'])]}

def booking_agent_node(state: AgentState):
    """
    Invokes the Booking Agent.
    """
    messages = state['messages']
    last_user_msg = messages[-1].content
    
    response = handle_booking(state.get("booking_context", {}), last_user_msg)
    return {"messages": [AIMessage(content=response)]}

def translation_output_node(state: AgentState):
    """
    Translates the AI response back to the user's language.
    """
    messages = state['messages']
    last_message = messages[-1]
    user_lang = state.get("user_language", "English")
    
    if isinstance(last_message, AIMessage):
        original_text = last_message.content
        translated_text = translate_to_user_lang(original_text, user_lang)
        
        # Replace the AI message with the translated one
        # Or just return it. LangGraph appends returned messages.
        # We want to overwrite or append? 
        # Let's return a new message with the translated content.
        # But we need to make sure we don't duplicate.
        # For the UI, we'll display the last message.
        
        return {"messages": [AIMessage(content=translated_text)]}
    return {}

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
