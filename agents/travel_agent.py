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
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple
import json
import re

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

AVAILABLE TOOLS (only use when needed for NEW searches):
1. search_flights(origin, destination, date) - Search flights. date is optional.
2. search_next_available_flight(origin, destination, after_date) - Find next available flights
3. search_hotels(location) - Search hotels in a city
4. search_trains(origin, destination, date) - Search trains. date is optional.
5. search_buses(origin, destination, date) - Search buses. date is optional.
6. get_attractions(location) - Get tourist attractions
7. get_restaurants(location) - Get restaurant recommendations
8. get_cultural_tips(location) - Get travel tips

CURRENT SEARCH RESULTS (from previous query):
{context_summary}

CRITICAL RULES:
1. If user asks about EXISTING results shown above (e.g., "which has a pool?", "tell me more about the first one"), 
   DO NOT call any tools - just answer from the context above!
2. Only call tools when user wants a NEW search (new destination, different dates, etc.)
3. For dates like "tomorrow" use {tomorrow_date}, "day after tomorrow" use {day_after_date}
4. If user references previous results ("the first one", "cheapest", "which one has X"), use CONTEXT above
5. Be helpful and conversational

RESPONSE FORMAT:
- Use markdown formatting (bold for names, bullets for lists)
- Include all relevant details (prices, times, ratings)
- End with a helpful follow-up question"""


def run_travel_agent(
    input_msg: A2AMessage, 
    chat_history: List, 
    context: Dict[str, Any] = None
) -> A2AMessage:
    """
    Process a travel-related query using LLM with tool calling.
    """
    context = context or {}
    current_date = datetime.now()
    
    # Build context summary
    context_summary = _build_context_summary(context)
    
    # Calculate date references
    tomorrow = (current_date + timedelta(days=1)).strftime("%Y-%m-%d")
    day_after = (current_date + timedelta(days=2)).strftime("%Y-%m-%d")
    
    # Format system prompt
    system_content = SYSTEM_PROMPT.format(
        current_date=current_date.strftime("%Y-%m-%d"),
        context_summary=context_summary,
        tomorrow_date=tomorrow,
        day_after_date=day_after,
    )
    
    user_query = input_msg.content
    existing_results = context.get("last_search_results", [])
    
    # Check if this is a follow-up question about existing results
    if existing_results and _is_followup_question(user_query):
        # Answer directly without calling tools
        return _handle_followup_question(user_query, existing_results, context)
    
    try:
        llm = get_llm()
        
        # Try with tool calling
        try:
            llm_with_tools = llm.bind_tools(TOOLS)
            log_llm_call("travel_agent_with_tools", user_query)
            
            messages = [
                SystemMessage(content=system_content),
                HumanMessage(content=user_query)
            ]
            
            response = llm_with_tools.invoke(messages)
            
            # Process tool calls if any
            if response.tool_calls:
                search_results, search_type, tool_output = _execute_tool_calls(response.tool_calls)
                
                if search_results:
                    formatted_response = _format_results_as_text(search_results, search_type)
                    formatted_response += "\n\nWould you like to book any of these or see more options?"
                else:
                    formatted_response = tool_output or "I couldn't find any results. Would you like to try different dates or locations?"
                
                return A2AMessage(
                    sender="TravelAgent",
                    receiver="TranslationAgent",
                    message_type="RESPONSE",
                    content=formatted_response,
                    context={"search_results": search_results, "search_type": search_type}
                )
            else:
                # No tool calls - LLM responded directly
                response_text = response.content if response.content else "How can I help you with your travel plans?"
                if isinstance(response_text, list):
                    response_text = _extract_text_from_response(response_text)
                
                return A2AMessage(
                    sender="TravelAgent",
                    receiver="TranslationAgent",
                    message_type="RESPONSE",
                    content=str(response_text),
                    context={"search_results": [], "search_type": "unknown"}
                )
                
        except Exception as tool_error:
            log_error("TravelAgent", f"Tool calling failed: {tool_error}")
            # Fall back to non-tool response
            return _handle_without_tools(user_query, context, llm, system_content)
        
    except Exception as e:
        log_error("TravelAgent", f"Error: {str(e)}")
        return A2AMessage(
            sender="TravelAgent",
            receiver="TranslationAgent",
            message_type="RESPONSE",
            content="I apologize, I'm having trouble processing your request. Could you please try again?",
            context={"search_results": [], "search_type": "unknown", "error": str(e)}
        )


def _is_followup_question(query: str) -> bool:
    """Check if this is a follow-up question about existing results."""
    query_lower = query.lower()
    
    followup_patterns = [
        "which one", "which has", "tell me more", "more about",
        "the first", "the second", "the third", "what about",
        "compare", "difference between", "vs", "or the",
        "has a pool", "has wifi", "has breakfast", "near",
        "how much", "how far", "rating", "reviews",
        "amenities", "facilities", "features"
    ]
    
    return any(pattern in query_lower for pattern in followup_patterns)


def _handle_followup_question(query: str, results: List[Dict], context: Dict) -> A2AMessage:
    """Handle follow-up questions about existing search results."""
    search_type = context.get("search_context", "unknown")
    query_lower = query.lower()
    
    # Build response based on the question
    response = ""
    
    # Check for specific attribute questions
    if "pool" in query_lower:
        matches = [r for r in results if "pool" in str(r.get("amenities", "")).lower()]
        if matches:
            response = "Here are the options with a pool:\n\n"
            for i, item in enumerate(matches, 1):
                response += f"**{i}. {item.get('name', 'Unknown')}** - ₹{item.get('price_per_night', item.get('price', 'N/A'))}/night\n"
        else:
            response = "None of the current results show a pool in their amenities. Would you like me to search for hotels with pools specifically?"
    
    elif "wifi" in query_lower:
        matches = [r for r in results if "wifi" in str(r.get("amenities", "")).lower()]
        if matches:
            response = "These options have WiFi:\n\n"
            for i, item in enumerate(matches, 1):
                response += f"**{i}. {item.get('name', 'Unknown')}**\n"
        else:
            response = "WiFi availability isn't shown for these hotels. Most hotels typically do offer WiFi."
    
    elif "cheapest" in query_lower or "lowest" in query_lower:
        try:
            cheapest = min(results, key=lambda x: float(x.get('price', x.get('price_per_night', float('inf')))))
            response = f"The cheapest option is **{cheapest.get('name', cheapest.get('airline', 'Unknown'))}** at ₹{cheapest.get('price', cheapest.get('price_per_night', 'N/A'))}.\n\nWould you like to book it?"
        except:
            response = "I couldn't determine the cheapest option. Here are all the prices:\n\n"
            for r in results:
                response += f"- {r.get('name', r.get('airline', 'Unknown'))}: ₹{r.get('price', r.get('price_per_night', 'N/A'))}\n"
    
    elif any(x in query_lower for x in ["first", "second", "third", "1st", "2nd", "3rd"]):
        # Get specific item
        ordinals = {"first": 0, "1st": 0, "second": 1, "2nd": 1, "third": 2, "3rd": 2}
        idx = 0
        for word, i in ordinals.items():
            if word in query_lower:
                idx = i
                break
        
        if idx < len(results):
            item = results[idx]
            response = f"Here are the details for option {idx + 1}:\n\n"
            response += _format_single_item(item, search_type)
            response += "\n\nWould you like to book this?"
        else:
            response = f"I only have {len(results)} results. Please choose from 1 to {len(results)}."
    
    else:
        # General follow-up - show summary
        response = "Based on the current results:\n\n"
        for i, item in enumerate(results[:5], 1):
            name = item.get('name', item.get('airline', item.get('operator', 'Unknown')))
            price = item.get('price', item.get('price_per_night', 'N/A'))
            response += f"{i}. **{name}** - ₹{price}\n"
        response += "\nWhat would you like to know about these options?"
    
    return A2AMessage(
        sender="TravelAgent",
        receiver="TranslationAgent",
        message_type="RESPONSE",
        content=response,
        context={"search_results": results, "search_type": search_type}
    )


def _handle_without_tools(query: str, context: Dict, llm, system_content: str) -> A2AMessage:
    """Handle query without tool calling (fallback)."""
    try:
        messages = [
            SystemMessage(content=system_content + "\n\nNOTE: Answer based on your knowledge. Do not attempt to use any tools."),
            HumanMessage(content=query)
        ]
        
        response = llm.invoke(messages)
        response_text = response.content if response.content else "I need more details to help you. Where would you like to travel?"
        
        return A2AMessage(
            sender="TravelAgent",
            receiver="TranslationAgent",
            message_type="RESPONSE",
            content=str(response_text),
            context={"search_results": [], "search_type": "unknown"}
        )
    except Exception as e:
        return A2AMessage(
            sender="TravelAgent",
            receiver="TranslationAgent",
            message_type="RESPONSE",
            content="How can I help you with your travel plans today?",
            context={"search_results": [], "search_type": "unknown"}
        )


def _execute_tool_calls(tool_calls: List) -> Tuple[List[Dict], str, str]:
    """Execute tool calls and return results."""
    all_results = []
    search_type = "unknown"
    output_parts = []
    
    for tool_call in tool_calls:
        tool_name = tool_call.get("name", "")
        tool_args = tool_call.get("args", {})
        
        # Clean up args - remove any null/None values
        tool_args = {k: v for k, v in tool_args.items() if v is not None and v != "null"}
        
        tool_func = _get_tool_by_name(tool_name)
        if tool_func:
            try:
                result = tool_func.invoke(tool_args)
                log_tool_call(tool_name, tool_args, len(result) if isinstance(result, list) else 1)
                
                if isinstance(result, list):
                    all_results.extend(result)
                    if "flight" in tool_name:
                        search_type = "flight"
                    elif "hotel" in tool_name:
                        search_type = "hotel"
                    elif "train" in tool_name:
                        search_type = "train"
                    elif "bus" in tool_name:
                        search_type = "bus"
                    else:
                        search_type = "recommendation"
                elif isinstance(result, str):
                    output_parts.append(result)
                    
            except Exception as e:
                log_error("TravelAgent", f"Tool {tool_name} failed: {str(e)}")
                output_parts.append(f"Couldn't complete the search: {str(e)}")
    
    return all_results, search_type, "\n".join(output_parts)


def _get_tool_by_name(name: str):
    """Get a tool function by name."""
    for tool in TOOLS:
        if tool.name == name:
            return tool
    return None


def _build_context_summary(context: Dict[str, Any]) -> str:
    """Build summary of current context."""
    results = context.get("last_search_results", [])
    search_type = context.get("search_context", "unknown")
    
    if not results:
        return "No previous search results."
    
    summary = f"Found {len(results)} {search_type}(s):\n"
    for i, item in enumerate(results[:5], 1):
        if search_type == "flight":
            summary += f"{i}. {item.get('airline', '')} {item.get('flight_number', '')} - ₹{item.get('price', 'N/A')}\n"
        elif search_type == "hotel":
            amenities = item.get('amenities', [])
            if isinstance(amenities, list):
                amenities = ", ".join(amenities[:3])
            summary += f"{i}. {item.get('name', '')} - ₹{item.get('price_per_night', 'N/A')}/night - Amenities: {amenities}\n"
        elif search_type == "train":
            summary += f"{i}. {item.get('name', '')} ({item.get('train_number', '')}) - ₹{item.get('price', 'N/A')}\n"
        elif search_type == "bus":
            summary += f"{i}. {item.get('operator', '')} - ₹{item.get('price', 'N/A')}\n"
        else:
            summary += f"{i}. {item}\n"
    
    return summary


def _format_single_item(item: Dict, item_type: str) -> str:
    """Format a single item with all details."""
    if item_type == "hotel" or "price_per_night" in item:
        amenities = item.get('amenities', [])
        if isinstance(amenities, list):
            amenities = ", ".join(amenities)
        return (
            f"**{item.get('name', 'Unknown')}**\n"
            f"📍 Location: {item.get('location', '')}\n"
            f"⭐ Rating: {item.get('rating', 'N/A')}\n"
            f"💰 Price: ₹{item.get('price_per_night', 'N/A')}/night\n"
            f"🛎️ Amenities: {amenities}"
        )
    elif item_type == "flight" or "flight_number" in item:
        return (
            f"**{item.get('airline', 'Unknown')} {item.get('flight_number', '')}**\n"
            f"✈️ Route: {item.get('origin', '')} → {item.get('destination', '')}\n"
            f"📅 Date: {item.get('date', '')}\n"
            f"🕐 Time: {item.get('departure', '')} - {item.get('arrival', '')}\n"
            f"💰 Price: ₹{item.get('price', 'N/A')}"
        )
    elif item_type == "train" or "train_number" in item:
        return (
            f"**{item.get('name', 'Unknown')} ({item.get('train_number', '')})**\n"
            f"🚆 Route: {item.get('origin', '')} → {item.get('destination', '')}\n"
            f"📅 Date: {item.get('date', '')}\n"
            f"🎫 Class: {item.get('class', item.get('train_class', ''))}\n"
            f"💰 Price: ₹{item.get('price', 'N/A')}"
        )
    else:
        return str(item)


def _format_results_as_text(results: List[Dict], result_type: str) -> str:
    """Format results into text."""
    if not results:
        return "No results found."
    
    output = [f"Found {len(results)} {result_type}(s):\n"]
    
    for i, item in enumerate(results[:10], 1):
        if result_type == "flight":
            output.append(
                f"{i}. **{item.get('airline', 'Unknown')} {item.get('flight_number', '')}**\n"
                f"   {item.get('origin', '')} → {item.get('destination', '')}\n"
                f"   Date: {item.get('date', '')} | {item.get('departure', '')} - {item.get('arrival', '')}\n"
                f"   💰 ₹{item.get('price', 'N/A')}\n"
            )
        elif result_type == "hotel":
            amenities = item.get('amenities', [])
            if isinstance(amenities, list):
                amenities = ", ".join(amenities[:3])
            output.append(
                f"{i}. **{item.get('name', 'Unknown')}**\n"
                f"   📍 {item.get('location', '')} | ⭐ {item.get('rating', 'N/A')}\n"
                f"   💰 ₹{item.get('price_per_night', 'N/A')}/night\n"
                f"   Amenities: {amenities}\n"
            )
        elif result_type == "train":
            output.append(
                f"{i}. **{item.get('name', 'Unknown')} ({item.get('train_number', '')})**\n"
                f"   {item.get('origin', '')} → {item.get('destination', '')}\n"
                f"   Date: {item.get('date', '')} | Class: {item.get('class', item.get('train_class', ''))}\n"
                f"   💰 ₹{item.get('price', 'N/A')}\n"
            )
        elif result_type == "bus":
            output.append(
                f"{i}. **{item.get('operator', 'Unknown')}**\n"
                f"   {item.get('origin', '')} → {item.get('destination', '')}\n"
                f"   Date: {item.get('date', '')} | Type: {item.get('type', item.get('bus_type', ''))}\n"
                f"   💰 ₹{item.get('price', 'N/A')}\n"
            )
        else:
            output.append(f"{i}. {json.dumps(item)}\n")
    
    return "\n".join(output)


def _extract_text_from_response(content) -> str:
    """Extract text from LLM response."""
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
