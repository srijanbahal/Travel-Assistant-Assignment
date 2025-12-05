"""
Context Utilities
Helper functions to manage and validate conversation context and search results.
"""
from typing import List, Dict, Any, Optional
import difflib

def validate_booking_context(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Check if there is valid context (search results) to proceed with a booking.
    
    Returns:
        Dict with 'is_valid' (bool), 'error_message' (str), 'context_type' (str)
    """
    results = state.get("last_search_results", [])
    context_type = state.get("search_context", "unknown")
    
    if not results:
        return {
            "is_valid": False,
            "error_message": "I don't have any search results in our conversation yet. Where would you like to go?",
            "context_type": "none"
        }
    
    return {
        "is_valid": True,
        "error_message": None,
        "context_type": context_type
    }

def resolve_reference(user_input: str, search_results: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Attempt to resolve a user's reference (e.g., "the first one", "the cheapest one") 
    to a specific item in the search results.
    """
    user_input = user_input.lower()
    
    if not search_results:
        return None

    # 1. Ordinal references (first, second, third)
    ordinals = {"first": 0, "1st": 0, "second": 1, "2nd": 1, "third": 2, "3rd": 2}
    for word, index in ordinals.items():
        if word in user_input:
            if index < len(search_results):
                return search_results[index]

    # 2. Superlatives (cheapest, fastest)
    if "cheapest" in user_input:
        # Assuming results have a 'price' field
        try:
            return min(search_results, key=lambda x: float(str(x.get('price', float('inf'))).replace('$','').replace(',','')))
        except:
            pass

    # 3. Direct matching (airline name, hotel name) using fuzzy matching
    # Create a map of "name" -> item
    name_map = {}
    for item in search_results:
        # Flights usually have 'airline', Hotels have 'name'
        if 'airline' in item:
            name_map[item['airline'].lower()] = item
        if 'name' in item:
            name_map[item['name'].lower()] = item
            
    # Check if any name is in user input
    for name, item in name_map.items():
        if name in user_input:
            return item
            
    # Fuzzy match logic could go here if needed

    return None
