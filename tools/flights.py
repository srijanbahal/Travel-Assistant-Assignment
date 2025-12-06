"""
Flight Search Tools
Supports both PostgreSQL and SQLite.
"""
from typing import List
from langchain_core.tools import tool
from sqlalchemy import func
from data.database import get_db, Flight, is_sqlite
from datetime import datetime, timedelta


def case_insensitive_like(column, value):
    """Database-agnostic case-insensitive LIKE search."""
    # SQLite LIKE is case-insensitive by default for ASCII
    # PostgreSQL needs ilike or lower()
    return func.lower(column).like(func.lower(f"%{value}%"))


@tool
def search_flights(origin: str, destination: str, date: str = "") -> List[dict]:
    """
    Search for flights based on origin, destination, and date.
    
    Args:
        origin: Departure city (e.g., "Mumbai", "Delhi")
        destination: Arrival city (e.g., "Delhi", "Bangalore")
        date: Travel date in YYYY-MM-DD format. Leave empty to search all dates.
        
    Returns:
        List of flights with airline, flight_number, times, and price
    """
    db = next(get_db())
    try:
        query = db.query(Flight).filter(
            case_insensitive_like(Flight.origin, origin),
            case_insensitive_like(Flight.destination, destination)
        )
        
        if date and date.strip():
            query = query.filter(Flight.date == date)
            
        flights = query.limit(10).all()
        
        # Fuzzy Search: if no results and date provided, search +/- 2 days
        if not flights and date and date.strip():
            try:
                target_date = datetime.strptime(date, "%Y-%m-%d")
                start_date = (target_date - timedelta(days=2)).strftime("%Y-%m-%d")
                end_date = (target_date + timedelta(days=2)).strftime("%Y-%m-%d")
                
                flights = db.query(Flight).filter(
                    case_insensitive_like(Flight.origin, origin),
                    case_insensitive_like(Flight.destination, destination),
                    Flight.date.between(start_date, end_date)
                ).limit(10).all()
            except ValueError:
                pass
        
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
                "note": "Alternative date" if date and flight.date != date else "Exact match"
            })
        return results
    finally:
        db.close()


@tool
def search_next_available_flight(origin: str, destination: str, after_date: str = "") -> List[dict]:
    """
    Search for the next available flights from origin to destination.
    Use this when user asks for 'next available', 'upcoming', or 'any flight'.
    
    Args:
        origin: Departure city
        destination: Arrival city  
        after_date: Search for flights after this date (YYYY-MM-DD). Empty = today.
        
    Returns:
        List of next available flights
    """
    db = next(get_db())
    try:
        if not after_date or not after_date.strip():
            after_date = datetime.now().strftime("%Y-%m-%d")
        
        try:
            target = datetime.strptime(after_date, "%Y-%m-%d")
        except ValueError:
            target = datetime.now()
        
        end_date = (target + timedelta(days=14)).strftime("%Y-%m-%d")
        
        flights = db.query(Flight).filter(
            case_insensitive_like(Flight.origin, origin),
            case_insensitive_like(Flight.destination, destination),
            Flight.date >= after_date,
            Flight.date <= end_date
        ).order_by(Flight.date, Flight.departure).limit(5).all()
        
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
                "note": "Next available"
            })
        return results
    finally:
        db.close()
