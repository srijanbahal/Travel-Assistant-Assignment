from typing import List, Optional
from langchain_core.tools import tool
from data.database import get_db, Flight

@tool
def search_flights(origin: str, destination: str, date: Optional[str] = None) -> List[dict]:
    """
    Search for flights based on origin, destination, and optional date.
    Returns a list of available flights.
    """
    db = next(get_db())
    try:
        query = db.query(Flight).filter(
            Flight.origin.ilike(origin),
            Flight.destination.ilike(destination)
        )
        
        if date:
            query = query.filter(Flight.date == date)
            
        flights = query.all()
        
        # Fuzzy Search Logic: if no results and date provided, search +/- 2 days
        if not flights and date:
            try:
                from datetime import datetime, timedelta
                target_date = datetime.strptime(date, "%Y-%m-%d")
                start_date = (target_date - timedelta(days=2)).strftime("%Y-%m-%d")
                end_date = (target_date + timedelta(days=2)).strftime("%Y-%m-%d")
                
                # New query for range
                flights = db.query(Flight).filter(
                    Flight.origin.ilike(origin),
                    Flight.destination.ilike(destination),
                    Flight.date.between(start_date, end_date)
                ).all()
            except ValueError:
                pass # Invalid date format, just return empty
        
        results = []
        for flight in flights:
            results.append({
                "id": flight.id,
                "airline": flight.airline,
                "flight_number": flight.flight_number,
                "origin": flight.origin,
                "destination": flight.destination,
                "date": flight.date,
                "departure": flight.departure,
                "arrival": flight.arrival,
                "price": flight.price,
                "currency": flight.currency,
                "note": "Alternative date found" if date and flight.date != date else "Exact match"
            })
        return results
    finally:
        db.close()
