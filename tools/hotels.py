"""
Hotel Search Tool
Supports both PostgreSQL and SQLite.
"""
from typing import List
from langchain_core.tools import tool
from sqlalchemy import func
from data.database import get_db, Hotel


def case_insensitive_like(column, value):
    """Database-agnostic case-insensitive LIKE search."""
    return func.lower(column).like(func.lower(f"%{value}%"))


@tool
def search_hotels(location: str) -> List[dict]:
    """
    Search for hotels in a specific location.
    
    Args:
        location: The city or area to search for hotels (e.g., "Guwahati", "Delhi", "Goa")
        
    Returns:
        List of hotels with name, location, rating, price_per_night, amenities
    """
    db = next(get_db())
    try:
        query = db.query(Hotel).filter(case_insensitive_like(Hotel.location, location))
        hotels = query.all()
        
        results = []
        for hotel in hotels:
            amenities = hotel.amenities.split(",") if hotel.amenities else []
            results.append({
                "id": hotel.id,
                "name": hotel.name,
                "location": hotel.location,
                "rating": hotel.rating,
                "price_per_night": hotel.price_per_night,
                "amenities": amenities,
                "currency": hotel.currency
            })
        return results
    finally:
        db.close()
