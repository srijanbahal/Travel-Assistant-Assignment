import os
from sqlalchemy import create_engine, Column, Integer, String, Float, Date
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Use environment variable or default to localhost for local testing outside Docker
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/travel_db")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Flight(Base):
    __tablename__ = "flights"
    id = Column(String, primary_key=True, index=True)
    airline = Column(String)
    flight_number = Column(String)
    origin = Column(String, index=True)
    destination = Column(String, index=True)
    date = Column(String) # Keeping as string for simplicity in MVP
    departure = Column(String)
    arrival = Column(String)
    price = Column(Float)
    currency = Column(String)

class Hotel(Base):
    __tablename__ = "hotels"
    id = Column(String, primary_key=True, index=True)
    name = Column(String)
    location = Column(String, index=True)
    rating = Column(Float)
    price_per_night = Column(Float)
    amenities = Column(String) # Stored as comma-separated string
    currency = Column(String)

class Train(Base):
    __tablename__ = "trains"
    id = Column(String, primary_key=True, index=True)
    name = Column(String)
    train_number = Column(String)
    origin = Column(String, index=True)
    destination = Column(String, index=True)
    date = Column(String)
    departure = Column(String)
    arrival = Column(String)
    price = Column(Float)
    train_class = Column(String) # 'class' is reserved keyword
    currency = Column(String)

class Bus(Base):
    __tablename__ = "buses"
    id = Column(String, primary_key=True, index=True)
    operator = Column(String)
    origin = Column(String, index=True)
    destination = Column(String, index=True)
    date = Column(String)
    departure = Column(String)
    arrival = Column(String)
    price = Column(Float)
    bus_type = Column(String) # 'type' is reserved
    currency = Column(String)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
