from typing import List, Optional
from langchain_core.tools import tool
from data.database import get_db, Hotel

@tool
def search_hotels(location: str, price_range: Optional[str] = None) -> List[dict]:
    """
    Search for hotels in a specific location.
    """
    db = next(get_db())
    try:
        query = db.query(Hotel).filter(Hotel.location.ilike(f"%{location}%"))
        hotels = query.all()
        
        results = []
        for hotel in hotels:
            results.append({
                "id": hotel.id,
                "name": hotel.name,
                "location": hotel.location,
                "rating": hotel.rating,
                "price_per_night": hotel.price_per_night,
                "amenities": hotel.amenities.split(","),
                "currency": hotel.currency
            })
        return results
    finally:
        db.close()
