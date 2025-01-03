from database import SessionLocal
from models import Reward

# Create a database session
db = SessionLocal()

# Fetch all rewards
rewards = db.query(Reward).all()

if rewards:
    print("Available Rewards:")
    for reward in rewards:
        print(f"ID: {reward.id}, Name: {reward.name}, Points: {reward.points_required}, Quantity: {reward.quantity_available}")
else:
    print("No rewards found in the database.")

db.close()
