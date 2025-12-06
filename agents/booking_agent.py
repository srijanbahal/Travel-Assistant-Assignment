"""
Booking & Confirmation Agent

Handles multi-step booking workflow:
1. Confirm selection
2. Collect passenger details
3. Process payment (simulated)
4. Generate confirmation

Uses Pydantic for structured intent detection (robust, no JSON parsing issues).
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from enum import Enum
from langchain_core.prompts import ChatPromptTemplate
from agents.llm_engine import get_llm
from agents.a2a_schema import A2AMessage
from agents.logger import log_llm_call, log_error, log_agent_handoff
import uuid
import re


class BookingIntent(str, Enum):
    """Possible user intents during booking flow."""
    CONFIRM = "confirm"
    CANCEL = "cancel"  
    PROVIDE_DETAILS = "provide_details"
    PROVIDE_PAYMENT = "provide_payment"
    SELECT_ITEM = "select_item"
    UNCLEAR = "unclear"


class IntentResult(BaseModel):
    """Structured result from intent classification."""
    intent: BookingIntent = Field(description="The detected user intent")
    item_index: Optional[int] = Field(default=None, description="1-indexed item number if selecting an item")
    name: Optional[str] = Field(default=None, description="Passenger name if provided")
    email: Optional[str] = Field(default=None, description="Email address if provided")
    phone: Optional[str] = Field(default=None, description="Phone number if provided")
    card_digits: Optional[str] = Field(default=None, description="Last 4 card digits if provided")


def detect_intent(user_input: str, context: str, stage: str, has_results: bool) -> IntentResult:
    """
    Use LLM with structured output to detect booking intent.
    
    Args:
        user_input: What the user said
        context: Description of current booking context
        stage: Current booking stage (confirm/details/payment)
        has_results: Whether there are search results available
        
    Returns:
        IntentResult with detected intent and extracted data
    """
    prompt = f"""Analyze the user message and detect their booking intent.

Context: {context}
Current Stage: {stage}
Has Search Results: {has_results}

User said: "{user_input}"

Determine:
1. Intent: Are they confirming, cancelling, providing details, providing payment, or selecting an item?
2. Extract any relevant data (name, email, phone, card digits, item number)

