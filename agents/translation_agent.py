"""
Translation & Language Agent
Handles language detection, translation to English for processing,
and translation back to user's language for responses.
"""
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from agents.llm_engine import get_llm
from agents.a2a_schema import A2AMessage
from agents.logger import log_llm_call, log_error
from validation.input_guards import validate_user_input, validate_message_length
from typing import Tuple
import re

llm = get_llm()

# Prompt for detecting language and translating to English
DETECT_TRANSLATE_PROMPT = ChatPromptTemplate.from_template(
    """You are a language detection and translation expert.

Task: Analyze the user's input and:
1. Detect the language
2. Translate it to English (if not already English)

User Input: {input}

Respond in EXACTLY this format (no extra text):
Language: [detected language name, e.g. Hindi, Tamil, Bengali, Marathi, English, French, Japanese]
Translation: [English translation of the input, or original if already English]
"""
)

# Prompt for translating response back to user's language
TRANSLATE_RESPONSE_PROMPT = ChatPromptTemplate.from_template(
    """Translate the following text to {language}.

CRITICAL RULES:
1. Preserve ALL numbers exactly (prices, flight numbers, times, ratings)
2. Preserve ALL proper nouns (airline names, hotel names, city names)
3. Preserve formatting (bullet points, line breaks)
4. Preserve currency symbols (₹, $, €)
5. Use natural, conversational tone in the target language
6. If language is English, return the text unchanged

Text to translate:
{text}

Translation:"""
)


def translate_to_english(text: str) -> A2AMessage:
    """
    Detect the language of input text and translate to English.
    
    This is the entry point for user messages. It:
    1. Validates the input (length, content)
    2. Detects the source language
    3. Translates to English for processing
    
    Args:
        text: User's raw input in any language
        
    Returns:
        A2AMessage with translated content and detected language in context
    """
    # Validate message length
    if not validate_message_length(text):
        log_error("TranslationAgent", "Message too long", {"length": len(text)})
        return A2AMessage(
            sender="TranslationAgent",
            receiver="User",
            message_type="ERROR",
            content="Message is too long. Please keep it under 500 characters.",
            context={"error": "message_too_long"}
        )
    
    # Validate input for safety
    validation_result = validate_user_input(text, check_pii=False)
    if not validation_result["valid"]:
        log_error("TranslationAgent", "Validation failed", {"issues": validation_result["issues"]})
        return A2AMessage(
            sender="TranslationAgent",
            receiver="User",
            message_type="ERROR",
            content="Sorry, I can't process this request. Please rephrase your message.",
            context={"error": "validation_failed", "issues": validation_result["issues"]}
        )
    
    # Use the cleaned text from validation
    cleaned_text = validation_result["cleaned_text"]
    
    try:
        log_llm_call("translate_to_english", cleaned_text)
        chain = DETECT_TRANSLATE_PROMPT | llm | StrOutputParser()
        result = chain.invoke({"input": cleaned_text})
        
        # Parse the structured response
        detected_lang, translation = _parse_translation_result(result, cleaned_text)
        
        return A2AMessage(
            sender="TranslationAgent",
            receiver="Router",
            message_type="TASK",
            content=translation,
            context={"detected_language": detected_lang, "original_text": cleaned_text}
        )
        
    except Exception as e:
        log_error("TranslationAgent", f"Translation failed: {str(e)}")
        # Fallback: assume English and pass through
        return A2AMessage(
            sender="TranslationAgent",
            receiver="Router",
            message_type="TASK",
            content=cleaned_text,
            context={"detected_language": "English", "error": str(e)}
        )


def translate_to_user_lang(text: str, language: str) -> A2AMessage:
    """
    Translate the AI response back to the user's language.
    
    Args:
        text: English response text to translate
        language: Target language (e.g., "Hindi", "Tamil")
        
    Returns:
        A2AMessage with translated response
    """
    if not text or not text.strip():
        return A2AMessage(
            sender="TranslationAgent",
            receiver="User",
            message_type="RESPONSE",
            content="I apologize, I couldn't generate a response. Please try again.",
            context={"target_language": language, "error": "empty_response"}
        )
    
    # If English, skip translation
    if language.lower() == "english":
        return A2AMessage(
            sender="TranslationAgent",
            receiver="User",
            message_type="RESPONSE",
            content=text,
            context={"target_language": language}
        )
    
    try:
        log_llm_call("translate_to_user", f"{language}: {text[:50]}")
        chain = TRANSLATE_RESPONSE_PROMPT | llm | StrOutputParser()
        translated_text = chain.invoke({"text": text, "language": language})
        
        # Ensure translation is not empty
        if not translated_text or not translated_text.strip():
            translated_text = text  # Fallback to English
            
        return A2AMessage(
            sender="TranslationAgent",
            receiver="User",
            message_type="RESPONSE",
            content=translated_text.strip(),
            context={"target_language": language}
        )
        
    except Exception as e:
        log_error("TranslationAgent", f"Translation to {language} failed: {str(e)}")
        # Fallback: return English response
        return A2AMessage(
            sender="TranslationAgent",
            receiver="User",
            message_type="RESPONSE",
            content=text,
            context={"target_language": "English", "fallback": True, "error": str(e)}
        )


def _parse_translation_result(result: str, original: str) -> Tuple[str, str]:
    """
    Parse the LLM translation response into language and translation.
    
    Args:
        result: Raw LLM output
        original: Original user text (fallback for translation)
        
    Returns:
        Tuple of (detected_language, english_translation)
    """
    lines = result.strip().split('\n')
    detected_lang = "English"
    translation = original
    
    for line in lines:
        line = line.strip()
        if line.lower().startswith("language:"):
            detected_lang = line.split(":", 1)[1].strip()
        elif line.lower().startswith("translation:"):
            translation = line.split(":", 1)[1].strip()
    
    # If translation is empty or too short, use original
    if not translation or len(translation) < 2:
        translation = original
        
    return detected_lang, translation
