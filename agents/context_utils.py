"""
Context Utilities
Helper functions to manage and validate conversation context and search results.
"""
from typing import List, Dict, Any, Optional
import difflib
import re

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
            "error_message": "I don't have any search results in our conversation yet. Please search for flights/hotels first, then I can help you book.",
            "context_type": "none"
        }
    
    return {
        "is_valid": True,
        "error_message": None,
        "context_type": context_type
    }

def resolve_reference(user_input: str, search_results: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Attempt to resolve a user's reference to a specific item in the search results.
    Handles: ordinals, superlatives, names, dates, flight numbers.
    """
    user_input = user_input.lower()
    
    if not search_results:
        return None

    # 1. Ordinal references (first, second, third)
    ordinals = {
        "first": 0, "1st": 0, "one": 0, "1": 0,
        "second": 1, "2nd": 1, "two": 1, "2": 1,
        "third": 2, "3rd": 2, "three": 2, "3": 2,
        "fourth": 3, "4th": 3, "four": 3, "4": 3,
        "fifth": 4, "5th": 4, "five": 4, "5": 4
    }
    for word, index in ordinals.items():
        if word in user_input.split():  # Match whole words
            if index < len(search_results):
                return search_results[index]

    # 2. Superlatives (cheapest, most expensive)
    if "cheapest" in user_input or "lowest" in user_input or "budget" in user_input:
        try:
            return min(search_results, key=lambda x: float(str(x.get('price', x.get('price_per_night', float('inf')))).replace('$','').replace(',','')))
        except:
            pass
    
    if "expensive" in user_input or "premium" in user_input:
        try:
            return max(search_results, key=lambda x: float(str(x.get('price', x.get('price_per_night', 0))).replace('$','').replace(',','')))
        except:
            pass

    # 3. Date matching (e.g., "05-12-25", "December 5", "tomorrow")
    date_patterns = [
        r'(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',  # DD-MM-YY or DD/MM/YYYY
        r'(\d{4}[-/]\d{1,2}[-/]\d{1,2})',      # YYYY-MM-DD
    ]
    for pattern in date_patterns:
        match = re.search(pattern, user_input)
        if match:
            target_date = match.group(1)
            # Normalize to YYYY-MM-DD if needed
            for item in search_results:
                item_date = item.get('date', '')
                if target_date in item_date or item_date in target_date:
                    return item

    # 4. Flight number / Train number matching
    flight_pattern = r'([a-z]{2}[-]?\d{3,4})'  # e.g., AI-267, 6E123
    match = re.search(flight_pattern, user_input)
    if match:
        target = match.group(1).replace('-', '').upper()
        for item in search_results:
            fn = str(item.get('flight_number', item.get('train_number', ''))).replace('-', '').upper()
            if target in fn or fn in target:
                return item

    # 5. Airline/Operator name matching
    name_map = {}
    for item in search_results:
        if 'airline' in item:
            name_map[item['airline'].lower()] = item
        if 'name' in item:
            name_map[item['name'].lower()] = item
        if 'operator' in item:
            name_map[item['operator'].lower()] = item
            
    for name, item in name_map.items():
        if name in user_input:
            return item

    # 6. "Today" / "Tomorrow" matching
    from datetime import datetime, timedelta
    today = datetime.now().strftime("%Y-%m-%d")
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    
    if "today" in user_input:
        for item in search_results:
            if item.get('date') == today:
                return item
    if "tomorrow" in user_input:
        for item in search_results:
            if item.get('date') == tomorrow:
                return item
    
    # 7. "Last" / "Last one" matching
    if "last" in user_input:
        return search_results[-1]

    # 8. Fuzzy matching for Flight Numbers (handle spaces like "AI - 362")
    # Normalize input: remove spaces, uppercase
    clean_input = re.sub(r'\s+', '', user_input).upper()
    for item in search_results:
        fn = str(item.get('flight_number', item.get('train_number', ''))).replace('-', '').replace(' ', '').upper()
        if fn and fn in clean_input:
            return item

    # 9. Fuzzy matching for Names (Airline/Hotel) using difflib
    names = []
    for item in search_results:
        if 'airline' in item: names.append(item['airline'])
        if 'name' in item: names.append(item['name'])
        if 'operator' in item: names.append(item['operator'])
    
    # Check for close matches in the user input
    # Heuristic: split user input into words and check if any word/phrase matches a name
    import difflib
    for name in names:
        # Check if the name (or close to it) appears in the input
        # Simple approach: is 'Air Inda' close to 'Air India'?
        # We can scan substrings of input? Expensive.
        # Let's try matching distinct words/phrases of suitable length.
        # Better: use SequenceMatcher on the whole input vs name? No.
        pass

    # Simple Fuzzy fallback: Check if any part of the input significantly overlaps with a name
    for item in search_results:
        name = item.get('airline', item.get('name', item.get('operator', ''))).lower()
        if not name: continue
        
        # Calculate similarity ratio
        s = difflib.SequenceMatcher(None, name, user_input)
        if s.find_longest_match(0, len(name), 0, len(user_input)).size > len(name) * 0.7:
             return item

    # 10. Default: if user just says "book it", "proceed", etc. - return first result
    proceed_words = ["book it", "proceed", "confirm", "yes", "go ahead", "do it", "book this"]
    for word in proceed_words:
        if word in user_input:
            return search_results[0] if search_results else None

    return None
