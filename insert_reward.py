from sqlalchemy.orm import Session
from database import SessionLocal
from models import Event, Reward
from datetime import datetime

# Create a session
db_session = SessionLocal()

# Sample events
sample_events = [
    Event(
        name="Environment Day Lucky Draw",
        description="Win exciting prizes by participating in our lucky draw!",
        date=datetime(2024, 12, 5),
        poster_url="https://i.pinimg.com/originals/c9/da/89/c9da892078dfc34e7c2cb7022cc20522.jpg",
    ),
    Event(
        name="Recycling Workshop",
        description="Learn how to recycle effectively and earn extra points.",
        date=datetime(2024, 12, 10),
        poster_url="https://example.com/path/to/second_poster.jpg",
    ),
]

# Sample rewards
sample_rewards = [
    Reward(
        name="TNG Pin RM5",
        description="Redeem for a RM5 Touch 'n Go pin.",
        points_required=50,
        quantity_available=100,
    ),
    Reward(
        name="TNG Pin RM10",
        description="Redeem for a RM10 Touch 'n Go pin.",
        points_required=100,
        quantity_available=50,
    ),
]

try:
    # Add events if not already present
    for event in sample_events:
        existing_event = db_session.query(Event).filter_by(name=event.name).first()
        if not existing_event:
            db_session.add(event)
            print(f"Added event: {event.name}")
        else:
            print(f"Event already exists: {event.name}")

    # Add rewards if not already present
    for reward in sample_rewards:
        existing_reward = db_session.query(Reward).filter_by(name=reward.name).first()
        if not existing_reward:
            db_session.add(reward)
            print(f"Added reward: {reward.name}")
        else:
            print(f"Reward already exists: {reward.name}")

    db_session.commit()
    print("Sample data inserted successfully!")
except Exception as e:
    db_session.rollback()
    print(f"An error occurred: {e}")
finally:
    db_session.close()
