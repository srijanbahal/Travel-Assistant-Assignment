"""
Booking & Confirmation Agent

Handles multi-step booking workflow:
1. Item selection from search results
2. Booking confirmation
3. Passenger details collection
4. Payment processing (simulated)
5. Confirmation generation

Uses structured JSON output for booking decisions.
Receives full memory context including search results.
"""
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import json
import re
import uuid

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from agents.llm_engine import get_llm
from agents.memory import ConversationMemory
from agents.logger import log_llm_call, log_error


@dataclass
class BookingAgentResponse:
    """Response from Booking Agent."""
    response: str  # User-facing response
    booking_state: Dict[str, Any]  # Updated booking state


# System prompt for booking agent
BOOKING_SYSTEM_PROMPT = """You are a booking assistant helping users complete their travel reservations.

{context}

CURRENT BOOKING STATUS:
- Stage: {stage}
- Selected Item: {selected_item}
- User Details: {user_details}

AVAILABLE ACTIONS:
1. SELECT - User is selecting an item to book
2. CONFIRM - User is confirming their selection
3. DETAILS - User is providing personal details (name, email, phone)
4. PAYMENT - User is providing payment info (4 digits)
5. CANCEL - User wants to cancel booking
6. UNCLEAR - Need clarification

RULES:
1. For "cheapest"/"lowest price" - select the item with lowest price
2. For "first one"/"second one" - select by position (1-indexed)
3. For confirmations ("yes", "ok", "proceed") - move to next stage
4. Extract any provided details (name, email, phone, card digits)
5. Be helpful and guide user through the process

Respond with JSON only:
{{
    "action": "select|confirm|details|payment|cancel|unclear",
    "item_index": 1,  // Only for select action, 1-indexed. Use -1 for cheapest, -2 for most expensive
    "extracted_details": {{
        "name": "...",
        "email": "...",
        "phone": "...",
        "card_digits": "..."
    }},
    "response": "Your response to user"
}}"""


def run_booking_agent(message: str, memory: ConversationMemory) -> BookingAgentResponse:
    """
    Handle booking workflow.
    
    Args:
        message: English user message
        memory: Conversation memory with search results and booking state
        
    Returns:
        BookingAgentResponse with response and updated booking state
    """
    # Check if we have search results to book
    if not memory.search_results and not memory.booking_state.get("stage"):
        return BookingAgentResponse(
            response="I don't have any search results to book from. Please search for flights, hotels, or trains first!",
            booking_state={"stage": None}
        )
    
    current_stage = memory.booking_state.get("stage")
    selected_item = memory.booking_state.get("selected_item")
    user_details = memory.booking_state.get("user_details", {})
    
    # Build context
    context = memory.get_context_for_llm()
    
    # Build system prompt with simple string formatting (not LangChain templates)
    system_prompt = f"""You are a booking assistant helping users complete their travel reservations.

{context}

CURRENT BOOKING STATUS:
- Stage: {current_stage or "none"}
- Selected Item: {_format_item(selected_item) if selected_item else "None"}
- User Details: {json.dumps(user_details) if user_details else "None"}

AVAILABLE ACTIONS:
1. SELECT - User is selecting an item to book
2. CONFIRM - User is confirming their selection
3. DETAILS - User is providing personal details (name, email, phone)
4. PAYMENT - User is providing payment info (4 digits)
5. CANCEL - User wants to cancel booking
6. UNCLEAR - Need clarification

RULES:
1. For "cheapest"/"lowest price" - select the item with lowest price
2. For "first one"/"second one" - select by position (1-indexed)
3. For confirmations ("yes", "ok", "proceed", "book it") - move to next stage
4. For rejections ("no", "don't book", "cancel", "stop", "wait") - use action "cancel"
5. Extract any provided details (name, email, phone, card digits)
6. Be helpful and guide user through the process

Respond with JSON only:
{{"action": "select", "item_index": 1, "extracted_details": {{}}, "response": "..."}}
OR
{{"action": "confirm", "response": "..."}}, {{"action": "details", "extracted_details": {{"name": "...", "email": "...", "phone": "..."}}, "response": "..."}}"""
    
    try:
        log_llm_call("booking_agent", message[:50])
        
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
        
        # Process based on action
        action = decision.get("action", "unclear")
        
        if action == "cancel":
            return BookingAgentResponse(
                response="Booking cancelled. Let me know if you'd like to search for something else!",
                booking_state={"stage": None, "selected_item": None, "user_details": {}}
            )
        
        elif action == "select":
            return _handle_selection(decision, memory)
        
        elif action == "confirm":
            return _handle_confirmation(memory)
        
        elif action == "details":
            return _handle_details(decision, memory)
        
        elif action == "payment":
            return _handle_payment(decision, memory)
        
        else:
            # Unclear - ask for clarification
            response = decision.get("response", "I'm not sure what you'd like to do. Could you clarify?")
            return BookingAgentResponse(
                response=response,
                booking_state=memory.booking_state
            )
            
    except Exception as e:
        log_error("BookingAgent", f"Error: {e}")
        return BookingAgentResponse(
            response="I'm having trouble processing your booking. Please try again.",
            booking_state=memory.booking_state
        )


