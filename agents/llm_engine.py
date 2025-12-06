"""
LLM Engine - Handles LLM initialization with Groq or Google

Supports both local (.env) and Streamlit Cloud (secrets.toml) configurations.
"""
import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from dotenv import load_dotenv

load_dotenv()


def get_api_key(key_name: str) -> str:
    """
    Get API key from environment or Streamlit secrets.
    Priority: Environment variable > Streamlit secrets
    """
    # Try environment variable first
    value = os.getenv(key_name)
    if value:
        return value
    
    # Try Streamlit secrets (for cloud deployment)
    try:
        import streamlit as st
        if hasattr(st, 'secrets') and key_name in st.secrets:
            return st.secrets[key_name]
    except Exception:
        pass
    
    return ""


def get_llm(model_type="groq"):
    """
    Get LLM instance. Prioritizes Groq, falls back to Google.
    
    Args:
        model_type: "groq" or "flash"
        
    Returns:
        LangChain chat model instance
    """
    groq_api_key = get_api_key("GROQ_API_KEY")
    google_api_key = get_api_key("GOOGLE_API_KEY")
    
    # Prioritize Groq Llama 70B
    if model_type == "groq" and groq_api_key:
        return ChatGroq(
            api_key=groq_api_key,
            model_name="llama-3.3-70b-versatile", 
            temperature=0,
            max_tokens=2048
        )
    
    # Fallback to Gemini
    if model_type == "flash" and google_api_key:
        try:
            return ChatGoogleGenerativeAI(
                google_api_key=google_api_key,
                model="gemini-2.0-flash", 
                temperature=0
            )
        except Exception as e:
            print(f"Error initializing Gemini: {e}")
    
    # Final fallback
    if groq_api_key:
        return ChatGroq(
            api_key=groq_api_key,
            model_name="llama-3.3-70b-versatile", 
            temperature=0
        )
    if google_api_key:
        return ChatGoogleGenerativeAI(
            google_api_key=google_api_key,
            model="gemini-2.0-flash", 
            temperature=0
        )

    raise ValueError(
        "No API keys found! Set GROQ_API_KEY or GOOGLE_API_KEY in:\n"
        "- .env file (local development)\n"
        "- Streamlit Cloud Secrets (production)"
    )
