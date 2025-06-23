"""
News Filter Engine for SignalOS
Blocks signal execution during high-impact news events to prevent trades during volatile market conditions
"""

import json
import time
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import os
import requests

class NewsImpact(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class FilterStatus(Enum):
    ALLOWED = "allowed"
    BLOCKED_NEWS = "blocked_news"
    BLOCKED_MANUAL = "blocked_manual"
    OVERRIDE_ACTIVE = "override_active"

@dataclass
class NewsEvent:
    event_id: str
    title: str
    currency: str
    impact: NewsImpact
    event_time: datetime
    actual: Optional[str] = None
    forecast: Optional[str] = None
    previous: Optional[str] = None
    source: str = "unknown"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "title": self.title,
            "currency": self.currency,
            "impact": self.impact.value,
            "event_time": self.event_time.isoformat(),
            "actual": self.actual,
            "forecast": self.forecast,
            "previous": self.previous,
            "source": self.source
        }

@dataclass
class FilterResult:
    status: FilterStatus
    reason: str
    news_events: List[NewsEvent]
    next_clear_time: Optional[datetime] = None
    override_expires: Optional[datetime] = None

@dataclass
class NewsFilterConfig:
    enabled: bool = True
    impact_filters: Dict[str, bool] = None  # Which impact levels to filter
    time_buffers: Dict[str, int] = None  # Minutes before/after news
    symbol_mappings: Dict[str, List[str]] = None  # Currency to symbols mapping
    manual_override_duration: int = 60  # Minutes
    news_sources: List[str] = None
    update_interval: int = 300  # 5 minutes
    
    def __post_init__(self):
        if self.impact_filters is None:
            self.impact_filters = {
                "critical": True,
                "high": True,
                "medium": False,
                "low": False
            }
        if self.time_buffers is None:
            self.time_buffers = {
                "critical": 60,  # 1 hour before/after
                "high": 30,      # 30 minutes before/after
                "medium": 15,    # 15 minutes before/after
                "low": 5         # 5 minutes before/after
            }
        if self.symbol_mappings is None:
            self.symbol_mappings = {
                "USD": ["EURUSD", "GBPUSD", "AUDUSD", "NZDUSD", "USDCAD", "USDCHF", "USDJPY"],
                "EUR": ["EURUSD", "EURGBP", "EURAUD", "EURCHF", "EURJPY"],
                "GBP": ["GBPUSD", "EURGBP", "GBPAUD", "GBPCHF", "GBPJPY"],
                "AUD": ["AUDUSD", "EURAUD", "GBPAUD", "AUDCAD", "AUDJPY"],
                "JPY": ["USDJPY", "EURJPY", "GBPJPY", "AUDJPY", "CADJPY"],
                "CAD": ["USDCAD", "AUDCAD", "CADJPY"],
                "CHF": ["USDCHF", "EURCHF", "GBPCHF"],
                "NZD": ["NZDUSD", "NZDJPY"]
            }
        if self.news_sources is None:
            self.news_sources = ["forexfactory", "investing", "fxstreet"]

