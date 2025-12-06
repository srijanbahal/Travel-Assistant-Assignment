import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from dotenv import load_dotenv

load_dotenv()

def get_llm(model_type="groq"):
    google_api_key = os.getenv("GOOGLE_API_KEY")
    groq_api_key = os.getenv("GROQ_API_KEY")
    
    # Prioritize Groq Llama 70B for better context handling
    if model_type == "groq" and groq_api_key:
        return ChatGroq(
            model_name="llama-3.3-70b-versatile", 
            temperature=0,  # Deterministic
            max_tokens=2048  # Prevent overly long responses
        )
    
    # Fallback to Gemini Flash if requested
    if model_type == "flash" and google_api_key:
        try:
            return ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0)
        except Exception as e:
            print(f"Error initializing Gemini: {e}")
            pass
    
    # Final fallback
    if groq_api_key:
        return ChatGroq(model_name="llama-3.3-70b-versatile", temperature=0)
    if google_api_key:
         return ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0)

    raise ValueError("No API keys found for Google or Groq. Please set GOOGLE_API_KEY or GROQ_API_KEY in .env")