def _parse_json_response(text: str) -> Dict[str, Any]:
    """Parse JSON from LLM response."""
    text = re.sub(r'```json\s*', '', text)
    text = re.sub(r'```\s*', '', text)
    text = text.strip()
    
    try:
        parsed = json.loads(text)
        return parsed
    except json.JSONDecodeError:
        # Try to find JSON within text
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            try:
                parsed = json.loads(match.group())
                return parsed
            except:
                pass
        
        # If we can find a "response" field in the text, extract it
        response_match = re.search(r'"response"\s*:\s*"([^"]+)"', text)
        if response_match:
            return {"action": "unclear", "response": response_match.group(1)}
        
        # Last resort: clean the JSON artifacts and return as response
        clean_text = re.sub(r'\{[^}]*\}', '', text).strip()
        if clean_text:
            return {"action": "unclear", "response": clean_text}
        
        return {"action": "unclear", "response": "I'm not sure what you'd like to do. Could you clarify?"}


def _handle_selection(decision: Dict, memory: ConversationMemory) -> BookingAgentResponse:
    """Handle item selection."""
    results = memory.search_results
    item_index = decision.get("item_index", 1)
    
    selected_item = None
    
    if item_index == -1:  # Cheapest
        try:
            selected_item = min(results, key=lambda x: float(x.get('price', x.get('price_per_night', float('inf')))))
        except:
            selected_item = results[0] if results else None
    elif item_index == -2:  # Most expensive
        try:
            selected_item = max(results, key=lambda x: float(x.get('price', x.get('price_per_night', 0))))
        except:
            selected_item = results[-1] if results else None
    elif 1 <= item_index <= len(results):
        selected_item = results[item_index - 1]
    
    if selected_item:
        item_str = _format_item(selected_item)
        return BookingAgentResponse(
            response=f"You've selected:\n\n{item_str}\n\nWould you like to proceed with this booking? (yes/no)",
            booking_state={
                "stage": "confirm",
                "selected_item": selected_item,
                "user_details": {}
            }
        )
    else:
        return BookingAgentResponse(
            response="I couldn't identify which item you want to book. Please specify (e.g., 'book the first one' or 'book the cheapest').",
            booking_state=memory.booking_state
        )


def _handle_confirmation(memory: ConversationMemory) -> BookingAgentResponse:
    """Handle booking confirmation, move to details collection."""
    selected_item = memory.booking_state.get("selected_item")
    
    if not selected_item:
        return BookingAgentResponse(
            response="No item selected. Please select an item to book first.",
            booking_state={"stage": None}
        )
    
    return BookingAgentResponse(
        response="Great! Let's complete your booking.\n\nPlease provide your details:\n• Full Name\n• Email Address\n• Phone Number\n\n(You can provide all at once or one at a time)",
        booking_state={
            "stage": "details",
            "selected_item": selected_item,
            "user_details": {}
        }
    )


