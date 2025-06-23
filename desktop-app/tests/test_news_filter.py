"""
Test Suite for News Filter Engine
Tests news event filtering, symbol-specific blocking, and manual override functionality
"""

import unittest
import asyncio
import json
import tempfile
import os
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from news_filter import (
    NewsFilter, NewsEvent, NewsImpact, FilterStatus, FilterResult, NewsFilterConfig
)

class TestNewsFilter(unittest.TestCase):
    
    def setUp(self):
        """Set up test environment"""
        # Create temporary config file
        self.temp_config = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        self.temp_log = tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False)
        
        # Test configuration
        test_config = {
            "news_filter": {
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
                "news_sources": ["mock"],
                "api_settings": {
                    "request_timeout": 10,
                    "retry_attempts": 1
                }
            }
        }
        
        json.dump(test_config, self.temp_config)
        self.temp_config.close()
        
        # Initialize news filter
        self.filter = NewsFilter(
            config_path=self.temp_config.name,
            log_path=self.temp_log.name
        )
        
    def tearDown(self):
        """Clean up test environment"""
        self.filter.stop_auto_update()
        os.unlink(self.temp_config.name)
        os.unlink(self.temp_log.name)
        
        # Clean up news data file if created
        news_file = self.temp_log.name.replace('.log', '_events.json')
        if os.path.exists(news_file):
            os.unlink(news_file)

class TestBasicFunctionality(TestNewsFilter):
    """Test basic news filter functionality"""
    
    def test_initialization(self):
        """Test news filter initialization"""
        self.assertTrue(self.filter.config.enabled)
        self.assertTrue(self.filter.config.impact_filters["high"])
        self.assertFalse(self.filter.config.impact_filters["medium"])
        self.assertEqual(self.filter.config.time_buffers["high"], 30)
        
    def test_news_event_creation(self):
        """Test news event object creation"""
        event_time = datetime.now() + timedelta(hours=1)
        event = NewsEvent(
            event_id="test_001",
            title="Non-Farm Payrolls",
            currency="USD",
            impact=NewsImpact.HIGH,
            event_time=event_time,
            forecast="200K",
            source="test"
        )
        
        self.assertEqual(event.event_id, "test_001")
        self.assertEqual(event.currency, "USD")
        self.assertEqual(event.impact, NewsImpact.HIGH)
        self.assertEqual(event.forecast, "200K")
        
        # Test serialization
        event_dict = event.to_dict()
        self.assertIn("event_id", event_dict)
        self.assertEqual(event_dict["impact"], "high")
        
    def test_symbol_mappings(self):
        """Test currency to symbol mappings"""
        usd_symbols = self.filter._get_affected_symbols("USD")
        self.assertIn("EURUSD", usd_symbols)
        self.assertIn("GBPUSD", usd_symbols)
        self.assertIn("USDJPY", usd_symbols)
        
        eur_symbols = self.filter._get_affected_symbols("EUR")
        self.assertIn("EURUSD", eur_symbols)
        self.assertIn("EURGBP", eur_symbols)
        
        # Test unknown currency
        unknown_symbols = self.filter._get_affected_symbols("XYZ")
        self.assertEqual(len(unknown_symbols), 0)

class TestNewsEventFiltering(TestNewsFilter):
    """Test news event filtering logic"""
    
    def test_is_news_active_within_buffer(self):
        """Test news activity detection within time buffer"""
        now = datetime.now()
        
        # High impact event 15 minutes from now (buffer = 30 minutes)
        event = NewsEvent(
            event_id="test_001",
            title="Test Event",
            currency="USD",
            impact=NewsImpact.HIGH,
            event_time=now + timedelta(minutes=15)
        )
        
        # Should be active (within 30-minute buffer)
        self.assertTrue(self.filter._is_news_active(event, now))
        
        # Event 45 minutes from now (outside buffer)
        event_future = NewsEvent(
            event_id="test_002",
            title="Future Event",
            currency="USD",
            impact=NewsImpact.HIGH,
            event_time=now + timedelta(minutes=45)
        )
        
        # Should not be active (outside 30-minute buffer)
        self.assertFalse(self.filter._is_news_active(event_future, now))
        
    def test_is_news_active_impact_filtering(self):
        """Test impact level filtering"""
        now = datetime.now()
        
        # Medium impact event within buffer but not filtered
        medium_event = NewsEvent(
            event_id="test_003",
            title="Medium Event",
            currency="USD",
            impact=NewsImpact.MEDIUM,
            event_time=now + timedelta(minutes=10)
        )
        
        # Should not be active (medium impact not filtered)
        self.assertFalse(self.filter._is_news_active(medium_event, now))
        
        # High impact event within buffer and filtered
        high_event = NewsEvent(
            event_id="test_004",
            title="High Event",
            currency="USD",
            impact=NewsImpact.HIGH,
            event_time=now + timedelta(minutes=10)
        )
        
        # Should be active (high impact is filtered)
        self.assertTrue(self.filter._is_news_active(high_event, now))

