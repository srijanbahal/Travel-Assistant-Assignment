"""
Multi-Lingual Travel Assistant - Streamlit UI

Main entry point for the web application.
Handles user input, invokes the LangGraph workflow, and displays results.
"""
import streamlit as st
import os
import sys
import uuid
from typing import Dict, Any, List

# Add root directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from graph.workflow import app_graph
from langchain_core.messages import HumanMessage, AIMessage
from data.init_db import init_db
from data.chat_repo import get_chat_history

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
    
    .stTextInput input {
        border-radius: 25px;
        background: rgba(255,255,255,0.1);
        border: 1px solid rgba(255,255,255,0.2);
    }
    
    .dataframe {
        background: rgba(30, 33, 48, 0.9) !important;
        border-radius: 10px;
    }
    .dataframe th {
        background: rgba(255,107,107,0.2) !important;
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
    
    # Show booking status if active
    if st.session_state.get("booking_stage"):
        st.markdown("### 🎫 Booking Progress")
        stage = st.session_state.booking_stage
        stages = {
            "confirm": "1️⃣ Confirming...", 
            "details": "2️⃣ Collecting Details", 
            "payment": "3️⃣ Processing Payment", 
            "complete": "✅ Complete"
        }
        st.caption(stages.get(stage, stage))
    
    # Show search context
    if st.session_state.get("last_search_results"):
        st.markdown("### 🔍 Last Search")
        st.caption(f"{len(st.session_state.last_search_results)} {st.session_state.get('search_context', 'items')}(s) found")
    
    st.markdown("---")
    if st.button("🗑️ Clear Conversation"):
        # Clear all session state
        for key in list(st.session_state.keys()):
            if key != "session_id":
                del st.session_state[key]
        st.session_state.session_id = str(uuid.uuid4())
        st.rerun()

# Main Title
st.title("🌍 AI Travel Companion")
st.markdown("*Ask me anything in your native language!*")

# Initialize session state
defaults = {
    "messages": [],
    "last_search_results": [],
    "search_context": "unknown",
    "booking_context": {"session_id": st.session_state.session_id},
    "booking_stage": None,
    "user_language": "English"
}
for key, default in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = default

# Load chat history from DB on first load
if not st.session_state.messages:
    try:
        history = get_chat_history(st.session_state.session_id)
        for msg in history:
            role = "user" if msg.sender == "user" else "assistant"
            st.session_state.messages.append({"role": role, "content": msg.message})
    except Exception as e:
        print(f"Error loading history: {e}")


def render_search_results(results: List[Dict], search_type: str):
    """Render search results as a clean table."""
    if not results:
        return
    
    import pandas as pd
    
    st.markdown("### 🔍 Search Results")
    
    if search_type == "flight":
        df_data = []
        for i, flight in enumerate(results, 1):
            df_data.append({
                "#": i,
                "✈️ Airline": flight.get('airline', 'N/A'),
                "Flight": flight.get('flight_number', ''),
                "Route": f"{flight.get('origin', '')} → {flight.get('destination', '')}",
                "Date": flight.get('date', ''),
                "Time": f"{flight.get('departure', '')} - {flight.get('arrival', '')}",
                "💰 Price": f"₹{flight.get('price', 'N/A')}",
            })
        df = pd.DataFrame(df_data)
        
    elif search_type == "hotel":
        df_data = []
        for i, hotel in enumerate(results, 1):
            amenities = hotel.get('amenities', [])
            if isinstance(amenities, list):
                amenities = ", ".join(amenities[:2])
            df_data.append({
                "#": i,
                "🏨 Hotel": hotel.get('name', 'N/A'),
                "📍 Location": hotel.get('location', ''),
                "⭐ Rating": hotel.get('rating', 'N/A'),
                "💰 Price/Night": f"₹{hotel.get('price_per_night', 'N/A')}",
                "Amenities": amenities,
            })
        df = pd.DataFrame(df_data)
        
    elif search_type == "train":
        df_data = []
        for i, train in enumerate(results, 1):
            df_data.append({
                "#": i,
                "🚆 Train": f"{train.get('name', 'N/A')} ({train.get('train_number', '')})",
                "Route": f"{train.get('origin', '')} → {train.get('destination', '')}",
                "Date": train.get('date', ''),
                "Class": train.get('class', train.get('train_class', '')),
                "💰 Price": f"₹{train.get('price', 'N/A')}",
            })
        df = pd.DataFrame(df_data)
        
    elif search_type == "bus":
        df_data = []
        for i, bus in enumerate(results, 1):
            df_data.append({
                "#": i,
                "🚌 Operator": bus.get('operator', 'N/A'),
                "Route": f"{bus.get('origin', '')} → {bus.get('destination', '')}",
                "Date": bus.get('date', ''),
                "Type": bus.get('type', bus.get('bus_type', '')),
                "💰 Price": f"₹{bus.get('price', 'N/A')}",
            })
        df = pd.DataFrame(df_data)
    else:
        return  # Unknown type
    
    st.dataframe(df, use_container_width=True, hide_index=True)
    st.caption("💡 Say 'book the first one' or 'book the cheapest' to book!")


def render_booking_confirmation(booking_context: Dict):
    """Render booking confirmation card."""
    conf_id = booking_context.get("confirmation_id", "N/A")
    item = booking_context.get("selected_item", {})
    details = booking_context.get("user_details", {})
    
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
        <p>📅 {item.get('date', '')} | 💳 Card ****{booking_context.get('card_last4', 'XXXX')}</p>
    </div>
    """, unsafe_allow_html=True)
    
    if st.button("🎉 Book Another Trip"):
        st.session_state.booking_context = {"session_id": st.session_state.session_id}
        st.session_state.booking_stage = None
        st.session_state.last_search_results = []
        st.rerun()


# Display Chat History
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        # Show English translation toggle if available
        if msg.get("role") == "assistant" and "original_english" in msg:
            with st.expander("🌐 Show English Translation"):
                st.markdown(msg["original_english"])

# Check if booking just completed
if st.session_state.booking_stage == "complete" and st.session_state.booking_context.get("confirmation_id"):
    render_booking_confirmation(st.session_state.booking_context)

# Chat Input
if prompt := st.chat_input("Type your message here... (Try: 'Show me flights from Mumbai to Delhi')"):
    # Add user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.spinner("✨ Thinking..."):
        try:
            # Build LangChain message history (last 10 messages)
            history = []
            for m in st.session_state.messages[-10:]:
                if m["role"] == "user":
                    history.append(HumanMessage(content=m["content"]))
                else:
                    history.append(AIMessage(content=m["content"]))
            
            # Prepare graph inputs with FULL context
            inputs = {
                "messages": history,
                "user_language": st.session_state.user_language,
                "booking_context": st.session_state.booking_context,
                "last_search_results": st.session_state.last_search_results,
                "search_context": st.session_state.search_context,
                "booking_stage": st.session_state.booking_stage,
                "a2a_log": [],
                "next_agent": "travel_agent",
            }
            
            # Invoke the graph
            result = app_graph.invoke(inputs)
            
            # Update ALL state from result
            # Only update search results if we got new ones
            new_results = result.get("last_search_results", [])
            if new_results:
                st.session_state.last_search_results = new_results
            
            st.session_state.search_context = result.get("search_context", st.session_state.search_context)
            st.session_state.booking_context = result.get("booking_context", st.session_state.booking_context)
            st.session_state.booking_stage = result.get("booking_stage")
            st.session_state.user_language = result.get("user_language", st.session_state.user_language)
            
            # Get the response
            last_msg = result["messages"][-1]
            response = last_msg.content
            
            # Store message with metadata
            msg_data = {"role": "assistant", "content": response}
            if hasattr(last_msg, 'additional_kwargs') and "original_english" in last_msg.additional_kwargs:
                msg_data["original_english"] = last_msg.additional_kwargs["original_english"]
            
            st.session_state.messages.append(msg_data)
            
            # Display response
            with st.chat_message("assistant"):
                st.markdown(response)
                if "original_english" in msg_data:
                    with st.expander("🌐 Show English Translation"):
                        st.markdown(msg_data["original_english"])
            
            # Auto-display results if this was a search
            if new_results:
                render_search_results(new_results, st.session_state.search_context)
            
            # Check for booking completion
            if st.session_state.booking_stage == "complete":
                render_booking_confirmation(st.session_state.booking_context)
                
        except Exception as e:
            st.error(f"⚠️ An error occurred: {e}")
            import traceback
            st.code(traceback.format_exc())
