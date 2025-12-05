from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from agents.llm_engine import get_llm

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

def translate_to_english(text):
    chain = detect_translate_prompt | llm | StrOutputParser()
    result = chain.invoke({"input": text})
    
    # Simple parsing (robustness can be improved)
    lines = result.strip().split('\n')
    detected_lang = "English"
    translation = text
    
    for line in lines:
        if line.startswith("Language:"):
            detected_lang = line.replace("Language:", "").strip()
        elif line.startswith("Translation:"):
            translation = line.replace("Translation:", "").strip()
            
    return detected_lang, translation

def translate_to_user_lang(text, language):
    if language.lower() == "english":
        return text
    chain = translate_response_prompt | llm | StrOutputParser()
    return chain.invoke({"text": text, "language": language})
