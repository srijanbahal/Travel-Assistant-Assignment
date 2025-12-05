from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from agents.llm_engine import get_llm
from agents.a2a_schema import A2AMessage
from validation.input_guards import validate_user_input, validate_message_length

llm = get_llm()

detect_translate_prompt = ChatPromptTemplate.from_template(
    """
    You are a helpful translator. 
    1. Detect the language of the user's input.
    2. Translate it to English.
    3. Return the result in the following format:
    Language: [Detected Language]
    Translation: [English Translation]
    
    If the input is already in English, return:
    Language: English
    Translation: [Original Input]
    
    User Input: {input}
    """
)

translate_response_prompt = ChatPromptTemplate.from_template(
    """
    Translate the following text to {language}.
    Maintain the formatting, prices, and numbers exactly.
    Do not add any extra conversational filler unless it was in the original text.
    
    Text: {text}
    """
)

def translate_to_english(text) -> A2AMessage:
    # Validate message length
    if not validate_message_length(text):
        return A2AMessage(
            sender="TranslationAgent",
            receiver="User",
            message_type="ERROR",
            content="Message is too long. Please keep it under 500 characters.",
            context={"error": "message_too_long"}
        )
    
    # Validate input for toxic language and topic restrictions
    validation_result = validate_user_input(text, check_pii=False)
    
    if not validation_result["valid"]:
        return A2AMessage(
            sender="TranslationAgent",
            receiver="User",
            message_type="ERROR",
            content="Sorry, I can't process this request. Please rephrase your message.",
            context={"error": "validation_failed", "issues": validation_result["issues"]}
        )
    
    # Use the cleaned text from validation
    cleaned_text = validation_result["cleaned_text"]
    chain = detect_translate_prompt | llm | StrOutputParser()
    result = chain.invoke({"input": cleaned_text})
    
    lines = result.strip().split('\n')
    detected_lang = "English"
    translation = text
    
    for line in lines:
        if line.startswith("Language:"):
            detected_lang = line.replace("Language:", "").strip()
        elif line.startswith("Translation:"):
            translation = line.replace("Translation:", "").strip()
            
    return A2AMessage(
        sender="TranslationAgent",
        receiver="Router",
        message_type="TASK",
        content=translation,
        context={"detected_language": detected_lang}
    )

def translate_to_user_lang(text, language) -> A2AMessage:
    if language.lower() == "english":
        translated_text = text
    else:
        chain = translate_response_prompt | llm | StrOutputParser()
        translated_text = chain.invoke({"text": text, "language": language})
        
    return A2AMessage(
        sender="TranslationAgent",
        receiver="User",
        message_type="RESPONSE",
        content=translated_text,
        context={"target_language": language}
    )
