"""
Travel Services Agent

Handles travel-related queries using LLM with memory context.
- Flight search and recommendations
- Hotel/accommodation search
- Train/bus ticket information
- Local attraction recommendations
- Weather and travel tips

Uses structured JSON output for tool calling decisions.
"""
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
import json
import re

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from agents.llm_engine import get_llm
from agents.memory import ConversationMemory
from agents.logger import log_llm_call, log_error, log_tool_call

# Import tools
from tools.flights import search_flights, search_next_available_flight
from tools.hotels import search_hotels
from tools.trains import search_trains, search_buses
from tools.recommendations import get_attractions, get_restaurants, get_cultural_tips


@dataclass
class TravelAgentResponse:
    """Response from Travel Agent."""
    response: str  # User-facing response text
    search_results: List[Dict] = None  # New search results if any
    search_type: str = "unknown"  # Type of search performed


# System prompt for travel agent
TRAVEL_SYSTEM_PROMPT = """You are a helpful travel assistant. Today is {current_date}.

{context}

AVAILABLE ACTIONS:
1. SEARCH - Call a search tool to find travel options
2. RESPOND - Answer directly without searching (use for follow-up questions about existing results)

TOOLS AVAILABLE:
- search_flights: Find flights. Params: origin, destination, date (optional, YYYY-MM-DD)
- search_hotels: Find hotels. Params: location
- search_trains: Find trains. Params: origin, destination, date (optional)
- search_buses: Find buses. Params: origin, destination, date (optional)
- get_attractions: Tourist spots. Params: location
- get_restaurants: Food recommendations. Params: location
- get_cultural_tips: Travel tips. Params: location

RULES:
1. If Current Search Results already exist and user asks about them (e.g., "which is cheapest?"), use RESPOND
2. For NEW searches, use SEARCH with appropriate tool
3. For dates: "tomorrow" = {tomorrow}, "day after" = {day_after}
4. Always be helpful and conversational

Respond with JSON (no markdown, no extra text):
{{
    "action": "search" or "respond",
    "tool": "tool_name if action is search",
    "params": {{"origin": "...", "destination": "..."}},
    "response": "your response text"
}}"""


def run_travel_agent(message: str, memory: ConversationMemory) -> TravelAgentResponse:
    """
    Process a travel-related query.
    
    Args:
        message: English user message
        memory: Conversation memory with context
        
    Returns:
        TravelAgentResponse with response and optional search results
    """
    current_date = datetime.now()
    tomorrow = (current_date + timedelta(days=1)).strftime("%Y-%m-%d")
    day_after = (current_date + timedelta(days=2)).strftime("%Y-%m-%d")
    
    # Build context from memory
    context = memory.get_context_for_llm()
    
    # Build system prompt with simple string formatting (not LangChain templates)
    system_prompt = f"""You are a helpful travel assistant. Today is {current_date.strftime("%Y-%m-%d")}.

{context}

AVAILABLE ACTIONS:
1. SEARCH - Call a search tool to find travel options
2. RESPOND - Answer directly without searching (use for follow-up questions about existing results)

TOOLS AVAILABLE:
- search_flights: Find flights. Params: origin, destination, date (optional, YYYY-MM-DD)
- search_hotels: Find hotels. Params: location
- search_trains: Find trains. Params: origin, destination, date (optional)
- search_buses: Find buses. Params: origin, destination, date (optional)
- get_attractions: Tourist spots. Params: location
- get_restaurants: Food recommendations. Params: location
- get_cultural_tips: Travel tips. Params: location

RULES:
1. If Current Search Results already exist and user asks about them (e.g., "which is cheapest?"), use RESPOND
2. For NEW searches, use SEARCH with appropriate tool
3. For dates: "tomorrow" = {tomorrow}, "day after" = {day_after}
4. Always be helpful and conversational

Respond with JSON (no markdown, no extra text):
{{"action": "search", "tool": "search_flights", "params": {{"origin": "Mumbai", "destination": "Delhi"}}, "response": ""}}
OR
{{"action": "respond", "response": "your response text"}}"""
    
    try:
        log_llm_call("travel_agent", message[:50])
        
        llm = get_llm()
        
        # Use direct message format instead of ChatPromptTemplate
        from langchain_core.messages import SystemMessage, HumanMessage
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=message)
        ]
        
        result = llm.invoke(messages)
        result_text = result.content if hasattr(result, 'content') else str(result)
        
        # Parse JSON response
        decision = _parse_json_response(result_text)
        
        if decision.get("action") == "search":
            # Execute tool and format response
            return _execute_search(decision, memory)
        else:
            # Direct response
            response_text = decision.get("response", "How can I help with your travel plans?")
            return TravelAgentResponse(
                response=_clean_response(response_text),
                search_results=None,
                search_type=memory.search_type
            )
            
    except Exception as e:
        log_error("TravelAgent", f"Error: {e}")
        return TravelAgentResponse(
            response="I apologize, I'm having trouble processing your request. Could you please try again?",
            search_results=None,
            search_type="unknown"
        )


def _parse_json_response(text: str) -> Dict[str, Any]:
    """Parse JSON from LLM response, handling common issues."""
    # Remove markdown code blocks if present
    text = re.sub(r'```json\s*', '', text)
    text = re.sub(r'```\s*', '', text)
    text = text.strip()
    
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Try to extract JSON from text
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except:
                pass
        
        # Fallback: return as direct response
        return {"action": "respond", "response": text}


