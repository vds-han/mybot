from sqlalchemy.orm import Session
from database import SessionLocal
from models import User

# Create a session
db_session = SessionLocal()

# Fetch and print user data
users = db_session.query(User).all()
print("Registered Users:")
for user in users:
    print(f"ID: {user.id}, Telegram ID: {user.telegram_id}, Points: {user.points}, Phone Number: {user.phone_number}")

db_session.close()
