# database.py
import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
from base import Base
from models import (
    User, Reward, Transaction,
    Redemption, Event, UserSession, Configuration, SensitiveInfoFilter
)
# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
# Debug statement
print(f"Base instance in database: {id(Base)}")

# Database Connection
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    logger.error("DATABASE_URL environment variable is not set.")
    raise ValueError("DATABASE_URL environment variable is not set.")

# Strip any leading/trailing whitespace
DATABASE_URL = DATABASE_URL.strip()

# Log the connection string without sensitive information
logger.info(f"Connecting to database at {DATABASE_URL.split('@')[-1]}")

# Create the SQLAlchemy engine with SSL mode
connect_args = {}
if DATABASE_URL.startswith("postgresql"):
    connect_args["sslmode"] = "require"

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args
)

# Create a configured "Session" class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    # Import models lazily inside the function to avoid circular imports
    import models
    try:
        print(f"Base instance in database.py: {id(Base)}")
        Base.metadata.create_all(bind=engine)
        print("✅ Tables created successfully.")
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