def _execute_search(decision: Dict, memory: ConversationMemory) -> TravelAgentResponse:
    """Execute a search tool and format results."""
    tool_name = decision.get("tool", "")
    params = decision.get("params", {})
    
    log_tool_call("TravelAgent", tool_name, params)
    
    results = []
    search_type = "unknown"
    
    try:
        # Tools are LangChain StructuredTool objects, use .invoke() to call them
        if tool_name == "search_flights":
            results = search_flights.invoke({
                "origin": params.get("origin", ""),
                "destination": params.get("destination", ""),
                "date": params.get("date", "")
            })
            search_type = "flight"
            
        elif tool_name == "search_next_available_flight":
            results = search_next_available_flight.invoke({
                "origin": params.get("origin", ""),
                "destination": params.get("destination", ""),
                "after_date": params.get("after_date", "")
            })
            search_type = "flight"
            
        elif tool_name == "search_hotels":
            results = search_hotels.invoke({"location": params.get("location", "")})
            search_type = "hotel"
            
        elif tool_name == "search_trains":
            results = search_trains.invoke({
                "origin": params.get("origin", ""),
                "destination": params.get("destination", ""),
                "date": params.get("date", "")
            })
            search_type = "train"
            
        elif tool_name == "search_buses":
            results = search_buses.invoke({
                "origin": params.get("origin", ""),
                "destination": params.get("destination", ""),
                "date": params.get("date", "")
            })
            search_type = "bus"
            
        elif tool_name == "get_attractions":
            results = get_attractions.invoke({"location": params.get("location", "")})
            search_type = "recommendation"
            
        elif tool_name == "get_restaurants":
            results = get_restaurants.invoke({"location": params.get("location", "")})
            search_type = "recommendation"
            
        elif tool_name == "get_cultural_tips":
            tips = get_cultural_tips.invoke({"location": params.get("location", "")})
            # Tips are text, not list
            return TravelAgentResponse(
                response=tips if isinstance(tips, str) else str(tips),
                search_results=None,
                search_type="recommendation"
            )
        else:
            return TravelAgentResponse(
                response="I'm not sure how to help with that. Could you please rephrase?",
                search_results=None,
                search_type="unknown"
            )
        
        # Format results for user
        if results:
            response = _format_results(results, search_type)
            response += "\n\nWould you like to book any of these or see more options?"
        else:
            response = "I couldn't find any results. Would you like to try different dates or locations?"
        
        return TravelAgentResponse(
            response=response,
            search_results=results,
            search_type=search_type
        )
        
    except Exception as e:
        log_error("TravelAgent", f"Tool execution failed: {e}")
        return TravelAgentResponse(
            response=f"I had trouble searching. Please try again with different criteria.",
            search_results=None,
            search_type="unknown"
        )


def _format_results(results: List[Dict], search_type: str) -> str:
    """Format search results for user display."""
    if not results:
        return "No results found."
    
    lines = []
    
    if search_type == "flight":
        lines.append(f"Here are the available flights:\n")
        for i, f in enumerate(results[:5], 1):
            lines.append(
                f"**{i}. {f.get('airline', 'Unknown')}** ({f.get('flight_number', '')})\n"
                f"   {f.get('origin', '')} → {f.get('destination', '')} | "
                f"{f.get('departure', '')} - {f.get('arrival', '')} | "
                f"₹{f.get('price', 'N/A')}"
            )
    
    elif search_type == "hotel":
        lines.append(f"Here are the available hotels:\n")
        for i, h in enumerate(results[:5], 1):
            lines.append(
                f"**{i}. {h.get('name', 'Unknown')}** ⭐{h.get('rating', 'N/A')}\n"
                f"   {h.get('location', '')} | ₹{h.get('price_per_night', 'N/A')}/night\n"
                f"   Amenities: {h.get('amenities', 'N/A')}"
            )
    
    elif search_type == "train":
        lines.append(f"Here are the available trains:\n")
        for i, t in enumerate(results[:5], 1):
            lines.append(
                f"**{i}. {t.get('name', 'Unknown')}** ({t.get('train_number', '')})\n"
                f"   {t.get('origin', '')} → {t.get('destination', '')} | "
                f"{t.get('departure', '')} - {t.get('arrival', '')} | "
                f"₹{t.get('price', 'N/A')}"
            )
    
    elif search_type == "bus":
        lines.append(f"Here are the available buses:\n")
        for i, b in enumerate(results[:5], 1):
            lines.append(
                f"**{i}. {b.get('operator', 'Unknown')}** ({b.get('type', b.get('bus_type', ''))})\n"
                f"   {b.get('origin', '')} → {b.get('destination', '')} | "
                f"{b.get('departure', '')} | ₹{b.get('price', 'N/A')}"
            )
    
    else:
        # Generic formatting for recommendations
        for i, item in enumerate(results[:5], 1):
            name = item.get('name', item.get('title', 'Unknown'))
            desc = item.get('description', item.get('cuisine', ''))
            lines.append(f"**{i}. {name}**\n   {desc}")
    
    return "\n\n".join(lines)


def _clean_response(text: str) -> str:
    """Clean up response text."""
    if not text:
        return "How can I help with your travel plans?"
    
    # Remove any JSON artifacts
    text = re.sub(r'\{[^}]*\}', '', text)
    text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
    
    return text.strip() or "How can I help with your travel plans?"
