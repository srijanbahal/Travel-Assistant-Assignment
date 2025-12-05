import streamlit as st
import os
import sys

# Add root directory to sys.path to allow imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from graph.workflow import app_graph
from langchain_core.messages import HumanMessage, AIMessage
from dotenv import load_dotenv
from data.init_db import init_db

load_dotenv()

# Initialize Database
try:
    init_db()
except Exception as e:
    print(f"Database initialization skipped/failed (might be running without DB): {e}")

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

# Initialize Chat History
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display Chat History
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

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
            inputs = {"messages": history}
            result = app_graph.invoke(inputs)
            
            # Get the last message (Response)
            last_msg = result["messages"][-1]
            response = last_msg.content
            
            # Add assistant message to state
            st.session_state.messages.append({"role": "assistant", "content": response})
            with st.chat_message("assistant"):
                st.markdown(response)
                
        except Exception as e:
            st.error(f"An error occurred: {e}")