class NewsFilter:
    def __init__(self, config_path: str = "config.json", log_path: str = "logs/news_filter.log"):
        self.config_path = config_path
        self.log_path = log_path
        self.config = self._load_config()
        self.logger = self._setup_logger()
        
        # News data storage
        self.news_events: List[NewsEvent] = []
        self.last_update: Optional[datetime] = None
        
        # Manual override state
        self.manual_override_active: bool = False
        self.override_expires: Optional[datetime] = None
        self.manual_block_active: bool = False
        self.manual_block_expires: Optional[datetime] = None
        
        # Background update task
        self.update_task = None
        self.is_updating = False
        
        # Load existing news data
        self._load_news_data()
        
    def _load_config(self) -> NewsFilterConfig:
        """Load news filter configuration"""
        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)
                
            if "news_filter" not in config:
                config["news_filter"] = {
                    "enabled": True,
                    "impact_filters": {
                        "critical": True,
                        "high": True,
                        "medium": False,
                        "low": False
                    },
                    "time_buffers": {
                        "critical": 60,
                        "high": 30,
                        "medium": 15,
                        "low": 5
                    },
                    "manual_override_duration": 60,
                    "update_interval": 300,
                    "news_sources": ["forexfactory"],
                    "api_settings": {
                        "forexfactory_url": "https://nfs.faireconomy.media/ff_calendar_thisweek.json",
                        "backup_sources": ["investing", "fxstreet"],
                        "request_timeout": 30,
                        "retry_attempts": 3
                    }
                }
                self._save_config(config)
                
            news_config_data = config.get("news_filter", {})
            
            return NewsFilterConfig(
                enabled=news_config_data.get("enabled", True),
                impact_filters=news_config_data.get("impact_filters"),
                time_buffers=news_config_data.get("time_buffers"),
                manual_override_duration=news_config_data.get("manual_override_duration", 60),
                news_sources=news_config_data.get("news_sources"),
                update_interval=news_config_data.get("update_interval", 300)
            )
            
        except FileNotFoundError:
            self.logger.warning(f"Config file not found: {self.config_path}, using defaults")
            return NewsFilterConfig()
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in config file: {e}")
            return NewsFilterConfig()
            
    def _save_config(self, full_config: Dict[str, Any]):
        """Save updated configuration"""
        try:
            with open(self.config_path, 'w') as f:
                json.dump(full_config, f, indent=4)
        except Exception as e:
            self.logger.error(f"Failed to save config: {e}")
            
    def _setup_logger(self) -> logging.Logger:
        """Setup dedicated logger for news filter"""
        logger = logging.getLogger("news_filter")
        logger.setLevel(logging.INFO)
        
        # Create logs directory if it doesn't exist
        os.makedirs(os.path.dirname(self.log_path), exist_ok=True)
        
        # File handler
        file_handler = logging.FileHandler(self.log_path)
        file_handler.setLevel(logging.INFO)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.WARNING)
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        if not logger.handlers:
            logger.addHandler(file_handler)
            logger.addHandler(console_handler)
            
        return logger
        
    def _load_news_data(self):
        """Load existing news data from storage"""
        news_file = self.log_path.replace('.log', '_events.json')
        try:
            if os.path.exists(news_file):
                with open(news_file, 'r') as f:
                    news_data = json.load(f)
                    
                for event_data in news_data.get('news_events', []):
                    event = NewsEvent(
                        event_id=event_data['event_id'],
                        title=event_data['title'],
                        currency=event_data['currency'],
                        impact=NewsImpact(event_data['impact']),
                        event_time=datetime.fromisoformat(event_data['event_time']),
                        actual=event_data.get('actual'),
                        forecast=event_data.get('forecast'),
                        previous=event_data.get('previous'),
                        source=event_data.get('source', 'unknown')
                    )
                    self.news_events.append(event)
                    
                self.last_update = datetime.fromisoformat(news_data.get('last_update', datetime.now().isoformat()))
                self.logger.info(f"Loaded {len(self.news_events)} news events from storage")
                
        except Exception as e:
            self.logger.error(f"Error loading news data: {e}")
            
    def _save_news_data(self):
        """Save news data to storage"""
        news_file = self.log_path.replace('.log', '_events.json')
        try:
            news_data = {
                'news_events': [event.to_dict() for event in self.news_events],
                'last_update': self.last_update.isoformat() if self.last_update else datetime.now().isoformat()
            }
            
            with open(news_file, 'w') as f:
                json.dump(news_data, f, indent=4)
                
        except Exception as e:
            self.logger.error(f"Error saving news data: {e}")
            
    def _fetch_forex_factory_news(self) -> List[NewsEvent]:
        """Fetch news events from Forex Factory"""
        try:
            with open(self.config_path, 'r') as f:
                full_config = json.load(f)
            
            api_settings = full_config.get("news_filter", {}).get("api_settings", {})
            url = api_settings.get("forexfactory_url", "https://nfs.faireconomy.media/ff_calendar_thisweek.json")
            timeout = api_settings.get("request_timeout", 30)
            
            response = requests.get(url, timeout=timeout)
            response.raise_for_status()
            
            events = []
            data = response.json()
            
            for item in data:
                try:
                    # Parse impact level
                    impact_str = item.get('impact', 'low').lower()
                    if impact_str == 'non economic':
                        impact = NewsImpact.LOW
                    elif impact_str == 'low':
                        impact = NewsImpact.LOW
                    elif impact_str == 'medium':
                        impact = NewsImpact.MEDIUM
                    elif impact_str == 'high':
                        impact = NewsImpact.HIGH
                    else:
                        impact = NewsImpact.MEDIUM  # Default
                    
                    # Parse event time
                    date_str = item.get('date', '')
                    time_str = item.get('time', '')
                    
                    if date_str and time_str:
                        # Combine date and time
                        datetime_str = f"{date_str} {time_str}"
                        try:
                            event_time = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M")
                        except ValueError:
                            # Try alternative format
                            event_time = datetime.strptime(datetime_str, "%m-%d-%Y %H:%M")
                    else:
                        continue  # Skip events without proper time
                    
                    # Create event
                    event = NewsEvent(
                        event_id=f"ff_{item.get('id', hash(item.get('title', '')))}",
                        title=item.get('title', 'Unknown Event'),
                        currency=item.get('currency', 'USD'),
                        impact=impact,
                        event_time=event_time,
                        actual=item.get('actual'),
                        forecast=item.get('forecast'),
                        previous=item.get('previous'),
                        source="forexfactory"
                    )
                    events.append(event)
                    
                except Exception as e:
                    self.logger.warning(f"Error parsing news event: {e}")
                    continue
                    
            self.logger.info(f"Fetched {len(events)} events from Forex Factory")
            return events
            
        except requests.RequestException as e:
            self.logger.error(f"Error fetching from Forex Factory: {e}")
            return []
        except Exception as e:
            self.logger.error(f"Unexpected error fetching news: {e}")
            return []
            
    def _fetch_mock_news_data(self) -> List[NewsEvent]:
        """Generate mock news data for testing purposes"""
        mock_events = []
        now = datetime.now()
        
        # Create some test events
        test_events = [
            {
                "title": "Non-Farm Payrolls",
                "currency": "USD",
                "impact": NewsImpact.HIGH,
                "time_offset": 30  # 30 minutes from now
            },
            {
                "title": "ECB Interest Rate Decision",
                "currency": "EUR",
                "impact": NewsImpact.HIGH,
                "time_offset": 120  # 2 hours from now
            },
            {
                "title": "UK GDP",
                "currency": "GBP",
                "impact": NewsImpact.MEDIUM,
                "time_offset": 240  # 4 hours from now
            }
        ]
        
        for i, event_data in enumerate(test_events):
            event_time = now + timedelta(minutes=event_data["time_offset"])
            event = NewsEvent(
                event_id=f"mock_{i}",
                title=event_data["title"],
                currency=event_data["currency"],
                impact=event_data["impact"],
                event_time=event_time,
                source="mock"
            )
            mock_events.append(event)
            
        return mock_events
        
    async def update_news_data(self, force_update: bool = False) -> bool:
        """Update news data from external sources"""
        try:
            # Check if update is needed
            if not force_update and self.last_update:
                time_since_update = (datetime.now() - self.last_update).total_seconds()
                if time_since_update < self.config.update_interval:
                    return True
                    
            self.logger.info("Updating news data...")
            
            # Try to fetch from configured sources
            new_events = []
            
            if "forexfactory" in self.config.news_sources:
                ff_events = self._fetch_forex_factory_news()
                new_events.extend(ff_events)
                
            # If no events fetched and in testing mode, use mock data
            if not new_events:
                self.logger.warning("No news data fetched, using mock data for testing")
                new_events = self._fetch_mock_news_data()
                
            # Filter out old events (older than 24 hours)
            cutoff_time = datetime.now() - timedelta(hours=24)
            current_events = [event for event in new_events if event.event_time > cutoff_time]
            
            # Update events list
            self.news_events = current_events
            self.last_update = datetime.now()
            
            # Save to storage
            self._save_news_data()
            
            self.logger.info(f"Updated news data: {len(self.news_events)} current events")
            return True
            
        except Exception as e:
            self.logger.error(f"Error updating news data: {e}")
            return False
            
    def _get_affected_symbols(self, currency: str) -> List[str]:
        """Get symbols affected by news for a specific currency"""
        return self.config.symbol_mappings.get(currency, [])
        
    def _is_news_active(self, event: NewsEvent, current_time: datetime) -> bool:
        """Check if a news event is currently affecting trading"""
        if not self.config.impact_filters.get(event.impact.value, False):
            return False
            
        buffer_minutes = self.config.time_buffers.get(event.impact.value, 0)
        
        start_time = event.event_time - timedelta(minutes=buffer_minutes)
        end_time = event.event_time + timedelta(minutes=buffer_minutes)
        
        return start_time <= current_time <= end_time
        
    def check_symbol_filter(self, symbol: str, current_time: Optional[datetime] = None) -> FilterResult:
        """Check if trading is allowed for a specific symbol"""
        if current_time is None:
            current_time = datetime.now()
            
        # Check if filtering is disabled
        if not self.config.enabled:
            return FilterResult(
                status=FilterStatus.ALLOWED,
                reason="News filtering disabled",
                news_events=[]
            )
            
        # Check manual override
        if self.manual_override_active and self.override_expires and current_time < self.override_expires:
            return FilterResult(
                status=FilterStatus.OVERRIDE_ACTIVE,
                reason="Manual override active",
                news_events=[],
                override_expires=self.override_expires
            )
            
        # Check manual block
        if self.manual_block_active and self.manual_block_expires and current_time < self.manual_block_expires:
            return FilterResult(
                status=FilterStatus.BLOCKED_MANUAL,
                reason="Manual block active",
                news_events=[],
                override_expires=self.manual_block_expires
            )
            
        # Find active news events affecting this symbol
        active_events = []
        
        for event in self.news_events:
            if self._is_news_active(event, current_time):
                affected_symbols = self._get_affected_symbols(event.currency)
                if symbol in affected_symbols:
                    active_events.append(event)
                    
        if active_events:
            # Find next clear time
            next_clear = None
            for event in active_events:
                buffer_minutes = self.config.time_buffers.get(event.impact.value, 0)
                event_end = event.event_time + timedelta(minutes=buffer_minutes)
                if next_clear is None or event_end > next_clear:
                    next_clear = event_end
                    
            return FilterResult(
                status=FilterStatus.BLOCKED_NEWS,
                reason=f"Blocked due to {len(active_events)} active news event(s)",
                news_events=active_events,
                next_clear_time=next_clear
            )
            
        return FilterResult(
            status=FilterStatus.ALLOWED,
            reason="No active news events affecting symbol",
            news_events=[]
        )
        
    def enable_manual_override(self, duration_minutes: int = None) -> bool:
        """Enable manual override to allow trading during news"""
        try:
            if duration_minutes is None:
                duration_minutes = self.config.manual_override_duration
                
            self.manual_override_active = True
            self.override_expires = datetime.now() + timedelta(minutes=duration_minutes)
            self.manual_block_active = False  # Disable manual block if active
            
            self.logger.info(f"Manual override enabled for {duration_minutes} minutes")
            return True
            
        except Exception as e:
            self.logger.error(f"Error enabling manual override: {e}")
            return False
            
    def disable_manual_override(self) -> bool:
        """Disable manual override"""
        try:
            self.manual_override_active = False
            self.override_expires = None
            
            self.logger.info("Manual override disabled")
            return True
            
        except Exception as e:
            self.logger.error(f"Error disabling manual override: {e}")
            return False
            
    def enable_manual_block(self, duration_minutes: int = 60) -> bool:
        """Enable manual block to prevent all trading"""
        try:
            self.manual_block_active = True
            self.manual_block_expires = datetime.now() + timedelta(minutes=duration_minutes)
            self.manual_override_active = False  # Disable override if active
            
            self.logger.info(f"Manual block enabled for {duration_minutes} minutes")
            return True
            
        except Exception as e:
            self.logger.error(f"Error enabling manual block: {e}")
            return False
            
    def disable_manual_block(self) -> bool:
        """Disable manual block"""
        try:
            self.manual_block_active = False
            self.manual_block_expires = None
            
            self.logger.info("Manual block disabled")
            return True
            
        except Exception as e:
            self.logger.error(f"Error disabling manual block: {e}")
            return False
            
    def get_upcoming_news(self, hours_ahead: int = 24, impact_filter: Optional[List[str]] = None) -> List[NewsEvent]:
        """Get upcoming news events"""
        now = datetime.now()
        end_time = now + timedelta(hours=hours_ahead)
        
        upcoming = []
        for event in self.news_events:
            if now <= event.event_time <= end_time:
                if impact_filter is None or event.impact.value in impact_filter:
                    upcoming.append(event)
                    
        # Sort by event time
        upcoming.sort(key=lambda x: x.event_time)
        return upcoming
        
    def get_current_news_status(self) -> Dict[str, Any]:
        """Get current news filter status"""
        now = datetime.now()
        
        # Count active events by impact
        active_events = []
        for event in self.news_events:
            if self._is_news_active(event, now):
                active_events.append(event)
                
        impact_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for event in active_events:
            impact_counts[event.impact.value] += 1
            
        return {
            "enabled": self.config.enabled,
            "total_events_loaded": len(self.news_events),
            "active_events": len(active_events),
            "active_by_impact": impact_counts,
            "manual_override_active": self.manual_override_active,
            "override_expires": self.override_expires.isoformat() if self.override_expires else None,
            "manual_block_active": self.manual_block_active,
            "block_expires": self.manual_block_expires.isoformat() if self.manual_block_expires else None,
            "last_update": self.last_update.isoformat() if self.last_update else None
        }
        
    async def start_auto_update(self):
        """Start automatic news data updates"""
        if not self.is_updating:
            self.is_updating = True
            try:
                self.update_task = asyncio.create_task(self._auto_update_loop())
                self.logger.info("Auto news update started")
            except RuntimeError:
                self.is_updating = False
                self.logger.warning("No event loop running, cannot start auto update")
                
    def stop_auto_update(self):
        """Stop automatic news data updates"""
        if self.is_updating:
            self.is_updating = False
            if self.update_task:
                self.update_task.cancel()
            self.logger.info("Auto news update stopped")
            
    async def _auto_update_loop(self):
        """Background task for automatic news updates"""
        while self.is_updating:
            try:
                await self.update_news_data()
                await asyncio.sleep(self.config.update_interval)
            except Exception as e:
                self.logger.error(f"Error in auto update loop: {e}")
                await asyncio.sleep(60)  # Wait before retrying

# Global instance for easy access
news_filter = NewsFilter()