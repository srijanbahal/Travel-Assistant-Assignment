"""
Date Parsing and Validation Utilities
Handles relative dates (today, tomorrow, next week) and absolute dates
"""
import dateparser
from datetime import datetime, timedelta
from typing import Optional, Dict

def parse_date(date_string: str, reference_date: Optional[datetime] = None) -> Optional[Dict]:
    """
    Parse natural language date into standardized format.
    
    Args:
        date_string: Natural language date (e.g., "tomorrow", "next Tuesday", "Dec 15")
        reference_date: Reference date for relative parsing (defaults to now)
        
    Returns:
        Dict with 'date' (datetime object), 'formatted' (YYYY-MM-DD string), 'is_valid' (bool)
    """
    if reference_date is None:
        reference_date = datetime.now()
    
    # Use dateparser to handle multiple languages and formats
    parsed_date = dateparser.parse(
        date_string,
        settings={
            'RELATIVE_BASE': reference_date,
            'PREFER_DATES_FROM': 'future',  # Always prefer future dates for travel
            'RETURN_AS_TIMEZONE_AWARE': False
        }
    )
    
    if parsed_date is None:
        return {
            'date': None,
            'formatted': None,
            'is_valid': False,
            'error': f"Could not parse date: {date_string}"
        }
    
    # Validate date is not in the past
    if parsed_date.date() < reference_date.date():
        return {
            'date': parsed_date,
            'formatted': parsed_date.strftime('%Y-%m-%d'),
            'is_valid': False,
            'error': f"Date {parsed_date.strftime('%Y-%m-%d')} is in the past"
        }
    
    return {
        'date': parsed_date,
        'formatted': parsed_date.strftime('%Y-%m-%d'),
        'is_valid': True,
        'error': None
    }

def extract_dates_from_text(text: str) -> list:
    """
    Extract all date references from text.
    
    Returns:
        List of parsed date dictionaries
    """
    # Common date keywords in multiple languages
    date_keywords = [
        'today', 'tomorrow', 'yesterday',
        'next week', 'next month', 'this week',
        'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday',
        # Spanish
        'hoy', 'mañana', 'próxima semana',
        # French
        'aujourd\'hui', 'demain', 'semaine prochaine',
        # Japanese (transliterated)
        'kyou', 'ashita', 'raishuu'
    ]
    
    dates = []
    text_lower = text.lower()
    
    for keyword in date_keywords:
        if keyword in text_lower:
            parsed = parse_date(keyword)
            if parsed['is_valid']:
                dates.append(parsed)
    
    return dates

def get_date_range(start_date_str: str, duration_days: int = 7) -> Dict:
    """
    Get a date range for flexible searches.
    
    Args:
        start_date_str: Starting date
        duration_days: Number of days in range
        
    Returns:
        Dict with 'start', 'end' formatted dates
    """
    start = parse_date(start_date_str)
    
    if not start['is_valid']:
        return {'start': None, 'end': None, 'error': start['error']}
    
    end_date = start['date'] + timedelta(days=duration_days)
    
    return {
        'start': start['formatted'],
        'end': end_date.strftime('%Y-%m-%d'),
        'error': None
    }
