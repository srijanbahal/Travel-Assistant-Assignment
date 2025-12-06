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
            Train.origin.ilike(f"%{origin}%"),
            Train.destination.ilike(f"%{destination}%")
        )
        
        if date:
            query = query.filter(Train.date == date)
            
        trains = query.all()

        # Fuzzy Search Logic
        if not trains and date:
            try:
                from datetime import datetime, timedelta
                target_date = datetime.strptime(date, "%Y-%m-%d")
                start_date = (target_date - timedelta(days=2)).strftime("%Y-%m-%d")
                end_date = (target_date + timedelta(days=2)).strftime("%Y-%m-%d")
                
                trains = db.query(Train).filter(
                    Train.origin.ilike(f"%{origin}%"),
                    Train.destination.ilike(f"%{destination}%"),
                    Train.date.between(start_date, end_date)
                ).all()
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
                "note": "Alternative date found" if date and train.date != date else "Exact match"
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
            Bus.origin.ilike(f"%{origin}%"),
            Bus.destination.ilike(f"%{destination}%")
        )
        
        if date:
            query = query.filter(Bus.date == date)
            
        buses = query.all()

        # Fuzzy Search Logic
        if not buses and date:
            try:
                from datetime import datetime, timedelta
                target_date = datetime.strptime(date, "%Y-%m-%d")
                start_date = (target_date - timedelta(days=2)).strftime("%Y-%m-%d")
                end_date = (target_date + timedelta(days=2)).strftime("%Y-%m-%d")
                
                buses = db.query(Bus).filter(
                    Bus.origin.ilike(f"%{origin}%"),
                    Bus.destination.ilike(f"%{destination}%"),
                    Bus.date.between(start_date, end_date)
                ).all()
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
                "note": "Alternative date found" if date and bus.date != date else "Exact match"
            })
        return results
    finally:
        db.close()
