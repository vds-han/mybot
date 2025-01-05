# database.py
import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define the base class for declarative models
Base = declarative_base()

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

# Import models explicitly at the module level
from models import User, Reward, Transaction, Redemption, Event, UserSession, Configuration,TNGPin  # Ensure all models are imported

def init_db():
    """
    Initialize the database by creating all tables.
    """
    try:
        logger.info("Initializing database...")
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Tables created successfully.")
    except Exception as e:
        logger.error(f"❌ Error creating tables: {e}")
        raise e
