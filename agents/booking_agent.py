from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from agents.llm_engine import get_llm
from agents.a2a_schema import A2AMessage

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
    
    chain = booking_prompt | llm | StrOutputParser()
    response = chain.invoke({
        "item": state.get("booking_item", "Unknown"),
        "details": state.get("user_details", "None"),
        "input": user_input
    })
    
    return A2AMessage(
        sender="BookingAgent",
        receiver="TranslationAgent",
        message_type="RESPONSE",
        content=response,
        context={"booking_status": "in_progress"} # Simplified context update
    )
