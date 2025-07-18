"""
Database models for SignalOS Backend
"""

from sqlalchemy import Column, String, Integer, Float, DateTime, Boolean, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from datetime import datetime

Base = declarative_base()


class User(Base):
    """User model"""
    __tablename__ = "users"
    
    id = Column(String, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    telegram_id = Column(String(50), nullable=True)
    device_fingerprint = Column(String(64), nullable=False)
    license_key = Column(String(32), unique=True, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    last_login = Column(DateTime, nullable=True)


class Signal(Base):
    """Signal model"""
    __tablename__ = "signals"
    
    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False)
    symbol = Column(String(10), nullable=False)
    signal_type = Column(String(10), nullable=False)  # BUY, SELL, CLOSE, MODIFY
    entry_price = Column(Float, nullable=True)
    stop_loss = Column(Float, nullable=True)
    take_profit = Column(JSON, nullable=True)  # List of TP levels
    lot_size = Column(Float, nullable=True)
    confidence = Column(String(20), nullable=False)  # HIGH, MEDIUM, LOW, UNCERTAIN
    raw_text = Column(Text, nullable=False)
    parsing_method = Column(String(50), nullable=False)
    image_data = Column(Text, nullable=True)  # Base64 encoded
    processed_at = Column(DateTime, default=func.now())
    executed = Column(Boolean, default=False)


class TradeOrder(Base):
    """Trade order model"""
    __tablename__ = "trade_orders"
    
    id = Column(String, primary_key=True)
    signal_id = Column(String, nullable=True)
    user_id = Column(String, nullable=False)
    symbol = Column(String(10), nullable=False)
    order_type = Column(Integer, nullable=False)  # MT5 order type
    volume = Column(Float, nullable=False)
    price = Column(Float, nullable=True)
    stop_loss = Column(Float, nullable=True)
    take_profit = Column(Float, nullable=True)
    deviation = Column(Integer, default=10)
    magic_number = Column(Integer, default=12345)
    comment = Column(String(100), default="SignalOS")
    status = Column(String(20), nullable=False)  # PENDING, EXECUTING, EXECUTED, FAILED, CANCELLED
    ticket = Column(Integer, nullable=True)  # MT5 ticket
    executed_price = Column(Float, nullable=True)
    executed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.now())
    error_message = Column(Text, nullable=True)


class License(Base):
    """License model"""
    __tablename__ = "licenses"
    
    id = Column(String, primary_key=True)
    license_key = Column(String(32), unique=True, nullable=False)
    user_id = Column(String, nullable=False)
    device_id = Column(String(16), nullable=False)
    plan_type = Column(String(20), default="standard")
    features = Column(JSON, nullable=False)  # Dict of features
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    expires_at = Column(DateTime, nullable=False)
    last_validated = Column(DateTime, nullable=True)


class SystemLog(Base):
    """System log model"""
    __tablename__ = "system_logs"
    
    id = Column(String, primary_key=True)
    level = Column(String(10), nullable=False)  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    module = Column(String(50), nullable=False)
    message = Column(Text, nullable=False)
    user_id = Column(String, nullable=True)
    extra_data = Column(JSON, nullable=True)
    timestamp = Column(DateTime, default=func.now())


class QueueTask(Base):
    """Queue task model"""
    __tablename__ = "queue_tasks"
    
    id = Column(String, primary_key=True)
    task_type = Column(String(50), nullable=False)
    data = Column(JSON, nullable=False)
    priority = Column(Integer, default=2)  # 1=LOW, 2=NORMAL, 3=HIGH, 4=CRITICAL
    status = Column(String(20), nullable=False)  # PENDING, PROCESSING, COMPLETED, FAILED, RETRYING
    attempts = Column(Integer, default=0)
    max_attempts = Column(Integer, default=3)
    created_at = Column(DateTime, default=func.now())
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    result = Column(JSON, nullable=True)


class SystemStats(Base):
    """System statistics model"""
    __tablename__ = "system_stats"
    
    id = Column(String, primary_key=True)
    metric_name = Column(String(50), nullable=False)
    metric_value = Column(Float, nullable=False)
    metric_data = Column(JSON, nullable=True)
    recorded_at = Column(DateTime, default=func.now())