def _handle_details(decision: Dict, memory: ConversationMemory) -> BookingAgentResponse:
    """Handle details collection."""
    extracted = decision.get("extracted_details", {})
    current_details = memory.booking_state.get("user_details", {}).copy()
    
    # Update with extracted details
    if extracted.get("name"):
        current_details["name"] = extracted["name"]
    if extracted.get("email"):
        current_details["email"] = extracted["email"]
    if extracted.get("phone"):
        current_details["phone"] = extracted["phone"]
    
    # Check what's missing
    missing = []
    if not current_details.get("name"):
        missing.append("Full Name")
    if not current_details.get("email"):
        missing.append("Email Address")
    if not current_details.get("phone"):
        missing.append("Phone Number")
    
    if not missing:
        # All details collected - move to payment
        item = memory.booking_state.get("selected_item", {})
        amount = item.get("price", item.get("price_per_night", "N/A"))
        
        return BookingAgentResponse(
            response=f"✓ Details received!\n\n**Passenger:** {current_details['name']}\n**Email:** {current_details['email']}\n**Phone:** {current_details['phone']}\n\n**Total Amount:** ₹{amount}\n\nTo complete payment, please enter the last 4 digits of your card.",
            booking_state={
                "stage": "payment",
                "selected_item": memory.booking_state.get("selected_item"),
                "user_details": current_details
            }
        )
    else:
        # Ask for missing details
        collected = []
        if current_details.get("name"):
            collected.append(f"✓ Name: {current_details['name']}")
        if current_details.get("email"):
            collected.append(f"✓ Email: {current_details['email']}")
        if current_details.get("phone"):
            collected.append(f"✓ Phone: {current_details['phone']}")
        
        collected_str = "\n".join(collected) if collected else ""
        missing_str = ", ".join(missing)
        
        return BookingAgentResponse(
            response=f"{collected_str}\n\nPlease provide: {missing_str}",
            booking_state={
                "stage": "details",
                "selected_item": memory.booking_state.get("selected_item"),
                "user_details": current_details
            }
        )


def _handle_payment(decision: Dict, memory: ConversationMemory) -> BookingAgentResponse:
    """Handle payment and generate confirmation."""
    extracted = decision.get("extracted_details", {})
    card_digits = extracted.get("card_digits", "")
    
    # Also try to extract from raw text
    if not card_digits:
        # The LLM might not have extracted it, check response
        response_text = decision.get("response", "")
        card_match = re.search(r'\b(\d{4})\b', response_text)
        if card_match:
            card_digits = card_match.group(1)
    
    if card_digits and len(card_digits) >= 4:
        card_digits = card_digits[:4]  # Take first 4 digits
        
        # Generate confirmation
        confirmation_id = f"BK{uuid.uuid4().hex[:8].upper()}"
        
        item = memory.booking_state.get("selected_item", {})
        details = memory.booking_state.get("user_details", {})
        
        item_str = _format_item(item)
        
        response = f"""✅ **BOOKING CONFIRMED!**

📋 **Confirmation Number:** {confirmation_id}

🎫 **Booking Details:**
{item_str}

👤 **Passenger:**
• Name: {details.get('name', 'N/A')}
• Email: {details.get('email', 'N/A')}
• Phone: {details.get('phone', 'N/A')}

💳 **Payment:** Card ending in ****{card_digits}

Thank you for booking with us! A confirmation email has been sent."""
        
        return BookingAgentResponse(
            response=response,
            booking_state={
                "stage": "complete",
                "selected_item": item,
                "user_details": details,
                "confirmation_id": confirmation_id,
                "card_last4": card_digits
            }
        )
    else:
        return BookingAgentResponse(
            response="Please enter the last 4 digits of your payment card to complete the booking.",
            booking_state=memory.booking_state
        )


def _format_item(item: Dict) -> str:
    """Format a booking item for display."""
    if not item:
        return "No item selected"
    
    if "flight_number" in item:
        return (
            f"✈️ **{item.get('airline', 'Unknown')} {item.get('flight_number', '')}**\n"
            f"   Route: {item.get('origin', '')} → {item.get('destination', '')}\n"
            f"   Date: {item.get('date', '')}\n"
            f"   Time: {item.get('departure', '')} - {item.get('arrival', '')}\n"
            f"   Price: ₹{item.get('price', 'N/A')}"
        )
    elif "train_number" in item:
        return (
            f"🚆 **{item.get('name', 'Unknown')} ({item.get('train_number', '')})**\n"
            f"   Route: {item.get('origin', '')} → {item.get('destination', '')}\n"
            f"   Date: {item.get('date', '')} | Class: {item.get('class', item.get('train_class', ''))}\n"
            f"   Price: ₹{item.get('price', 'N/A')}"
        )
    elif "operator" in item:
        return (
            f"🚌 **{item.get('operator', 'Unknown')}**\n"
            f"   Route: {item.get('origin', '')} → {item.get('destination', '')}\n"
            f"   Date: {item.get('date', '')} | Type: {item.get('type', item.get('bus_type', ''))}\n"
            f"   Price: ₹{item.get('price', 'N/A')}"
        )
    elif "price_per_night" in item:
        return (
            f"🏨 **{item.get('name', 'Unknown')}**\n"
            f"   Location: {item.get('location', '')}\n"
            f"   Rating: ⭐ {item.get('rating', 'N/A')}\n"
            f"   Price: ₹{item.get('price_per_night', 'N/A')}/night"
        )
    else:
        return str(item)
