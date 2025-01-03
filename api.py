# api.py
from flask import Flask, request
from database import SessionLocal
from models import User, Transaction
import os

app = Flask(__name__)
db_session = SessionLocal()

@app.route('/add_points', methods=['POST'])
def add_points():
    data = request.json
    user_id = data.get(
        'user_id')
    points = data.get('points')
    description = data.get('description', 'Points added')

    user = db_session.query(User).filter_by(telegram_id=user_id).first()
    if not user:
        return {"status": "error", "message": "User not found"}, 404

    user.points += points
    transaction = Transaction(
        user_id=user_id,
        points_change=points,
        description=description
    )
    db_session.add(transaction)
    db_session.commit()
    return {"status": "success", "message": f"{points} points added"}, 200

if __name__ == '__main__':
    app.run(port=5000)
