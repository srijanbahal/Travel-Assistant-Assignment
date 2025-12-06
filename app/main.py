"""
Multi-Lingual Travel Assistant - Streamlit UI

Main entry point for the web application.
Uses centralized memory management for reliable context handling.
"""
import streamlit as st
import os
import sys
import uuid
from typing import Dict, Any, List

# Add root directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import our modules
from agents.memory import get_memory, clear_memory
from agents.translation_agent import translate_input, translate_output
from agents.router import classify_intent
from agents.travel_agent import run_travel_agent
from agents.booking_agent import run_booking_agent
from data.init_db import init_db
from data.chat_repo import save_chat_message

# Initialize Database
try:
    init_db()
except Exception as e:
    print(f"DB Init Error: {e}")

# Page Config
st.set_page_config(
    page_title="Travel Assistant", 
    page_icon="🌍", 
    layout="wide"
)

# Session ID for persistence
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

# Enhanced CSS
st.markdown("""
<style>
    .stApp {
        background: linear-gradient(135deg, #0e1117 0%, #1a1f2e 100%);
        color: #ffffff;
    }
    
    .stChatMessage {
        background-color: rgba(38, 39, 48, 0.8);
        border-radius: 15px;
        padding: 15px;
        margin-bottom: 10px;
        border: 1px solid #41444c;
        backdrop-filter: blur(10px);
    }
    
    .result-card {
        background: linear-gradient(145deg, #1e2130, #252a3d);
        border-radius: 12px;
        padding: 16px;
        margin: 8px 0;
        border: 1px solid #3a3f52;
        transition: transform 0.2s, box-shadow 0.2s;
    }
    .result-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(0,0,0,0.3);
    }
    
    .price-tag {
        background: linear-gradient(135deg, #ff6b6b, #ff4757);
        color: white;
        padding: 8px 16px;
        border-radius: 20px;
        font-weight: bold;
        display: inline-block;
    }
    
    .booking-confirmed {
        background: linear-gradient(135deg, #2ed573, #1abc9c);
        border-radius: 16px;
        padding: 24px;
        text-align: center;
        margin: 16px 0;
    }
    
    h1 {
        background: linear-gradient(135deg, #ff6b6b, #ffa502);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-family: 'Helvetica Neue', sans-serif;
    }
    
    .stButton button {
        background: linear-gradient(135deg, #ff6b6b, #ff4757);
        color: white;
        border-radius: 25px;
        padding: 0.6rem 2rem;
        font-weight: bold;
        border: none;
        transition: all 0.3s;
    }
    .stButton button:hover {
        transform: scale(1.05);
        box-shadow: 0 5px 20px rgba(255,107,107,0.4);
    }
</style>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.title("🧳 Travel Assistant")
    st.markdown("---")
    st.markdown("### ✨ Capabilities")
    st.markdown("- ✈️ Flight Search & Booking")
    st.markdown("- 🏨 Hotel Search")
    st.markdown("- 🚆 Train & Bus Schedules")
    st.markdown("- 🗺️ Local Recommendations")
    st.markdown("- 🗣️ Multi-lingual Support")
    st.markdown("---")
    
    # Get memory for sidebar display
    memory = get_memory(st.session_state.session_id)
    
    # Show booking status if active
    if memory.booking_state.get("stage"):
        st.markdown("### 🎫 Booking Progress")
        stage = memory.booking_state.get("stage")
        stages = {
            "confirm": "1️⃣ Confirming...", 
            "details": "2️⃣ Collecting Details", 
            "payment": "3️⃣ Processing Payment", 
            "complete": "✅ Complete"
        }
        st.caption(stages.get(stage, stage))
    
    # Show search context
    if memory.search_results:
        st.markdown("### 🔍 Last Search")
        st.caption(f"{len(memory.search_results)} {memory.search_type}(s) found")
    
    st.markdown("---")
    if st.button("🗑️ Clear Conversation"):
        clear_memory(st.session_state.session_id)
        st.session_state.session_id = str(uuid.uuid4())
        st.session_state.messages = []
        st.rerun()

# Main Title
st.title("🌍 AI Travel Companion")
st.markdown("*Ask me anything in your native language!*")

# Initialize session state for messages display
if "messages" not in st.session_state:
    st.session_state.messages = []


def render_search_results(results: List[Dict], search_type: str):
    """Render search results as a clean table."""
    if not results:
        return
    
    import pandas as pd
    
    st.markdown("### 🔍 Search Results")
    
    if search_type == "flight":
        df_data = []
        for i, flight in enumerate(results[:5], 1):
            df_data.append({
                "#": i,
                "Airline": flight.get("airline", ""),
                "Flight": flight.get("flight_number", ""),
                "Route": f"{flight.get('origin', '')} → {flight.get('destination', '')}",
                "Time": f"{flight.get('departure', '')} - {flight.get('arrival', '')}",
                "Price": f"₹{flight.get('price', 'N/A')}"
            })
        df = pd.DataFrame(df_data)
    elif search_type == "hotel":
        df_data = []
        for i, hotel in enumerate(results[:5], 1):
            df_data.append({
                "#": i,
                "Hotel": hotel.get("name", ""),
                "Location": hotel.get("location", ""),
                "Rating": f"⭐ {hotel.get('rating', 'N/A')}",
                "Price": f"₹{hotel.get('price_per_night', 'N/A')}/night"
            })
        df = pd.DataFrame(df_data)
    elif search_type == "train":
        df_data = []
        for i, train in enumerate(results[:5], 1):
            df_data.append({
                "#": i,
                "Train": train.get("name", ""),
                "Number": train.get("train_number", ""),
                "Route": f"{train.get('origin', '')} → {train.get('destination', '')}",
                "Time": f"{train.get('departure', '')} - {train.get('arrival', '')}",
                "Price": f"₹{train.get('price', 'N/A')}"
            })
        df = pd.DataFrame(df_data)
    elif search_type == "bus":
        df_data = []
        for i, bus in enumerate(results[:5], 1):
            df_data.append({
                "#": i,
                "Operator": bus.get("operator", ""),
                "Type": bus.get("type", bus.get("bus_type", "")),
                "Route": f"{bus.get('origin', '')} → {bus.get('destination', '')}",
                "Time": bus.get("departure", ""),
                "Price": f"₹{bus.get('price', 'N/A')}"
            })
        df = pd.DataFrame(df_data)
    else:
        return  # Unknown type
    
    st.dataframe(df, use_container_width=True, hide_index=True)
    st.caption("💡 Say 'book the first one' or 'book the cheapest' to book!")


def render_booking_confirmation(booking_state: Dict):
    """Render booking confirmation card."""
    conf_id = booking_state.get("confirmation_id", "N/A")
    item = booking_state.get("selected_item", {})
    details = booking_state.get("user_details", {})
    
    st.markdown(f"""
    <div class="booking-confirmed">
        <h2>✅ Booking Confirmed!</h2>
        <h3>Confirmation: {conf_id}</h3>
        <hr style="border-color: rgba(255,255,255,0.3)">
        <p><strong>Passenger:</strong> {details.get('name', 'N/A')}</p>
        <p><strong>Email:</strong> {details.get('email', 'N/A')}</p>
        <p><strong>Phone:</strong> {details.get('phone', 'N/A')}</p>
        <hr style="border-color: rgba(255,255,255,0.3)">
        <p>✈️ {item.get('airline', item.get('name', 'N/A'))} | {item.get('origin', '')} → {item.get('destination', '')}</p>
        <p>📅 {item.get('date', '')} | 💳 Card ****{booking_state.get('card_last4', 'XXXX')}</p>
    </div>
    """, unsafe_allow_html=True)
    
    if st.button("🎉 Book Another Trip"):
        clear_memory(st.session_state.session_id)
        st.session_state.messages = []
        st.rerun()


def handle_chat(user_message: str) -> Dict[str, Any]:
    """Process a chat message using the new architecture."""
    session_id = st.session_state.session_id
    memory = get_memory(session_id)
    
    # 1. Translate input
    english_text, is_valid = translate_input(user_message, memory)
    
    if not is_valid:
        return {
            "response": english_text,
            "english_response": english_text,
            "search_results": memory.search_results,
            "search_type": memory.search_type,
            "booking_state": memory.booking_state
        }
    
    # 2. Route to appropriate agent
    intent = classify_intent(english_text, memory)
    
    # 3. Execute agent
    if intent == "booking":
        result = run_booking_agent(english_text, memory)
        memory.update_booking_state(result.booking_state)
        response_text = result.response
    else:
        result = run_travel_agent(english_text, memory)
        if result.search_results:
            memory.update_search_results(result.search_results, result.search_type)
        response_text = result.response
    
    # 4. Translate output
    translated_response = translate_output(response_text, memory)
    
    # 5. Update message history
    memory.add_message("user", user_message)
    memory.add_message("assistant", translated_response)
    
    # Save to database
    try:
        save_chat_message(session_id, "user", user_message)
        save_chat_message(session_id, "assistant", translated_response)
    except Exception as e:
        print(f"Failed to save messages: {e}")
    
    return {
        "response": translated_response,
        "english_response": response_text if memory.user_language != "English" else None,
        "search_results": memory.search_results,
        "search_type": memory.search_type,
        "booking_state": memory.booking_state
    }


# Display Chat History
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("role") == "assistant" and msg.get("english_response"):
            with st.expander("🌐 Show English Translation"):
                st.markdown(msg["english_response"])

# Check if booking just completed
memory = get_memory(st.session_state.session_id)
if memory.booking_state.get("stage") == "complete" and memory.booking_state.get("confirmation_id"):
    render_booking_confirmation(memory.booking_state)

# Chat Input
if prompt := st.chat_input("Type your message here... (Try: 'Show me flights from Mumbai to Delhi')"):
    # Add user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.spinner("✨ Thinking..."):
        try:
            result = handle_chat(prompt)
            
            # Store message with metadata
            msg_data = {
                "role": "assistant", 
                "content": result["response"],
                "english_response": result.get("english_response")
            }
            st.session_state.messages.append(msg_data)
            
            # Display response
            with st.chat_message("assistant"):
                st.markdown(result["response"])
                if result.get("english_response"):
                    with st.expander("🌐 Show English Translation"):
                        st.markdown(result["english_response"])
            
            # Auto-display results if this was a search
            if result["search_results"] and result.get("search_type") != memory.search_type:
                render_search_results(result["search_results"], result["search_type"])
            
            # Check for booking completion
            if result["booking_state"].get("stage") == "complete":
                render_booking_confirmation(result["booking_state"])
                
        except Exception as e:
            st.error(f"⚠️ An error occurred: {e}")
            import traceback
            st.code(traceback.format_exc())
