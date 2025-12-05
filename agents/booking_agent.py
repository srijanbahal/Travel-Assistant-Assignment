from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from agents.llm_engine import get_llm

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

def handle_booking(state, user_input):
    # This is a simplified handler. In a real graph, we'd manage state more explicitly.
    # For now, we'll let the LLM generate the next question or confirmation.
    chain = booking_prompt | llm | StrOutputParser()
    response = chain.invoke({
        "item": state.get("booking_item", "Unknown"),
        "details": state.get("user_details", "None"),
        "input": user_input
    })
    return response