class TestSymbolFiltering(TestNewsFilter):
    """Test symbol-specific filtering"""
    
    def test_check_symbol_filter_allowed(self):
        """Test symbol filtering when no news is active"""
        # No active news events
        result = self.filter.check_symbol_filter("EURUSD")
        
        self.assertEqual(result.status, FilterStatus.ALLOWED)
        self.assertEqual(len(result.news_events), 0)
        self.assertIn("No active news", result.reason)
        
    def test_check_symbol_filter_blocked(self):
        """Test symbol filtering when news is active"""
        now = datetime.now()
        
        # Add active USD news event
        usd_event = NewsEvent(
            event_id="test_005",
            title="USD News",
            currency="USD",
            impact=NewsImpact.HIGH,
            event_time=now + timedelta(minutes=15)
        )
        self.filter.news_events = [usd_event]
        
        # Test USD pair - should be blocked
        result = self.filter.check_symbol_filter("EURUSD", now)
        
        self.assertEqual(result.status, FilterStatus.BLOCKED_NEWS)
        self.assertEqual(len(result.news_events), 1)
        self.assertIn("active news event", result.reason)
        self.assertIsNotNone(result.next_clear_time)
        
        # Test non-USD pair - should be allowed
        result_unaffected = self.filter.check_symbol_filter("EURGBP", now)
        self.assertEqual(result_unaffected.status, FilterStatus.ALLOWED)
        
    def test_check_symbol_filter_disabled(self):
        """Test symbol filtering when disabled"""
        # Disable filtering
        self.filter.config.enabled = False
        
        # Add active news event
        now = datetime.now()
        event = NewsEvent(
            event_id="test_006",
            title="Test Event",
            currency="USD",
            impact=NewsImpact.HIGH,
            event_time=now
        )
        self.filter.news_events = [event]
        
        # Should be allowed despite active news
        result = self.filter.check_symbol_filter("EURUSD", now)
        self.assertEqual(result.status, FilterStatus.ALLOWED)
        self.assertIn("disabled", result.reason)

class TestManualOverride(TestNewsFilter):
    """Test manual override functionality"""
    
    def test_enable_manual_override(self):
        """Test enabling manual override"""
        success = self.filter.enable_manual_override(30)
        
        self.assertTrue(success)
        self.assertTrue(self.filter.manual_override_active)
        self.assertIsNotNone(self.filter.override_expires)
        
        # Should be approximately 30 minutes from now
        expected_expiry = datetime.now() + timedelta(minutes=30)
        time_diff = abs((self.filter.override_expires - expected_expiry).total_seconds())
        self.assertLess(time_diff, 5)  # Within 5 seconds
        
    def test_manual_override_filtering(self):
        """Test filtering behavior with manual override"""
        now = datetime.now()
        
        # Add active news event
        event = NewsEvent(
            event_id="test_007",
            title="Override Test",
            currency="USD",
            impact=NewsImpact.HIGH,
            event_time=now
        )
        self.filter.news_events = [event]
        
        # Without override - should be blocked
        result = self.filter.check_symbol_filter("EURUSD", now)
        self.assertEqual(result.status, FilterStatus.BLOCKED_NEWS)
        
        # Enable override
        self.filter.enable_manual_override(60)
        
        # With override - should be allowed
        result_override = self.filter.check_symbol_filter("EURUSD", now)
        self.assertEqual(result_override.status, FilterStatus.OVERRIDE_ACTIVE)
        self.assertIn("override", result_override.reason)
        
    def test_disable_manual_override(self):
        """Test disabling manual override"""
        # Enable first
        self.filter.enable_manual_override(30)
        self.assertTrue(self.filter.manual_override_active)
        
        # Disable
        success = self.filter.disable_manual_override()
        
        self.assertTrue(success)
        self.assertFalse(self.filter.manual_override_active)
        self.assertIsNone(self.filter.override_expires)

