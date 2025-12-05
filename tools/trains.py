from typing import List, Optional
from langchain_core.tools import tool
from data.database import get_db, Train, Bus

@tool
def search_trains(origin: str, destination: str, date: Optional[str] = None) -> List[dict]:
    """
    Search for trains based on origin and destination.
    """
    db = next(get_db())
    try:
        query = db.query(Train).filter(
            Train.origin.ilike(origin),
            Train.destination.ilike(destination)
        )
        
        if date:
            query = query.filter(Train.date == date)
            
        trains = query.all()
        
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
                "currency": train.currency
            })
        return results
    finally:
        db.close()

@tool
def search_buses(origin: str, destination: str, date: Optional[str] = None) -> List[dict]:
    """
    Search for buses based on origin and destination.
    """
    db = next(get_db())
    try:
        query = db.query(Bus).filter(
            Bus.origin.ilike(origin),
            Bus.destination.ilike(destination)
        )
        
        if date:
            query = query.filter(Bus.date == date)
            
        buses = query.all()
        
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
                "currency": bus.currency
            })
        return results
    finally:
        db.close()
