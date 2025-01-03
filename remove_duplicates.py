from database import SessionLocal
from models import Event, Reward

# Create a database session
db = SessionLocal()

# Function to remove duplicates based on a unique field (e.g., name)
def remove_duplicates(table, unique_field):
    records = db.query(table).all()
    seen = set()
    duplicates_removed = 0

    for record in records:
        unique_value = getattr(record, unique_field)
        if unique_value in seen:
            db.delete(record)
            duplicates_removed += 1
        else:
            seen.add(unique_value)

    db.commit()
    return duplicates_removed

# Remove duplicate events
event_duplicates = remove_duplicates(Event, "name")
print(f"Removed {event_duplicates} duplicate events.")

# Remove duplicate rewards
reward_duplicates = remove_duplicates(Reward, "name")
print(f"Removed {reward_duplicates} duplicate rewards.")

# Close the session
db.close()
