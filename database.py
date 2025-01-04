# database.py
import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Define the base class for declarative models
Base = declarative_base()

# Database Connection
DATABASE_URL = os.getenv("DATABASE_URL")  # Removed default to enforce external DB

if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set.")

# Create the SQLAlchemy engine
engine = create_engine(
    DATABASE_URL,
    connect_args={"sslmode": "require"} if DATABASE_URL.startswith("postgresql") else {}
)

# Create a configured "Session" class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Import models explicitly at the module level
from models import User, Reward, Transaction, Redemption, Event, UserSession, Configuration  # Add all models here

def init_db():
    """
    Initialize the database by creating all tables.
    """
    Base.metadata.create_all(bind=engine)
