from database import SessionLocal, User

def list_users():
    db = SessionLocal()
    users = db.query(User).all()
    print("Registered Users:")
    for user in users:
        print(f"ID: {user.id}, Name: {user.name}, Telegram ID: {user.telegram_id}")
    db.close()

def remove_user(telegram_id):
    db = SessionLocal()
    user = db.query(User).filter_by(telegram_id=telegram_id).first()
    if user:
        db.delete(user)
        db.commit()
        print(f"Removed user: {user.name} (Telegram ID: {telegram_id})")
    else:
        print(f"No user found with Telegram ID: {telegram_id}")
    db.close()

# Example usage
if __name__ == "__main__":
    print("1. List users")
    print("2. Remove user by Telegram ID")
    choice = input("Enter your choice: ")
    if choice == "1":
        list_users()
    elif choice == "2":
        telegram_id = int(input("Enter Telegram ID to remove: "))
        remove_user(telegram_id)
    else:
        print("Invalid choice.")
