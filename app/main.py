import streamlit as st
import os
import sys

# Add root directory to sys.path to allow imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from graph.workflow import app_graph
from langchain_core.messages import HumanMessage, AIMessage
from data.init_db import init_db
from data.chat_repo import get_chat_history
import uuid

# Initialize DB
try:
    init_db()
except Exception as e:
    print(f"DB Init Error: {e}")

# Session ID
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

st.set_page_config(page_title="Travel Assistant", page_icon="🌍", layout="wide")

# Custom CSS for Premium Feel
st.markdown("""
<style>
    .stApp {
        background-color: #0e1117;
        color: #ffffff;
    }
    .stChatMessage {
        background-color: #262730;
        border-radius: 15px;
        padding: 15px;
        margin-bottom: 10px;
        border: 1px solid #41444c;
    }
    .stChatMessage[data-testid="stChatMessageUser"] {
        background-color: #2b313e;
    }
    .stChatMessage[data-testid="stChatMessageAssistant"] {
        background-color: #1c1f26;
    }
    h1 {
        color: #ff4b4b;
        font-family: 'Helvetica Neue', sans-serif;
    }
    .stButton button {
        background-color: #ff4b4b;
        color: white;
        border-radius: 20px;
        padding: 0.5rem 2rem;
        font-weight: bold;
    }
    .stTextInput input {
        border-radius: 20px;
    }
</style>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.title("🧳 Travel Assistant")
    st.markdown("---")
    st.markdown("### Capabilities")
    st.markdown("- ✈️ Flight Search")
    st.markdown("- 🏨 Hotel Booking")
    st.markdown("- 🚆 Train Schedules")
    st.markdown("- 🗣️ Multi-lingual Support")
    st.markdown("---")
    if st.button("Clear Conversation"):
        st.session_state.messages = []
        st.rerun()

st.title("🌍 AI Travel Companion")
st.markdown("Ask me anything in your native language!")

# Initialize Context State
if "last_search_results" not in st.session_state:
    st.session_state.last_search_results = []
if "search_context" not in st.session_state:
    st.session_state.search_context = "unknown"

# Initialize Chat History
if "messages" not in st.session_state:
    st.session_state.messages = []
    # Load from DB
    try:
        history = get_chat_history(st.session_state.session_id)
        for msg in history:
            role = "user" if msg.sender == "user" else "assistant"
            st.session_state.messages.append({"role": role, "content": msg.message})
    except Exception as e:
        print(f"Error loading history: {e}")

# Display Chat History
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("role") == "assistant" and "original_english" in msg:
             with st.expander("Show English Translation"):
                st.markdown(msg["original_english"])

# Chat Input
if prompt := st.chat_input("Type your message here..."):
    # Add user message to state
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.spinner("Thinking..."):
        try:
            # Reconstruct LangChain history
            history = []
            for m in st.session_state.messages:
                if m["role"] == "user":
                    history.append(HumanMessage(content=m["content"]))
                else:
                    history.append(AIMessage(content=m["content"]))
            
            # Invoke Graph
            inputs = {
                "messages": history,
                "user_language": "English",
                "booking_context": {"session_id": st.session_state.session_id},
                "last_search_results": st.session_state.last_search_results,
                "search_context": st.session_state.search_context,
                "a2a_log": []
            }
            result = app_graph.invoke(inputs)
            
            # Update Context from Result
            st.session_state.last_search_results = result.get("last_search_results", [])
            st.session_state.search_context = result.get("search_context", "unknown")
            
            # Get the last message (Response)
            last_msg = result["messages"][-1]
            response = last_msg.content
            
            # Add assistant message to state
            # Store metadata if available
            msg_data = {"role": "assistant", "content": response}
            if "original_english" in last_msg.additional_kwargs:
                msg_data["original_english"] = last_msg.additional_kwargs["original_english"]
            
            st.session_state.messages.append(msg_data)
            
            with st.chat_message("assistant"):
                st.markdown(response)
                if "original_english" in msg_data:
                    with st.expander("Show English Translation"):
                        st.markdown(msg_data["original_english"])
                
        except Exception as e:
            st.error(f"An error occurred: {e}")