class TestManualBlock(TestNewsFilter):
    """Test manual block functionality"""
    
    def test_enable_manual_block(self):
        """Test enabling manual block"""
        success = self.filter.enable_manual_block(45)
        
        self.assertTrue(success)
        self.assertTrue(self.filter.manual_block_active)
        self.assertIsNotNone(self.filter.manual_block_expires)
        
    def test_manual_block_filtering(self):
        """Test filtering behavior with manual block"""
        now = datetime.now()
        
        # No active news - normally allowed
        result = self.filter.check_symbol_filter("EURUSD", now)
        self.assertEqual(result.status, FilterStatus.ALLOWED)
        
        # Enable manual block
        self.filter.enable_manual_block(30)
        
        # Should now be blocked
        result_blocked = self.filter.check_symbol_filter("EURUSD", now)
        self.assertEqual(result_blocked.status, FilterStatus.BLOCKED_MANUAL)
        self.assertIn("Manual block", result_blocked.reason)
        
    def test_manual_block_overrides_override(self):
        """Test that manual block overrides manual override"""
        # Enable override first
        self.filter.enable_manual_override(60)
        self.assertTrue(self.filter.manual_override_active)
        
        # Enable block - should disable override
        self.filter.enable_manual_block(30)
        
        self.assertTrue(self.filter.manual_block_active)
        self.assertFalse(self.filter.manual_override_active)

class TestNewsDataHandling(TestNewsFilter):
    """Test news data fetching and storage"""
    
    def test_mock_news_generation(self):
        """Test mock news data generation"""
        mock_events = self.filter._fetch_mock_news_data()
        
        self.assertGreater(len(mock_events), 0)
        
        for event in mock_events:
            self.assertIsInstance(event, NewsEvent)
            self.assertIn(event.impact, [NewsImpact.LOW, NewsImpact.MEDIUM, NewsImpact.HIGH])
            self.assertGreater(event.event_time, datetime.now())
            self.assertEqual(event.source, "mock")
            
    def test_news_data_persistence(self):
        """Test news data persistence to file"""
        # Add some test events
        now = datetime.now()
        events = [
            NewsEvent(
                event_id="persist_001",
                title="Test Persistence",
                currency="USD",
                impact=NewsImpact.HIGH,
                event_time=now + timedelta(hours=1)
            ),
            NewsEvent(
                event_id="persist_002",
                title="Another Test",
                currency="EUR",
                impact=NewsImpact.MEDIUM,
                event_time=now + timedelta(hours=2)
            )
        ]
        
        self.filter.news_events = events
        self.filter.last_update = now
        
        # Save data
        self.filter._save_news_data()
        
        # Create new filter instance and load
        new_filter = NewsFilter(
            config_path=self.temp_config.name,
            log_path=self.temp_log.name
        )
        
        # Check events were loaded
        self.assertEqual(len(new_filter.news_events), 2)
        self.assertEqual(new_filter.news_events[0].event_id, "persist_001")
        self.assertEqual(new_filter.news_events[1].currency, "EUR")
        
    @patch('requests.get')
    def test_forex_factory_fetch_success(self, mock_get):
        """Test successful Forex Factory data fetch"""
        # Mock successful response
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = [
            {
                "id": "12345",
                "title": "Non-Farm Payrolls",
                "currency": "USD",
                "date": "2023-12-01",
                "time": "13:30",
                "impact": "high",
                "forecast": "200K",
                "previous": "190K"
            }
        ]
        mock_get.return_value = mock_response
        
        events = self.filter._fetch_forex_factory_news()
        
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].title, "Non-Farm Payrolls")
        self.assertEqual(events[0].currency, "USD")
        self.assertEqual(events[0].impact, NewsImpact.HIGH)
        self.assertEqual(events[0].source, "forexfactory")
        
    @patch('requests.get')
    def test_forex_factory_fetch_failure(self, mock_get):
        """Test Forex Factory fetch failure handling"""
        # Mock failed response
        mock_get.side_effect = Exception("Network error")
        
        events = self.filter._fetch_forex_factory_news()
        
        self.assertEqual(len(events), 0)

