"""
Travel Services Agent

Handles travel-related queries using direct LLM tool calling.
Processes: flights, hotels, trains, buses, recommendations, weather/tips.
"""
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from tools.flights import search_flights, search_next_available_flight
from tools.hotels import search_hotels  
from tools.trains import search_trains, search_buses
from tools.recommendations import get_attractions, get_restaurants, get_cultural_tips
from agents.llm_engine import get_llm
from agents.a2a_schema import A2AMessage
from agents.logger import log_tool_call, log_llm_call, log_error
from datetime import datetime
from typing import List, Dict, Any, Tuple
import json

# All available tools
TOOLS = [
    search_flights, 
    search_next_available_flight,
    search_hotels, 
    search_trains, 
    search_buses,
    get_attractions,
    get_restaurants,
    get_cultural_tips
]

# System prompt for the travel agent
SYSTEM_PROMPT = """You are a helpful travel assistant. Today is {current_date}.

CAPABILITIES:
1. Flight Search - search_flights(origin, destination, date) or search_next_available_flight(origin, destination)
2. Hotel Search - search_hotels(location)
3. Train Search - search_trains(origin, destination, date)
4. Bus Search - search_buses(origin, destination, date)
5. Attractions - get_attractions(location)
6. Restaurants - get_restaurants(location)
7. Cultural Tips - get_cultural_tips(location)

CONTEXT FROM PREVIOUS SEARCHES:
{context_summary}

CONVERSATION HISTORY:
{history_summary}

CRITICAL RULES:
1. ALWAYS use tools when the user asks for travel information
2. If a required parameter is missing, ASK for it (don't guess)
3. For dates like "tomorrow", "next week" - calculate the actual date
4. If no results found, suggest alternatives (nearby dates, different transport)
5. Format results clearly with prices, times, and key details
6. End responses with a helpful follow-up question
7. If user references previous results ("the first one", "cheapest"), use the CONTEXT above

DATE HANDLING:
- "tomorrow" = {tomorrow_date}
- "day after tomorrow" = {day_after_date}
- "next week" = approximately {next_week_date}

RESPONSE FORMAT:
- Use markdown formatting (bold, bullets)
- Include all relevant details (prices, times, ratings)
- Be concise but complete"""


def run_travel_agent(
    input_msg: A2AMessage, 
    chat_history: List, 
    context: Dict[str, Any] = None
) -> A2AMessage:
    """
    Process a travel-related query using LLM with tool calling.
    
    Args:
        input_msg: The translated user message
        chat_history: Previous conversation messages
        context: Current state including last_search_results
        
    Returns:
        A2AMessage with response and any search results
    """
    context = context or {}
    current_date = datetime.now()
    
    # Build context summary for the LLM
    context_summary = _build_context_summary(context)
    history_summary = _build_history_summary(chat_history[-6:] if chat_history else [])
    
    # Calculate date references
    tomorrow = (current_date + __import__('datetime').timedelta(days=1)).strftime("%Y-%m-%d")
    day_after = (current_date + __import__('datetime').timedelta(days=2)).strftime("%Y-%m-%d")
    next_week = (current_date + __import__('datetime').timedelta(days=7)).strftime("%Y-%m-%d")
    
    # Format system prompt
    system_content = SYSTEM_PROMPT.format(
        current_date=current_date.strftime("%Y-%m-%d"),
        context_summary=context_summary,
        history_summary=history_summary,
        tomorrow_date=tomorrow,
        day_after_date=day_after,
        next_week_date=next_week
    )
    
    try:
        # Get LLM with tools bound
        llm = get_llm()
        llm_with_tools = llm.bind_tools(TOOLS)
        
        log_llm_call("travel_agent", input_msg.content)
        
        # Invoke the LLM
        messages = [
            SystemMessage(content=system_content),
            HumanMessage(content=input_msg.content)
        ]
        
        response = llm_with_tools.invoke(messages)
        
        # Process tool calls if any
        search_results = []
        search_type = "unknown"
        
        if response.tool_calls:
            search_results, search_type, tool_output = _execute_tool_calls(response.tool_calls)
            
            # If we got results, ask LLM to format them nicely
            if search_results:
                formatted_response = _format_results_with_llm(
                    input_msg.content, 
                    search_results, 
                    search_type,
                    llm
                )
            else:
                formatted_response = tool_output or "I couldn't find any results. Would you like to try different dates or locations?"
        else:
            # No tool calls - LLM responded directly
            formatted_response = response.content if response.content else "I need more details. Where would you like to travel?"
        
        # Ensure response is a string
        if isinstance(formatted_response, list):
            formatted_response = _extract_text_from_response(formatted_response)
        
        return A2AMessage(
            sender="TravelAgent",
            receiver="TranslationAgent",
            message_type="RESPONSE",
            content=str(formatted_response),
            context={
                "search_results": search_results,
                "search_type": search_type
            }
        )
        
    except Exception as e:
        log_error("TravelAgent", f"Error: {str(e)}")
        return A2AMessage(
            sender="TravelAgent",
            receiver="TranslationAgent",
            message_type="RESPONSE",
            content="I apologize, I'm having trouble processing your request. Could you please rephrase or try again?",
            context={"search_results": [], "search_type": "unknown", "error": str(e)}
        )


