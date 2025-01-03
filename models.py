from sqlalchemy import Column, Integer, String, Date, DateTime, ForeignKey, BigInteger, UniqueConstraint  # Updated import
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(BigInteger, unique=True, index=True, nullable=False)
    phone_number = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=True)
    points = Column(Integer, default=0)

    # Relationships
    transactions = relationship("Transaction", back_populates="user", cascade="all, delete-orphan")
    redemptions = relationship("Redemption", back_populates="user", cascade="all, delete-orphan")
    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")
    # Removed the ActiveUser relationship since activation is now managed by Configuration

class Reward(Base):
    __tablename__ = "rewards"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    points_required = Column(Integer, nullable=False)
    quantity_available = Column(Integer, default=0)

    # Relationships
    redemptions = relationship("Redemption", back_populates="reward", cascade="all, delete-orphan")

class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    points_change = Column(Integer, nullable=False)
    description = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)  # Use DateTime

    # Relationships
    user = relationship("User", back_populates="transactions")

class Redemption(Base):
    __tablename__ = "redemptions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    reward_id = Column(Integer, ForeignKey("rewards.id"), nullable=False)
    status = Column(String, default="Pending")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)  # Changed from Date to DateTime

    # Relationships
    user = relationship("User", back_populates="redemptions")
    reward = relationship("Reward", back_populates="redemptions")

class Event(Base):
    __tablename__ = "events"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    date = Column(Date, nullable=False)
    poster_url = Column(String, nullable=True)

class UserSession(Base):
    __tablename__ = "user_sessions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    start_time = Column(BigInteger, nullable=False)  # Epoch timestamp in milliseconds
    end_time = Column(BigInteger, nullable=False)    # Epoch timestamp in milliseconds

    # Relationships
    user = relationship("User", back_populates="sessions")


class Configuration(Base):
    __tablename__ = "configuration"
    id = Column(Integer, primary_key=True, index=True)
    active_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
