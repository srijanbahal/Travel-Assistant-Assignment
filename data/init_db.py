import json
import os
import random
from datetime import datetime, timedelta
from data.database import engine, Base, SessionLocal, Flight, Hotel, Train, Bus

# Config
CITIES = ["Mumbai", "Delhi", "Bangalore", "Chennai", "Kolkata", "Hyderabad", "Pune", "Goa", "Jaipur", "Ahmedabad"]
AIRLINES = ["IndiGo", "Air India", "Vistara", "SpiceJet"]
TRAINS = ["Shatabdi Express", "Rajdhani Express", "Duronto Express", "Garib Rath"]
BUS_OPERATORS = ["Neeta Travels", "VRL Travels", "SRS Travels", "Orange Travels"]
HOTEL_NAMES = ["Radisson Blu", "Taj Hotel", "Marriott", "Hyatt Regency", "The Oberoi", "Ginger Hotel"]

def generate_schedule(days=45):
    """Generate mock data for the next 'days' days."""
    base_date = datetime.now().date()
    data = {"flights": [], "trains": [], "buses": [], "hotels": []}
    
    # Generate Routes (City A -> City B)
    routes = []
    for origin in CITIES:
        for dest in CITIES:
            if origin != dest:
                routes.append((origin, dest))
    
    # Select a subset of active routes to keep DB size manageable
    active_routes = random.sample(routes, 40) 

    current_id = 1
    
    for day_offset in range(days):
        current_date_obj = base_date + timedelta(days=day_offset)
        current_date = current_date_obj.strftime("%Y-%m-%d")
        
        for origin, dest in active_routes:
            # 1. Flights (2-3 per route)
            for _ in range(random.randint(2, 3)):
                dept_hour = random.randint(5, 22)
                duration = random.randint(2, 5)
                dept_time = f"{dept_hour:02d}:{random.randint(0,59):02d}"
                arr_hour = (dept_hour + duration) % 24
                arr_time = f"{arr_hour:02d}:{random.randint(0,59):02d}"
                
                data["flights"].append({
                    "id": f"FL{current_id:04d}",
                    "airline": random.choice(AIRLINES),
                    "flight_number": f"AI-{random.randint(100, 999)}",
                    "origin": origin,
                    "destination": dest,
                    "date": current_date,
                    "departure": dept_time,
                    "arrival": arr_time,
                    "price": random.randint(3000, 15000),
                    "currency": "INR"
                })
                current_id += 1

            # 2. Trains (1-2 per route)
            for _ in range(random.randint(1, 2)):
                dept_hour = random.randint(6, 23)
                dept_time = f"{dept_hour:02d}:00"
                arr_time = f"{(dept_hour + random.randint(4, 12)) % 24:02d}:30"
                
                data["trains"].append({
                    "id": f"TR{current_id:04d}",
                    "name": random.choice(TRAINS),
                    "train_number": f"{random.randint(12000, 12999)}",
                    "origin": origin,
                    "destination": dest,
                    "date": current_date,
                    "departure": dept_time,
                    "arrival": arr_time,
                    "price": random.randint(500, 3000),
                    "train_class": random.choice(["3AC", "2AC", "Sleeper"]),
                    "currency": "INR"
                })
                current_id += 1
                
            # 3. Buses (2-4 per route)
            for _ in range(random.randint(2, 4)):
                dept_hour = random.randint(18, 23)
                dept_time = f"{dept_hour:02d}:30"
                arr_time = f"{(dept_hour + random.randint(6, 10)) % 24:02d}:00"
                
                data["buses"].append({
                    "id": f"BS{current_id:04d}",
                    "operator": random.choice(BUS_OPERATORS),
                    "origin": origin,
                    "destination": dest,
                    "date": current_date,
                    "departure": dept_time,
                    "arrival": arr_time,
                    "price": random.randint(600, 2000),
                    "bus_type": random.choice(["AC Sleeper", "Volvo"]),
                    "currency": "INR"
                })
                current_id += 1

    # 4. Hotels (Static per city, available continuously)
    hotel_id = 1
    for city in CITIES:
        for _ in range(3): # 3 hotels per city
            data["hotels"].append({
                "id": f"HT{hotel_id:03d}",
                "name": f"{random.choice(HOTEL_NAMES)} {city}",
                "location": city,
                "rating": round(random.uniform(3.5, 5.0), 1),
                "price_per_night": random.randint(2000, 15000),
                "amenities": "WiFi,Pool,Spa",
                "currency": "INR"
            })
            hotel_id += 1

    return data

def init_db():
    print("Initializing Database with Dynamic Mock Data...")
    
    # Try to drop tables, ignore if they don't exist
    try:
        Base.metadata.drop_all(bind=engine) # CLEAR OLD DATA
    except Exception as e:
        print(f"Warning during drop_all: {e}")
        
    Base.metadata.create_all(bind=engine)
    
    session = SessionLocal()
    
    mock_data = generate_schedule(days=45) # Generate for next 45 days
    
    # Bulk insert
    print(f"Seeding {len(mock_data['flights'])} flights...")
    for item in mock_data["flights"]:
        session.add(Flight(**item))
        
    print(f"Seeding {len(mock_data['trains'])} trains...")
    for item in mock_data["trains"]:
        session.add(Train(**item))
        
    print(f"Seeding {len(mock_data['buses'])} buses...")
    for item in mock_data["buses"]:
        session.add(Bus(**item))
        
    print(f"Seeding {len(mock_data['hotels'])} hotels...")
    for item in mock_data["hotels"]:
        session.add(Hotel(**item))
        
    session.commit()
    session.close()
    print("Database seeding complete! ✅")

if __name__ == "__main__":
    init_db()
