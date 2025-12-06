"""
Translation & Language Agent

Handles:
- Language detection (automatic, no user selection)
- Translation to English for internal processing
- Translation back to user's language for responses
- Language-specific nuances (dates, currency, measurements)
- Input validation and guardrails

This agent is STATELESS - it doesn't need conversation history.
It reads/writes language info to ConversationMemory.
"""
from typing import Tuple, Optional
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from agents.llm_engine import get_llm
from agents.memory import ConversationMemory
from agents.logger import log_llm_call, log_error
from validation.input_guards import validate_user_input, validate_message_length
import re


# Prompt for detecting language and translating to English
DETECT_AND_TRANSLATE_PROMPT = """You are a language detection and translation expert.

Task: Analyze the input and:
1. Detect the language
2. Translate to English (if not already English)

User Input: {input}

Respond in EXACTLY this format (no extra text):
LANGUAGE: [detected language name - e.g., Hindi, Tamil, Bengali, English, French]
ENGLISH: [English translation, or original if already English]"""


# Prompt for translating response back to user's language
TRANSLATE_TO_USER_PROMPT = """Translate the following text to {language}.

RULES:
1. Preserve ALL numbers exactly (prices, flight numbers, times, ratings)
2. Preserve ALL proper nouns (airline names, hotel names, city names)
3. Preserve formatting (bullet points, line breaks, markdown)
4. Preserve currency symbols (₹, $, €)
5. Use natural, conversational tone
6. If language is English, return text unchanged

Text to translate:
{text}

Translation:"""


def translate_input(text: str, memory: ConversationMemory) -> Tuple[str, bool]:
    """
    Detect language and translate user input to English.
    Updates memory with detected language.
    
    Args:
        text: Raw user input
        memory: Conversation memory to update
        
    Returns:
        Tuple of (english_text, is_valid)
    """
    # Validate input length
    if not validate_message_length(text):
        log_error("TranslationAgent", "Message too long", {"length": len(text)})
        return "Message is too long. Please keep it under 500 characters.", False
    
    # Validate input content
    validation = validate_user_input(text, check_pii=False)
    if not validation["valid"]:
        log_error("TranslationAgent", "Validation failed", {"issues": validation["issues"]})
        return "Sorry, I can't process this request. Please rephrase.", False
    
    cleaned_text = validation["cleaned_text"]
    
    try:
        log_llm_call("translate_input", cleaned_text[:50])
        
        llm = get_llm()
        prompt = ChatPromptTemplate.from_template(DETECT_AND_TRANSLATE_PROMPT)
        chain = prompt | llm | StrOutputParser()
        
        result = chain.invoke({"input": cleaned_text})
        
        # Parse response
        detected_lang, english_text = _parse_detection_result(result, cleaned_text)
        
        # Update memory with language info
        memory.update_language(detected_lang)
        
        return english_text, True
        
    except Exception as e:
        log_error("TranslationAgent", f"Translation failed: {e}")
        # Fallback: assume English
        memory.update_language("English")
        return cleaned_text, True


def translate_output(text: str, memory: ConversationMemory) -> str:
    """
    Translate agent response to user's language.
    
    Args:
        text: English response text
        memory: Conversation memory with language info
        
    Returns:
        Translated response
    """
    if not text or not text.strip():
        return "I apologize, I couldn't generate a response. Please try again."
    
    target_language = memory.user_language
    
    # Skip translation for English
    if target_language.lower() == "english":
        return text
    
    try:
        log_llm_call("translate_output", f"to {target_language}")
        
        llm = get_llm()
        prompt = ChatPromptTemplate.from_template(TRANSLATE_TO_USER_PROMPT)
        chain = prompt | llm | StrOutputParser()
        
        translated = chain.invoke({
            "text": text,
            "language": target_language
        })
        
        # Ensure we got something back
        if not translated or not translated.strip():
            return text  # Fallback to English
            
        return translated.strip()
        
    except Exception as e:
        log_error("TranslationAgent", f"Output translation failed: {e}")
        return text  # Fallback to English


def _parse_detection_result(result: str, original: str) -> Tuple[str, str]:
    """Parse the LLM detection/translation response."""
    lines = result.strip().split('\n')
    detected_lang = "English"
    english_text = original
    
    for line in lines:
        line = line.strip()
        if line.upper().startswith("LANGUAGE:"):
            detected_lang = line.split(":", 1)[1].strip()
        elif line.upper().startswith("ENGLISH:"):
            english_text = line.split(":", 1)[1].strip()
    
    # Validate we got something
    if not english_text or len(english_text) < 2:
        english_text = original
    
    # Clean up language name
    detected_lang = detected_lang.strip().title()
    if detected_lang not in ["Hindi", "Tamil", "Telugu", "Bengali", "Marathi", 
                             "Gujarati", "Kannada", "Malayalam", "Punjabi",
                             "English", "French", "Spanish", "German", "Japanese"]:
        detected_lang = "English"
    
    return detected_lang, english_text