class TestAsyncOperations(TestNewsFilter):
    """Test async operations"""
    
    def test_update_news_data(self):
        """Test news data update"""
        async def run_test():
            # Mock the fetch method to return test data
            original_fetch = self.filter._fetch_mock_news_data
            
            def mock_fetch():
                return [
                    NewsEvent(
                        event_id="async_001",
                        title="Async Test",
                        currency="USD",
                        impact=NewsImpact.HIGH,
                        event_time=datetime.now() + timedelta(hours=1)
                    )
                ]
            
            self.filter._fetch_mock_news_data = mock_fetch
            
            # Update data
            success = await self.filter.update_news_data(force_update=True)
            
            self.assertTrue(success)
            self.assertEqual(len(self.filter.news_events), 1)
            self.assertEqual(self.filter.news_events[0].event_id, "async_001")
            self.assertIsNotNone(self.filter.last_update)
            
            # Restore original method
            self.filter._fetch_mock_news_data = original_fetch
            
        asyncio.run(run_test())

class TestUtilityFunctions(TestNewsFilter):
    """Test utility and status functions"""
    
    def test_get_upcoming_news(self):
        """Test getting upcoming news events"""
        now = datetime.now()
        
        # Add test events
        events = [
            NewsEvent(
                event_id="upcoming_001",
                title="Soon Event",
                currency="USD",
                impact=NewsImpact.HIGH,
                event_time=now + timedelta(hours=1)
            ),
            NewsEvent(
                event_id="upcoming_002",
                title="Later Event",
                currency="EUR",
                impact=NewsImpact.MEDIUM,
                event_time=now + timedelta(hours=6)
            ),
            NewsEvent(
                event_id="upcoming_003",
                title="Much Later Event",
                currency="GBP",
                impact=NewsImpact.HIGH,
                event_time=now + timedelta(hours=30)  # Outside 24 hour window
            )
        ]
        
        self.filter.news_events = events
        
        # Get upcoming events (24 hours)
        upcoming = self.filter.get_upcoming_news(24)
        
        self.assertEqual(len(upcoming), 2)  # Third event is outside window
        self.assertEqual(upcoming[0].event_id, "upcoming_001")  # Should be sorted by time
        
        # Test with impact filter
        upcoming_high = self.filter.get_upcoming_news(24, ["high"])
        self.assertEqual(len(upcoming_high), 1)
        self.assertEqual(upcoming_high[0].impact, NewsImpact.HIGH)
        
    def test_get_current_news_status(self):
        """Test getting current news status"""
        now = datetime.now()
        
        # Add mix of active and inactive events
        events = [
            NewsEvent(
                event_id="status_001",
                title="Active High",
                currency="USD",
                impact=NewsImpact.HIGH,
                event_time=now + timedelta(minutes=10)  # Active (within 30min buffer)
            ),
            NewsEvent(
                event_id="status_002",
                title="Inactive Low",
                currency="EUR",
                impact=NewsImpact.LOW,
                event_time=now + timedelta(minutes=10)  # Would be active but low impact not filtered
            ),
            NewsEvent(
                event_id="status_003",
                title="Inactive Future",
                currency="GBP",
                impact=NewsImpact.HIGH,
                event_time=now + timedelta(hours=2)  # Inactive (outside buffer)
            )
        ]
        
        self.filter.news_events = events
        
        status = self.filter.get_current_news_status()
        
        self.assertTrue(status["enabled"])
        self.assertEqual(status["total_events_loaded"], 3)
        self.assertEqual(status["active_events"], 1)  # Only one high impact active
        self.assertEqual(status["active_by_impact"]["high"], 1)
        self.assertEqual(status["active_by_impact"]["low"], 0)
        self.assertFalse(status["manual_override_active"])
        self.assertFalse(status["manual_block_active"])

if __name__ == '__main__':
    unittest.main()