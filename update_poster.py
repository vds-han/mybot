from database import SessionLocal
from models import Event

def update_poster(event_name, new_poster_url):
    """Update the poster URL for a specific event."""
    db_session = SessionLocal()
    
    try:
        # Find the event by its name
        event = db_session.query(Event).filter_by(name=event_name).first()
        if event:
            # Update the poster URL
            event.poster_url = new_poster_url
            db_session.commit()
            print(f"Poster URL updated for event: {event_name}")
        else:
            print(f"Event not found: {event_name}")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        db_session.close()

# Usage
if __name__ == "__main__":
    # Replace with the event name and new image URL
    event_name = "Recycling Workshop"  # Name of the event to update
    new_poster_url = "https://thumbs.dreamstime.com/z/go-green-recycle-reduce-reuse-eco-poster-concept-vector-creative-organic-illustration-rough-background-86195465.jpg"  # New image URL
    
    update_poster(event_name, new_poster_url)
