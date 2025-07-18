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
    timestamp = Column(DateTime, default=func.now())


# New Models for Audit Requirements

class OfflineAction(Base):
    """Offline action queue model"""
    __tablename__ = "offline_actions"
    
    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False)
    action_type = Column(String(50), nullable=False)  # SIGNAL_PARSE, TRADE_OPEN, TRADE_CLOSE, etc.
    payload = Column(JSON, nullable=False)
    timestamp = Column(DateTime, default=func.now())
    synced = Column(Boolean, default=False)
    sync_attempts = Column(Integer, default=0)
    sync_error = Column(Text, nullable=True)
    conflict_resolution = Column(String(20), nullable=True)  # MERGE, OVERWRITE, SKIP, MANUAL


class MarketplacePlugin(Base):
    """Marketplace plugin model"""
    __tablename__ = "marketplace_plugins"
    
    id = Column(String, primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    version = Column(String(20), nullable=False)
    author = Column(String(100), nullable=False)
    category = Column(String(50), nullable=False)  # SIGNAL_PROVIDER, STRATEGY, INDICATOR, UTILITY
    plugin_type = Column(String(30), nullable=False)  # OFFICIAL, COMMUNITY, PREMIUM
    rating = Column(Float, default=0.0)
    downloads = Column(Integer, default=0)
    price = Column(Float, default=0.0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now())
    config_schema = Column(JSON, nullable=True)  # JSON schema for configuration


class UserPlugin(Base):
    """User installed plugins model"""
    __tablename__ = "user_plugins"
    
    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False)
    plugin_id = Column(String, nullable=False)
    status = Column(String(20), default="installed")  # INSTALLED, ACTIVE, INACTIVE, UNINSTALLED
    config = Column(JSON, nullable=True)
    installed_at = Column(DateTime, default=func.now())
    last_used = Column(DateTime, nullable=True)


class ComplianceProfile(Base):
    """Compliance/regulatory profile model"""
    __tablename__ = "compliance_profiles"
    
    id = Column(String, primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    profile_type = Column(String(30), nullable=False)  # PROP_FIRM, REGULATORY, CUSTOM
    restrictions = Column(JSON, nullable=False)  # Trading restrictions and limits
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())


class UserCompliance(Base):
    """User compliance settings model"""
    __tablename__ = "user_compliance"
    
    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False)
    profile_id = Column(String, nullable=False)
    custom_restrictions = Column(JSON, nullable=True)
    is_active = Column(Boolean, default=True)
    activated_at = Column(DateTime, default=func.now())


class OnboardingStep(Base):
    """Onboarding step model"""
    __tablename__ = "onboarding_steps"
    
    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False)
    step_name = Column(String(50), nullable=False)
    step_type = Column(String(30), nullable=False)  # PROFILE, BROKER, PROVIDER, STRATEGY, TEST
    status = Column(String(20), default="pending")  # PENDING, IN_PROGRESS, COMPLETED, SKIPPED, FAILED
    data = Column(JSON, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.now())


class TwoFactorAuth(Base):
    """Two-factor authentication model"""
    __tablename__ = "two_factor_auth"
    
    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False)
    method = Column(String(20), nullable=False)  # TOTP, SMS, EMAIL
    secret = Column(String(32), nullable=True)  # TOTP secret
    phone_number = Column(String(20), nullable=True)  # SMS
    backup_codes = Column(JSON, nullable=True)  # Recovery codes
    is_active = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())
    last_used = Column(DateTime, nullable=True)


class SyncConflict(Base):
    """Sync conflict resolution model"""
    __tablename__ = "sync_conflicts"
    
    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False)
    offline_action_id = Column(String, nullable=False)
    conflict_type = Column(String(30), nullable=False)  # DATA_MISMATCH, DUPLICATE_ACTION, STALE_DATA
    local_data = Column(JSON, nullable=False)
    server_data = Column(JSON, nullable=False)
    resolution = Column(String(20), nullable=True)  # MERGE, USE_LOCAL, USE_SERVER, MANUAL
    resolved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.now())
    metric_value = Column(Float, nullable=False)
    metric_data = Column(JSON, nullable=True)
    recorded_at = Column(DateTime, default=func.now())