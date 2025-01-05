# models.py

from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Date
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import re
import logging

Base = declarative_base()

# Sensitive Info Filter
class SensitiveInfoFilter(logging.Filter):
    """Filter to redact sensitive information like the bot token in logs."""
    def __init__(self, sensitive_data: list):
        super().__init__()
        self.sensitive_data = sensitive_data

    def filter(self, record):
        if record.msg:
            # Replace each sensitive string with a placeholder
            for sensitive in self.sensitive_data:
                record.msg = re.sub(rf"{sensitive}", "[REDACTED]", str(record.msg))
        return True

class TNGPin(Base):
    __tablename__ = 'tng_pins'

    id = Column(Integer, primary_key=True, index=True)
    pin = Column(String, unique=True, index=True, nullable=False)
    reward_id = Column(Integer, ForeignKey('rewards.id'), nullable=False)
    used = Column(Boolean, default=False)
    used_by = Column(Integer, ForeignKey('users.id'), nullable=True)
    used_at = Column(DateTime, nullable=True)

    # Relationships
    reward = relationship("Reward", back_populates="tng_pins")
    user = relationship("User", back_populates="tng_pins")

    def __repr__(self):
        return f"<TNGPin(pin='{self.pin}', reward_id={self.reward_id}, used={self.used})>"

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(Integer, unique=True, index=True, nullable=False)
    phone_number = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=True)
    points = Column(Integer, default=0)

    # Relationships
    transactions = relationship("Transaction", back_populates="user", cascade="all, delete-orphan")
    redemptions = relationship("Redemption", back_populates="user", cascade="all, delete-orphan")
    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")
    tng_pins = relationship("TNGPin", back_populates="user")

    def __repr__(self):
        return f"<User(name='{self.name}', telegram_id={self.telegram_id}, points={self.points})>"

class Reward(Base):
    __tablename__ = "rewards"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)  # Ensure uniqueness
    description = Column(String, nullable=True)
    points_required = Column(Integer, nullable=False)
    quantity_available = Column(Integer, default=0)

    # Relationships
    redemptions = relationship("Redemption", back_populates="reward", cascade="all, delete-orphan")
    tng_pins = relationship("TNGPin", back_populates="reward", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Reward(name='{self.name}', points_required={self.points_required}, quantity_available={self.quantity_available})>"

class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    points_change = Column(Integer, nullable=False)
    description = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="transactions")

    def __repr__(self):
        return f"<Transaction(user_id={self.user_id}, points_change={self.points_change}, description='{self.description}')>"

class Redemption(Base):
    __tablename__ = "redemptions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    reward_id = Column(Integer, ForeignKey("rewards.id"), nullable=False)
    status = Column(String, default="Pending")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="redemptions")
    reward = relationship("Reward", back_populates="redemptions")

    def __repr__(self):
        return f"<Redemption(user_id={self.user_id}, reward_id={self.reward_id}, status='{self.status}')>"

class Event(Base):
    __tablename__ = "events"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    date = Column(Date, nullable=False)
    poster_url = Column(String, nullable=True)

    def __repr__(self):
        return f"<Event(name='{self.name}', date={self.date})>"

class UserSession(Base):
    __tablename__ = "user_sessions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    start_time = Column(Integer, nullable=False)  # Epoch timestamp in milliseconds
    end_time = Column(Integer, nullable=False)    # Epoch timestamp in milliseconds

    # Relationships
    user = relationship("User", back_populates="sessions")

    def __repr__(self):
        return f"<UserSession(user_id={self.user_id}, start_time={self.start_time}, end_time={self.end_time})>"

class Configuration(Base):
    __tablename__ = "configuration"
    id = Column(Integer, primary_key=True, index=True)
    active_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    def __repr__(self):
        return f"<Configuration(active_user_id={self.active_user_id})>"
