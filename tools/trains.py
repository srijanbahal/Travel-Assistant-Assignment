"""
Train and Bus Search Tools
Supports both PostgreSQL and SQLite.
"""
from typing import List
from langchain_core.tools import tool
from sqlalchemy import func
from data.database import get_db, Train, Bus
from datetime import datetime, timedelta


def case_insensitive_like(column, value):
    """Database-agnostic case-insensitive LIKE search."""
    return func.lower(column).like(func.lower(f"%{value}%"))


@tool
def search_trains(origin: str, destination: str, date: str = "") -> List[dict]:
    """
    Search for trains based on origin and destination.
    
    Args:
        origin: Departure city (e.g., "Chennai", "Mumbai")
        destination: Arrival city (e.g., "Bangalore", "Delhi")
        date: Travel date in YYYY-MM-DD format. Leave empty for all dates.
        
    Returns:
        List of trains with name, number, times, class, and price
    """
    db = next(get_db())
    try:
        query = db.query(Train).filter(
            case_insensitive_like(Train.origin, origin),
            case_insensitive_like(Train.destination, destination)
        )
        
        if date and date.strip():
            query = query.filter(Train.date == date)
            
        trains = query.limit(10).all()

        # Fuzzy Search if no results
        if not trains and date and date.strip():
            try:
                target_date = datetime.strptime(date, "%Y-%m-%d")
                start_date = (target_date - timedelta(days=2)).strftime("%Y-%m-%d")
                end_date = (target_date + timedelta(days=2)).strftime("%Y-%m-%d")
                
                trains = db.query(Train).filter(
                    case_insensitive_like(Train.origin, origin),
                    case_insensitive_like(Train.destination, destination),
                    Train.date.between(start_date, end_date)
                ).limit(10).all()
            except ValueError:
                pass
        
        results = []
        for train in trains:
            results.append({
                "id": train.id,
                "name": train.name,
                "train_number": train.train_number,
                "origin": train.origin,
                "destination": train.destination,
                "date": train.date,
                "departure": train.departure,
                "arrival": train.arrival,
                "price": train.price,
                "class": train.train_class,
                "currency": train.currency,
                "note": "Alternative date" if date and train.date != date else "Exact match"
            })
        return results
    finally:
        db.close()


@tool
def search_buses(origin: str, destination: str, date: str = "") -> List[dict]:
    """
    Search for buses based on origin and destination.
    
    Args:
        origin: Departure city (e.g., "Pune", "Bangalore")
        destination: Arrival city (e.g., "Goa", "Chennai")
        date: Travel date in YYYY-MM-DD format. Leave empty for all dates.
        
    Returns:
        List of buses with operator, type, times, and price
    """
    db = next(get_db())
    try:
        query = db.query(Bus).filter(
            case_insensitive_like(Bus.origin, origin),
            case_insensitive_like(Bus.destination, destination)
        )
        
        if date and date.strip():
            query = query.filter(Bus.date == date)
            
        buses = query.limit(10).all()

        # Fuzzy Search
        if not buses and date and date.strip():
            try:
                target_date = datetime.strptime(date, "%Y-%m-%d")
                start_date = (target_date - timedelta(days=2)).strftime("%Y-%m-%d")
                end_date = (target_date + timedelta(days=2)).strftime("%Y-%m-%d")
                
                buses = db.query(Bus).filter(
                    case_insensitive_like(Bus.origin, origin),
                    case_insensitive_like(Bus.destination, destination),
                    Bus.date.between(start_date, end_date)
                ).limit(10).all()
            except ValueError:
                pass
        
        results = []
        for bus in buses:
            results.append({
                "id": bus.id,
                "operator": bus.operator,
                "origin": bus.origin,
                "destination": bus.destination,
                "date": bus.date,
                "departure": bus.departure,
                "arrival": bus.arrival,
                "price": bus.price,
                "type": bus.bus_type,
                "currency": bus.currency,
                "note": "Alternative date" if date and bus.date != date else "Exact match"
            })
        return results
    finally:
        db.close()
