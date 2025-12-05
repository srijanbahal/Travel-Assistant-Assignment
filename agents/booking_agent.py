from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from agents.llm_engine import get_llm
from agents.a2a_schema import A2AMessage
from agents.context_utils import validate_booking_context, resolve_reference

llm = get_llm()

booking_prompt = ChatPromptTemplate.from_template(
    """
    You are a booking agent. Your goal is to collect necessary details to confirm a booking.
    
    Current Booking State:
    Item to Book: {item}
    User Details Collected: {details}
    
    User Input: {input}
    
    Instructions:
    1. If the user wants to book something, identify what it is (Flight, Hotel, etc.) if not already known.
    2. Ask for missing details: Name, Email, Phone.
    3. If all details are present, ask for confirmation to proceed with payment.
    4. If user confirms payment, say "Booking Confirmed" and provide a reference number.
    
    Return your response to the user.
    """
)

def handle_booking(state, user_input_msg: A2AMessage) -> A2AMessage:
    user_input = user_input_msg.content
    
    # 1. Validate Context
    ctx_validation = validate_booking_context(state)
    if not ctx_validation['is_valid']:
        return A2AMessage(
            sender="BookingAgent",
            receiver="TranslationAgent", # Send back error
            message_type="ERROR",
            content=ctx_validation['error_message'],
            context={}
        )

    # 2. Try to resolve reference if item not selected
    booking_context = state.get("booking_context", {})
    if "selected_item" not in booking_context:
        resolved_item = resolve_reference(user_input, state.get("last_search_results", []))
        if resolved_item:
            # We found what they want to book!
            # Update the *local* booking context variable (it will be passed back)
            # Note: We need to ensure this update propagates to the global state in the workflow
            booking_context["selected_item"] = resolved_item
            booking_context["item_type"] = ctx_validation['context_type']
    
    # 3. LLM Booking Flow
    chain = booking_prompt | llm | StrOutputParser()
    
    # Prepare prompt inputs
    item_details = booking_context.get("selected_item", "Not selected yet")
    if isinstance(item_details, dict):
        # Format dict nicely
        item_details = ", ".join([f"{k}: {v}" for k,v in item_details.items()])
        
    response = chain.invoke({
        "item": item_details,
        "details": booking_context.get("user_details", "None"),
        "input": user_input
    })
    
    return A2AMessage(
        sender="BookingAgent",
        receiver="TranslationAgent",
        message_type="RESPONSE",
        content=response,
        context={"booking_status": "in_progress", "updated_booking_context": booking_context} 
    )
