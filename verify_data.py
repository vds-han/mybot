from sqlalchemy.orm import Session
from database import SessionLocal
from models import Event, Reward

# Create a session
db_session = SessionLocal()

# Fetch and print events
events = db_session.query(Event).all()
print("Events:")
for event in events:
    print(f"ID: {event.id}, Name: {event.name}, Date: {event.date}, Description: {event.description}")

# Fetch and print rewards
rewards = db_session.query(Reward).all()
print("\nRewards:")
for reward in rewards:
    print(f"ID: {reward.id}, Name: {reward.name}, Points: {reward.points_required}, Quantity: {reward.quantity_available}")

db_session.close()