def _execute_tool_calls(tool_calls: List) -> Tuple[List[Dict], str, str]:
    """
    Execute tool calls and return aggregated results.
    
    Returns:
        Tuple of (results_list, search_type, raw_output_string)
    """
    all_results = []
    search_type = "unknown"
    output_parts = []
    
    for tool_call in tool_calls:
        tool_name = tool_call["name"]
        tool_args = tool_call["args"]
        
        # Find and execute the tool
        tool_func = _get_tool_by_name(tool_name)
        if tool_func:
            try:
                result = tool_func.invoke(tool_args)
                log_tool_call(tool_name, tool_args, len(result) if isinstance(result, list) else 1)
                
                if isinstance(result, list):
                    all_results.extend(result)
                    # Determine search type
                    if "flight" in tool_name:
                        search_type = "flight"
                    elif "hotel" in tool_name:
                        search_type = "hotel"
                    elif "train" in tool_name:
                        search_type = "train"
                    elif "bus" in tool_name:
                        search_type = "bus"
                    elif "attraction" in tool_name or "restaurant" in tool_name or "tip" in tool_name:
                        search_type = "recommendation"
                elif isinstance(result, str):
                    output_parts.append(result)
                    
            except Exception as e:
                log_error("TravelAgent", f"Tool {tool_name} failed: {str(e)}")
                output_parts.append(f"Error searching: {str(e)}")
    
    return all_results, search_type, "\n".join(output_parts)


def _get_tool_by_name(name: str):
    """Get a tool function by its name."""
    for tool in TOOLS:
        if tool.name == name:
            return tool
    return None


def _build_context_summary(context: Dict[str, Any]) -> str:
    """Build a summary of the current context for the LLM."""
    results = context.get("last_search_results", [])
    search_type = context.get("search_context", "unknown")
    
    if not results:
        return "No previous search results."
    
    summary = f"Previous search: {len(results)} {search_type}(s) found:\n"
    for i, item in enumerate(results[:5], 1):
        if search_type == "flight":
            summary += f"{i}. {item.get('airline', '')} {item.get('flight_number', '')} - ₹{item.get('price', 'N/A')}\n"
        elif search_type == "hotel":
            summary += f"{i}. {item.get('name', '')} - ₹{item.get('price_per_night', 'N/A')}/night\n"
        elif search_type == "train":
            summary += f"{i}. {item.get('name', '')} ({item.get('train_number', '')}) - ₹{item.get('price', 'N/A')}\n"
        elif search_type == "bus":
            summary += f"{i}. {item.get('operator', '')} - ₹{item.get('price', 'N/A')}\n"
        else:
            summary += f"{i}. {item}\n"
    
    return summary


def _build_history_summary(history: List) -> str:
    """Build a summary of recent conversation history."""
    if not history:
        return "This is the start of the conversation."
    
    summary = []
    for msg in history[-4:]:  # Last 4 messages
        role = "User" if isinstance(msg, HumanMessage) else "Assistant"
        content = msg.content[:100] + "..." if len(msg.content) > 100 else msg.content
        summary.append(f"{role}: {content}")
    
    return "\n".join(summary)


def _format_results_with_llm(query: str, results: List[Dict], result_type: str, llm) -> str:
    """Use LLM to format search results into a nice response."""
    if not results:
        return "No results found."
    
    # Create a structured representation of results
    results_text = _format_results_as_text(results, result_type)
    
    prompt = f"""Format these {result_type} search results into a helpful, conversational response.

User asked: "{query}"

Results:
{results_text}

Requirements:
- Be conversational and helpful
- Include all key details (prices, times, ratings)
- Use markdown formatting (bold, bullets)
- End with a helpful follow-up question about booking or more options
- Keep it concise but informative"""

    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        return response.content if response.content else results_text
    except:
        return results_text  # Fallback to plain formatting


def _format_results_as_text(results: List[Dict], result_type: str) -> str:
    """Format results into plain text."""
    output = []
    
    for i, item in enumerate(results[:10], 1):
        if result_type == "flight":
            output.append(
                f"{i}. **{item.get('airline', 'Unknown')} {item.get('flight_number', '')}**\n"
                f"   {item.get('origin', '')} → {item.get('destination', '')}\n"
                f"   Date: {item.get('date', '')} | {item.get('departure', '')} - {item.get('arrival', '')}\n"
                f"   Price: ₹{item.get('price', 'N/A')}"
            )
        elif result_type == "hotel":
            amenities = item.get('amenities', [])
            if isinstance(amenities, list):
                amenities = ", ".join(amenities[:3])
            output.append(
                f"{i}. **{item.get('name', 'Unknown')}**\n"
                f"   📍 {item.get('location', '')}\n"
                f"   ⭐ Rating: {item.get('rating', 'N/A')}\n"
                f"   💰 ₹{item.get('price_per_night', 'N/A')}/night\n"
                f"   Amenities: {amenities}"
            )
        elif result_type == "train":
            output.append(
                f"{i}. **{item.get('name', 'Unknown')} ({item.get('train_number', '')})**\n"
                f"   {item.get('origin', '')} → {item.get('destination', '')}\n"
                f"   Date: {item.get('date', '')} | Class: {item.get('class', item.get('train_class', ''))}\n"
                f"   Price: ₹{item.get('price', 'N/A')}"
            )
        elif result_type == "bus":
            output.append(
                f"{i}. **{item.get('operator', 'Unknown')}**\n"
                f"   {item.get('origin', '')} → {item.get('destination', '')}\n"
                f"   Date: {item.get('date', '')} | Type: {item.get('type', item.get('bus_type', ''))}\n"
                f"   Price: ₹{item.get('price', 'N/A')}"
            )
        else:
            output.append(f"{i}. {json.dumps(item)}")
    
    return "\n\n".join(output)


def _extract_text_from_response(content) -> str:
    """Extract text from various LLM response formats."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        text_parts = []
        for block in content:
            if isinstance(block, dict) and "text" in block:
                text_parts.append(block["text"])
            elif isinstance(block, str):
                text_parts.append(block)
        return " ".join(text_parts)
    return str(content)
