# database.py

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Fetch DATABASE_URL from environment variables
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("Environment variable DATABASE_URL is not set.")

# Create the SQLAlchemy engine
engine = create_engine(
    DATABASE_URL,
    # Uncomment and set if using PostgreSQL with SSL
    # connect_args={"sslmode": "require"}
)

# Create a configured "Session" class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for declarative models
Base = declarative_base()

def init_db():
    """Initialize the database by creating all tables."""
    Base.metadata.create_all(bind=engine)
