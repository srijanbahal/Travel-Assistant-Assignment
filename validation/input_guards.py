"""
Input Guardrails for Travel Assistant
Validates user inputs before processing
"""
from guardrails import Guard
from guardrails.hub import ToxicLanguage, RestrictToTopic, DetectPII

# Input validation guard
input_guard = Guard().use_many(
    ToxicLanguage(threshold=0.8, validation_method="sentence", on_fail="exception"),
    RestrictToTopic(
        valid_topics=["travel", "flights", "hotels", "trains", "buses", "booking", "tourism", "transportation"],
        invalid_topics=["politics", "religion", "hate speech", "illegal activities"],
        on_fail="fix"
    ),
)

# PII detection guard (optional - can be enabled for compliance)
pii_guard = Guard().use(
    DetectPII(pii_entities=["EMAIL_ADDRESS", "PHONE_NUMBER", "CREDIT_CARD"], on_fail="fix")
)

def validate_user_input(text: str, check_pii: bool = False) -> dict:
    """
    Validate user input against guardrails.
    
    Args:
        text: User input text
        check_pii: Whether to check for PII (privacy mode)
        
    Returns:
        dict with 'valid' (bool), 'cleaned_text' (str), 'issues' (list)
    """
    try:
        # Basic input validation
        result = input_guard.validate(text)
        cleaned_text = result.validated_output if hasattr(result, 'validated_output') else text
        
        # Optional PII check
        if check_pii:
            pii_result = pii_guard.validate(cleaned_text)
            cleaned_text = pii_result.validated_output if hasattr(pii_result, 'validated_output') else cleaned_text
        
        return {
            "valid": True,
            "cleaned_text": cleaned_text,
            "issues": []
        }
    except Exception as e:
        return {
            "valid": False,
            "cleaned_text": text,
            "issues": [str(e)]
        }

# Message length validator
MAX_MESSAGE_LENGTH = 500

def validate_message_length(text: str) -> bool:
    """Ensure message is not too long"""
    return len(text) <= MAX_MESSAGE_LENGTH
