"""
Output Guardrails for Travel Assistant
Validates agent outputs for hallucination, toxicity, and consistency
"""
from guardrails import Guard
from guardrails.hub import ToxicLanguage, ValidLength
from typing import Dict, Any

# Output validation guard
output_guard = Guard().use_many(
    ToxicLanguage(threshold=0.9, validation_method="sentence", on_fail="exception"),
    ValidLength(min=10, max=2000, on_fail="reask")
)

def validate_agent_output(text: str, context: Dict[str, Any] = None) -> dict:
    """
    Validate agent output before sending to user.
    
    Args:
        text: Agent response text
        context: Optional context (e.g., search results to check against)
        
    Returns:
        dict with 'valid' (bool), 'cleaned_text' (str), 'issues' (list)
    """
    try:
        result = output_guard.validate(text)
        cleaned_text = result.validated_output if hasattr(result, 'validated_output') else text
        
        issues = []
        
        # Check for hallucinated prices (if context provided)
        if context and 'search_results' in context:
            issues.extend(_check_price_hallucination(cleaned_text, context['search_results']))
        
        # Check for fabricated dates
        if context and 'valid_dates' in context:
            issues.extend(_check_date_consistency(cleaned_text, context['valid_dates']))
        
        return {
            "valid": len(issues) == 0,
            "cleaned_text": cleaned_text,
            "issues": issues
        }
    except Exception as e:
        return {
            "valid": False,
            "cleaned_text": text,
            "issues": [str(e)]
        }

def _check_price_hallucination(text: str, search_results: list) -> list:
    """Check if mentioned prices exist in actual search results"""
    issues = []
    # Extract prices from text (simple regex)
    import re
    mentioned_prices = re.findall(r'[$₹€£¥]\s*[\d,]+(?:\.\d{2})?', text)
    
    if search_results and mentioned_prices:
        actual_prices = [str(r.get('price', '')) for r in search_results]
        for price in mentioned_prices:
            # Simplified check - in production, normalize price formats
            if not any(p in price or price in p for p in actual_prices):
                issues.append(f"Price {price} not found in search results")
    
    return issues

def _check_date_consistency(text: str, valid_dates: list) -> list:
    """Check if mentioned dates are consistent with search parameters"""
    issues = []
    # This is a placeholder - would need proper date extraction
    # For now, just ensure no dates from the past are mentioned
    import re
    from datetime import datetime
    
    date_patterns = re.findall(r'\d{4}-\d{2}-\d{2}', text)
    today = datetime.now().date()
    
    for date_str in date_patterns:
        try:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
            if date_obj < today:
                issues.append(f"Date {date_str} is in the past")
        except ValueError:
            pass
    
    return issues
