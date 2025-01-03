# insert_events.py
from database import SessionLocal
from models import Event
from datetime import datetime

# Create a session
db_session = SessionLocal()

# Sample events with poster URLs
sample_events = [
    Event(
        name="Environment Day Lucky Draw",
        description="Win exciting prizes by participating in our lucky draw!",
        date=datetime(2025, 2, 5),
        poster_url="https://i.pinimg.com/originals/c9/da/89/c9da892078dfc34e7c2cb7022cc20522.jpg"
    ),
    Event(
        name="3R Workshop",
        description="Learn how to recycle effectively and earn extra points.",
        date=datetime(2025, 2, 10),
        poster_url="https://i.etsystatic.com/31847995/r/il/63219e/4226453121/il_fullxfull.4226453121_du9d.jpg"
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
    db_session.commit()
    print("Sample events inserted successfully!")
except Exception as e:
    db_session.rollback()
    print(f"An error occurred: {e}")
finally:
    db_session.close()
