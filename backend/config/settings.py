"""
Configuration settings for SignalOS Backend
"""

import os
from typing import List, Optional
from pydantic import field_validator
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings"""
    
    # Application
    APP_NAME: str = "SignalOS Backend"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = "production"
    DEBUG: bool = False
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    WORKERS: int = 1
    LOG_LEVEL: str = "INFO"
    
    # Security
    SECRET_KEY: str = "change-me-in-production"
    JWT_SECRET_KEY: str = "jwt-secret-change-me"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = 24
    
    # CORS
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:5000,http://localhost:8000"
    
    # Database
    DATABASE_URL: str = "sqlite:///./signalos.db"
    DATABASE_POOL_SIZE: int = 5
    
    # Redis/Queue
    REDIS_URL: str = "redis://localhost:6379/0"
    QUEUE_MAX_RETRIES: int = 3
    QUEUE_RETRY_DELAY: int = 5
    
    # MT5 Trading
    MT5_HOST: str = "localhost"
    MT5_PORT: int = 9999
    MT5_TIMEOUT: int = 30
    
    # Telegram
    TELEGRAM_BOT_TOKEN: Optional[str] = None
    TELEGRAM_API_ID: Optional[str] = None
    TELEGRAM_API_HASH: Optional[str] = None
    
    # AI/ML
    AI_MODEL_PATH: str = "./models"
    AI_CONFIDENCE_THRESHOLD: float = 0.8
    AI_MAX_TOKENS: int = 1000
    
    # Signal Processing
    SIGNAL_QUEUE_SIZE: int = 1000
    SIGNAL_PROCESSING_TIMEOUT: int = 30
    SIGNAL_RETRY_ATTEMPTS: int = 3
    
    # Trading
    MAX_DAILY_TRADES: int = 50
    MAX_RISK_PER_TRADE: float = 0.02
    DEFAULT_LOT_SIZE: float = 0.01
    
    # Logging
    LOG_FILE_PATH: str = "./logs/signalos.log"
    LOG_ROTATION_SIZE: str = "10MB"
    LOG_RETENTION_DAYS: int = 30
    
    @field_validator("ENVIRONMENT")
    @classmethod
    def validate_environment(cls, v):
        if v not in ["development", "staging", "production"]:
            raise ValueError("ENVIRONMENT must be development, staging, or production")
        return v
    
    @field_validator("LOG_LEVEL")
    @classmethod
    def validate_log_level(cls, v):
        if v.upper() not in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            raise ValueError("LOG_LEVEL must be DEBUG, INFO, WARNING, ERROR, or CRITICAL")
        return v.upper()
    
    def get_allowed_origins(self) -> List[str]:
        """Parse CORS origins from string"""
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()