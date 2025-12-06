"""
Database Configuration

Automatically uses SQLite for cloud deployment (Streamlit Cloud)
or PostgreSQL for local development with Docker.

Set USE_SQLITE=true to force SQLite mode.
"""
import os
from sqlalchemy import create_engine, Column, Integer, String, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Determine database URL
# Priority:
# 1. USE_SQLITE=true forces SQLite mode
# 2. DATABASE_URL env var (for PostgreSQL on production/Docker)
# 3. Fall back to SQLite (for Streamlit Cloud or local testing)

USE_SQLITE = os.getenv("USE_SQLITE", "false").lower() == "true"

if USE_SQLITE:
    # Force SQLite mode
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DB_PATH = os.path.join(BASE_DIR, "travel.db")
    DATABASE_URL = f"sqlite:///{DB_PATH}"
    print(f"📦 Using SQLite: {DB_PATH}")
elif os.getenv("DATABASE_URL"):
    DATABASE_URL = os.getenv("DATABASE_URL")
    print(f"🐘 Using PostgreSQL")
else:
    # Default to SQLite for Streamlit Cloud
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DB_PATH = os.path.join(BASE_DIR, "travel.db")
    DATABASE_URL = f"sqlite:///{DB_PATH}"
    print(f"📦 Using SQLite (default): {DB_PATH}")

# Create engine with appropriate settings
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
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
    date = Column(String)
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
    amenities = Column(String)
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
    train_class = Column(String)
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
    bus_type = Column(String)
    currency = Column(String)


class ChatHistory(Base):
    __tablename__ = "chat_history"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    session_id = Column(String, index=True)
    sender = Column(String)
    message = Column(String)
    timestamp = Column(String)


def get_db():
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def is_sqlite():
    """Check if using SQLite database."""
    return DATABASE_URL.startswith("sqlite")