Intent guidelines:
- "yes", "confirm", "proceed", "book it", "ok" → CONFIRM
- "no", "cancel", "stop", "nevermind" → CANCEL
- If they provide name/email/phone → PROVIDE_DETAILS
- If they provide 4 digits → PROVIDE_PAYMENT
- "first one", "second", "cheapest", "book flight 1" → SELECT_ITEM (extract item_index)
- Otherwise → UNCLEAR"""

    try:
        llm = get_llm()
        
        # Try structured output first
        try:
            structured_llm = llm.with_structured_output(IntentResult)
            result = structured_llm.invoke(prompt)
            if result:
                return result
        except Exception as e:
            log_error("BookingAgent", f"Structured output failed: {e}")
        
        # Fallback to keyword matching
        return _fallback_intent_detection(user_input)
        
    except Exception as e:
        log_error("BookingAgent", f"Intent detection error: {e}")
        return _fallback_intent_detection(user_input)


def _fallback_intent_detection(user_input: str) -> IntentResult:
    """Fallback intent detection using regex and keywords."""
    user_lower = user_input.lower().strip()
    
    # Check for confirmation
    confirm_words = ["yes", "confirm", "proceed", "ok", "sure", "book it", "go ahead", "yep", "yeah"]
    if any(word in user_lower for word in confirm_words):
        return IntentResult(intent=BookingIntent.CONFIRM)
    
    # Check for cancellation
    cancel_words = ["no", "cancel", "stop", "nevermind", "forget it", "don't"]
    if any(word in user_lower for word in cancel_words):
        return IntentResult(intent=BookingIntent.CANCEL)
    
    # Check for item selection
    ordinals = {
        "first": 1, "1st": 1, "one": 1, "1": 1,
        "second": 2, "2nd": 2, "two": 2, "2": 2,
        "third": 3, "3rd": 3, "three": 3, "3": 3,
        "fourth": 4, "4th": 4, "four": 4, "4": 4,
        "fifth": 5, "5th": 5, "five": 5, "5": 5
    }
    for word, idx in ordinals.items():
        if word in user_lower.split():
            return IntentResult(intent=BookingIntent.SELECT_ITEM, item_index=idx)
    
    # Check for "cheapest" or "expensive"
    if "cheapest" in user_lower or "lowest" in user_lower:
        return IntentResult(intent=BookingIntent.SELECT_ITEM, item_index=-1)  # -1 means cheapest
    if "expensive" in user_lower or "premium" in user_lower:
        return IntentResult(intent=BookingIntent.SELECT_ITEM, item_index=-2)  # -2 means most expensive
    
    # Check for card digits
    card_match = re.search(r'\b(\d{4})\b', user_input)
    if card_match:
        return IntentResult(intent=BookingIntent.PROVIDE_PAYMENT, card_digits=card_match.group(1))
    
    # Check for details (email, phone, name)
    email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', user_input)
    phone_match = re.search(r'[\+]?[\d\s\-]{10,}', user_input)
    
    if email_match or phone_match:
        result = IntentResult(intent=BookingIntent.PROVIDE_DETAILS)
        if email_match:
            result.email = email_match.group()
        if phone_match:
            result.phone = phone_match.group().strip()
        # Try to extract name (first capitalized words)
        name = _extract_name(user_input)
        if name:
            result.name = name
        return result
    
    return IntentResult(intent=BookingIntent.UNCLEAR)


def _extract_name(text: str) -> Optional[str]:
    """Extract a name from text (first capitalized words)."""
    words = text.split()
    name_parts = []
    for word in words:
        clean = re.sub(r'[^\w]', '', word)
        if clean and clean[0].isupper() and '@' not in word and not word.isdigit():
            name_parts.append(clean)
        elif name_parts:
            break
    if name_parts and len(name_parts) <= 4:
        return ' '.join(name_parts)
    return None


def handle_booking(state: Dict[str, Any], user_input_msg: A2AMessage) -> A2AMessage:
    """
    Main entry point for booking agent.
    
    Args:
        state: Current conversation state with search results and booking context
        user_input_msg: The user's translated message
        
    Returns:
        A2AMessage with response and updated booking context
    """
    user_input = user_input_msg.content
    booking_context = state.get("booking_context", {}).copy()
    current_stage = state.get("booking_stage")
    search_results = state.get("last_search_results", [])
    search_type = state.get("search_context", "unknown")
    
    log_agent_handoff("Router", "BookingAgent", user_input, state)
    
    # Validate: need search results to book
    if not search_results and current_stage is None:
        return A2AMessage(
            sender="BookingAgent",
            receiver="TranslationAgent",
            message_type="ERROR",
            content="I don't have any search results to book from. Please search for flights, hotels, or trains first!",
            context={"updated_booking_context": booking_context, "booking_stage": None}
        )
    
    # Detect intent
    has_results = len(search_results) > 0
    context_str = f"Booking {search_type}. Selected: {booking_context.get('selected_item', 'None')}"
    intent_result = detect_intent(user_input, context_str, current_stage or "none", has_results)
    
    # Handle based on current stage
    if current_stage is None or current_stage == "complete":
        # Starting new booking - user should be selecting an item
        return _handle_selection(intent_result, search_results, search_type, booking_context)
    elif current_stage == "confirm":
        return _handle_confirm_stage(intent_result, booking_context)
    elif current_stage == "details":
        return _handle_details_stage(intent_result, user_input, booking_context)
    elif current_stage == "payment":
        return _handle_payment_stage(intent_result, booking_context)
    else:
        return A2AMessage(
            sender="BookingAgent",
            receiver="TranslationAgent",
            message_type="RESPONSE",
            content="I'm not sure what you'd like to do. Would you like to search for travel options first?",
            context={"updated_booking_context": booking_context, "booking_stage": None}
        )


def _handle_selection(
    intent: IntentResult, 
    results: List[Dict], 
    search_type: str, 
    booking_context: Dict
) -> A2AMessage:
    """Handle item selection from search results."""
    
    if intent.intent == BookingIntent.CANCEL:
        return A2AMessage(
            sender="BookingAgent",
            receiver="TranslationAgent",
            message_type="RESPONSE",
            content="No problem! Let me know if you'd like to search for something else.",
            context={"updated_booking_context": {}, "booking_stage": None}
        )
    
    selected_item = None
    
    if intent.intent == BookingIntent.SELECT_ITEM and intent.item_index:
        idx = intent.item_index
        if idx == -1:  # Cheapest
            try:
                selected_item = min(results, key=lambda x: float(x.get('price', x.get('price_per_night', float('inf')))))
            except:
                selected_item = results[0] if results else None
        elif idx == -2:  # Most expensive
            try:
                selected_item = max(results, key=lambda x: float(x.get('price', x.get('price_per_night', 0))))
            except:
                selected_item = results[-1] if results else None
        elif 1 <= idx <= len(results):
            selected_item = results[idx - 1]
    
    # If no specific selection but user confirmed, take first item
    if not selected_item and intent.intent == BookingIntent.CONFIRM and results:
        selected_item = results[0]
    
    if selected_item:
        booking_context["selected_item"] = selected_item
        booking_context["item_type"] = search_type
        
        item_str = _format_item(selected_item, search_type)
        return A2AMessage(
            sender="BookingAgent",
            receiver="TranslationAgent",
            message_type="RESPONSE",
            content=f"You've selected:\n\n{item_str}\n\nWould you like to proceed with this booking? (yes/no)",
            context={"updated_booking_context": booking_context, "booking_stage": "confirm"}
        )
    else:
        return A2AMessage(
            sender="BookingAgent",
            receiver="TranslationAgent",
            message_type="RESPONSE",
            content="I couldn't identify which item you want to book. Please specify (e.g., 'book the first one' or 'book the cheapest').",
            context={"updated_booking_context": booking_context, "booking_stage": None}
        )


def _handle_confirm_stage(intent: IntentResult, booking_context: Dict) -> A2AMessage:
    """Handle confirmation stage."""
    item = booking_context.get("selected_item", {})
    item_type = booking_context.get("item_type", "item")
    
    if intent.intent == BookingIntent.CONFIRM:
        return A2AMessage(
            sender="BookingAgent",
            receiver="TranslationAgent",
            message_type="RESPONSE",
            content=f"Great! Let's complete your booking.\n\nPlease provide your details:\n• Full Name\n• Email Address\n• Phone Number\n\n(You can provide all at once or one at a time)",
            context={"updated_booking_context": booking_context, "booking_stage": "details"}
        )
    elif intent.intent == BookingIntent.CANCEL:
        return A2AMessage(
            sender="BookingAgent",
            receiver="TranslationAgent",
            message_type="RESPONSE",
            content="Booking cancelled. Let me know if you'd like to search for something else!",
            context={"updated_booking_context": {}, "booking_stage": None}
        )
    else:
        item_str = _format_item(item, item_type)
        return A2AMessage(
            sender="BookingAgent",
            receiver="TranslationAgent",
            message_type="RESPONSE",
            content=f"You've selected:\n\n{item_str}\n\nWould you like to proceed? Please say 'yes' to confirm or 'no' to cancel.",
            context={"updated_booking_context": booking_context, "booking_stage": "confirm"}
        )


def _handle_details_stage(intent: IntentResult, raw_input: str, booking_context: Dict) -> A2AMessage:
    """Handle details collection stage."""
    
    if intent.intent == BookingIntent.CANCEL:
        return A2AMessage(
            sender="BookingAgent",
            receiver="TranslationAgent",
            message_type="RESPONSE",
            content="Booking cancelled.",
            context={"updated_booking_context": {}, "booking_stage": None}
        )
    
    # Update collected details
    details = booking_context.get("user_details", {})
    
    # Extract from intent
    if intent.name:
        details["name"] = intent.name
    if intent.email:
        details["email"] = intent.email
    if intent.phone:
        details["phone"] = intent.phone
    
    # Also try to extract from raw input (backup)
    if "name" not in details:
        name = _extract_name(raw_input)
        if name:
            details["name"] = name
    
    email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', raw_input)
    if email_match and "email" not in details:
        details["email"] = email_match.group()
        
    phone_match = re.search(r'[\+]?[\d\s\-]{10,}', raw_input)
    if phone_match and "phone" not in details:
        details["phone"] = phone_match.group().strip()
    
    booking_context["user_details"] = details
    
    # Check what's still missing
    missing = []
    if "name" not in details:
        missing.append("Full Name")
    if "email" not in details:
        missing.append("Email Address")
    if "phone" not in details:
        missing.append("Phone Number")
    
    if not missing:
        # All details collected - move to payment
        item = booking_context.get("selected_item", {})
        amount = item.get("price", item.get("price_per_night", "N/A"))
        
        return A2AMessage(
            sender="BookingAgent",
            receiver="TranslationAgent",
            message_type="RESPONSE",
            content=f"✓ Details received!\n\n**Passenger:** {details['name']}\n**Email:** {details['email']}\n**Phone:** {details['phone']}\n\n**Total Amount:** ₹{amount}\n\nTo complete payment, please enter the last 4 digits of your card.",
            context={"updated_booking_context": booking_context, "booking_stage": "payment"}
        )
    else:
        collected = []
        if "name" in details:
            collected.append(f"✓ Name: {details['name']}")
        if "email" in details:
            collected.append(f"✓ Email: {details['email']}")
        if "phone" in details:
            collected.append(f"✓ Phone: {details['phone']}")
        
        collected_str = "\n".join(collected) if collected else ""
        missing_str = ", ".join(missing)
        
        return A2AMessage(
            sender="BookingAgent",
            receiver="TranslationAgent",
            message_type="RESPONSE",
            content=f"{collected_str}\n\nPlease provide: {missing_str}",
            context={"updated_booking_context": booking_context, "booking_stage": "details"}
        )


def _handle_payment_stage(intent: IntentResult, booking_context: Dict) -> A2AMessage:
    """Handle payment stage."""
    
    if intent.intent == BookingIntent.CANCEL:
        return A2AMessage(
            sender="BookingAgent",
            receiver="TranslationAgent",
            message_type="RESPONSE",
            content="Payment cancelled. Your booking was not completed.",
            context={"updated_booking_context": {}, "booking_stage": None}
        )
    
    card_digits = intent.card_digits
    
    if card_digits and len(card_digits) == 4:
        # Generate confirmation
        booking_context["card_last4"] = card_digits
        confirmation_id = f"BK{uuid.uuid4().hex[:8].upper()}"
        booking_context["confirmation_id"] = confirmation_id
        
        item = booking_context.get("selected_item", {})
        details = booking_context.get("user_details", {})
        item_type = booking_context.get("item_type", "item")
        
        item_str = _format_item(item, item_type)
        
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

        return A2AMessage(
            sender="BookingAgent",
            receiver="TranslationAgent",
            message_type="RESPONSE",
            content=response,
            context={"updated_booking_context": booking_context, "booking_stage": "complete"}
        )
    else:
        return A2AMessage(
            sender="BookingAgent",
            receiver="TranslationAgent",
            message_type="RESPONSE",
            content="Please enter the last 4 digits of your payment card to complete the booking.",
            context={"updated_booking_context": booking_context, "booking_stage": "payment"}
        )


def _format_item(item: Dict, item_type: str) -> str:
    """Format a booking item for display."""
    if not item:
        return "No item selected"
    
    if item_type == "flight" or "flight_number" in item:
        return (
            f"✈️ **{item.get('airline', 'Unknown')} {item.get('flight_number', '')}**\n"
            f"   Route: {item.get('origin', '')} → {item.get('destination', '')}\n"
            f"   Date: {item.get('date', '')}\n"
            f"   Time: {item.get('departure', '')} - {item.get('arrival', '')}\n"
            f"   Price: ₹{item.get('price', 'N/A')}"
        )
    elif item_type == "train" or "train_number" in item:
        return (
            f"🚆 **{item.get('name', 'Unknown')} ({item.get('train_number', '')})**\n"
            f"   Route: {item.get('origin', '')} → {item.get('destination', '')}\n"
            f"   Date: {item.get('date', '')} | Class: {item.get('class', item.get('train_class', ''))}\n"
            f"   Price: ₹{item.get('price', 'N/A')}"
        )
    elif item_type == "bus" or "operator" in item:
        return (
            f"🚌 **{item.get('operator', 'Unknown')}**\n"
            f"   Route: {item.get('origin', '')} → {item.get('destination', '')}\n"
            f"   Date: {item.get('date', '')} | Type: {item.get('type', item.get('bus_type', ''))}\n"
            f"   Price: ₹{item.get('price', 'N/A')}"
        )
    elif item_type == "hotel" or "price_per_night" in item:
        return (
            f"🏨 **{item.get('name', 'Unknown')}**\n"
            f"   Location: {item.get('location', '')}\n"
            f"   Rating: ⭐ {item.get('rating', 'N/A')}\n"
            f"   Price: ₹{item.get('price_per_night', 'N/A')}/night"
        )
    else:
        return str(item)
