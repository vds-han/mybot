from database import engine
from models import Base

# Recreate the database
Base.metadata.drop_all(bind=engine)  # Drops all existing tables
Base.metadata.create_all(bind=engine)  # Creates tables based on models
print("Database schema recreated successfully!")
