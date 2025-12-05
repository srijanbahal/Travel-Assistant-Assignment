import json
import os
from data.database import engine, Base, SessionLocal, Flight, Hotel, Train, Bus

def init_db():
    # Create tables
    Base.metadata.create_all(bind=engine)
    
    session = SessionLocal()
    
    # Check if data exists
    if session.query(Flight).first():
        print("Database already seeded.")
        session.close()
        return

    print("Seeding database...")
    
    # Load JSON
    json_path = os.path.join(os.path.dirname(__file__), "mock_db.json")
    with open(json_path, "r") as f:
        data = json.load(f)
        
    # Seed Flights
    for item in data.get("flights", []):
        flight = Flight(
            id=item["id"],
            airline=item["airline"],
            flight_number=item["flight_number"],
            origin=item["origin"],
            destination=item["destination"],
            date=item["date"],
            departure=item["departure"],
            arrival=item["arrival"],
            price=item["price"],
            currency=item["currency"]
        )
        session.add(flight)
        
    # Seed Hotels
    for item in data.get("hotels", []):
        hotel = Hotel(
            id=item["id"],
            name=item["name"],
            location=item["location"],
            rating=item["rating"],
            price_per_night=item["price_per_night"],
            amenities=",".join(item["amenities"]),
            currency=item["currency"]
        )
        session.add(hotel)
        
    # Seed Trains
    for item in data.get("trains", []):
        train = Train(
            id=item["id"],
            name=item["name"],
            train_number=item["train_number"],
            origin=item["origin"],
            destination=item["destination"],
            date=item["date"],
            departure=item["departure"],
            arrival=item["arrival"],
            price=item["price"],
            train_class=item["class"],
            currency=item["currency"]
        )
        session.add(train)

    # Seed Buses
    for item in data.get("buses", []):
        bus = Bus(
            id=item["id"],
            operator=item["operator"],
            origin=item["origin"],
            destination=item["destination"],
            date=item["date"],
            departure=item["departure"],
            arrival=item["arrival"],
            price=item["price"],
            bus_type=item["type"],
            currency=item["currency"]
        )
        session.add(bus)
        
    session.commit()
    session.close()
    print("Database seeded successfully!")

if __name__ == "__main__":
    init_db()
