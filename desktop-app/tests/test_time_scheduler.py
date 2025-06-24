"""
Tests for Time Scheduler module
"""

import pytest
import json
import tempfile
import os
from unittest.mock import patch, MagicMock
from datetime import datetime, time, timezone
from desktop_app.time_scheduler import TimeScheduler, TimeWindow, ScheduleRule, TimeFilterResult, should_execute_trade


class TestTimeScheduler:
    
    def setup_method(self):
        """Setup test environment"""
        self.temp_config = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        self.temp_log = tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False)
        
        # Create test config
        test_config = {
            'time_scheduler': {
                'enabled': True,
                'default_timezone': 'UTC',
                'log_filtering_actions': True,
                'rules': {
                    'GOLD': {
                        'start': '08:30',
                        'end': '15:00',
                        'timezone': 'UTC',
                        'weekdays': [0, 1, 2, 3, 4]  # Monday to Friday
                    },
                    'EURUSD': {
                        'start': '07:00',
                        'end': '17:00',
                        'timezone': 'UTC',
                        'weekdays': [0, 1, 2, 3, 4]
                    },
                    'default': {
                        'start': '00:00',
                        'end': '23:59',
                        'timezone': 'UTC',
                        'weekdays': [0, 1, 2, 3, 4, 5, 6]  # All days
                    }
                }
            }
        }
        
        json.dump(test_config, self.temp_config)
        self.temp_config.close()
        self.temp_log.close()
        
        self.scheduler = TimeScheduler(
            config_file=self.temp_config.name,
            log_file=self.temp_log.name
        )
    
    def teardown_method(self):
        """Cleanup test files"""
        os.unlink(self.temp_config.name)
        os.unlink(self.temp_log.name)
    
    def test_time_window_contains_time(self):
        """Test TimeWindow time containment logic"""
        # Normal window (8:30 to 15:00)
        window = TimeWindow(time(8, 30), time(15, 0), "UTC")
        
        # Test times within window
        test_time_inside = datetime(2023, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
        assert window.contains_time(test_time_inside, "UTC") == True
        
        # Test times outside window
        test_time_outside = datetime(2023, 6, 15, 16, 0, 0, tzinfo=timezone.utc)
        assert window.contains_time(test_time_outside, "UTC") == False
        
        # Test overnight window (22:00 to 06:00)
        overnight_window = TimeWindow(time(22, 0), time(6, 0), "UTC")
        
        test_time_night = datetime(2023, 6, 15, 23, 0, 0, tzinfo=timezone.utc)
        assert overnight_window.contains_time(test_time_night, "UTC") == True
        
        test_time_early = datetime(2023, 6, 16, 5, 0, 0, tzinfo=timezone.utc)
        assert overnight_window.contains_time(test_time_early, "UTC") == True
        
        test_time_middle = datetime(2023, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
        assert overnight_window.contains_time(test_time_middle, "UTC") == False
    
    def test_should_execute_trade_time_window(self):
        """Test trade execution based on time windows"""
        # GOLD trading window: 08:30-15:00 UTC, weekdays only
        
        # Test within allowed window (Friday 12:00 UTC)
        friday_noon = datetime(2023, 6, 16, 12, 0, 0, tzinfo=timezone.utc)  # Friday
        should_execute, result, reason = self.scheduler.should_execute_trade(friday_noon, "GOLD")
        
        assert should_execute == True
        assert result == TimeFilterResult.ALLOWED
        assert "allowed" in reason.lower()
        
        # Test outside time window (Friday 16:00 UTC)
        friday_evening = datetime(2023, 6, 16, 16, 0, 0, tzinfo=timezone.utc)  # Friday
        should_execute, result, reason = self.scheduler.should_execute_trade(friday_evening, "GOLD")
        
        assert should_execute == False
        assert result == TimeFilterResult.BLOCKED_TIME_WINDOW
        assert "outside allowed time" in reason.lower()
    
    def test_should_execute_trade_weekday(self):
        """Test trade execution based on weekday restrictions"""
        # GOLD is allowed Monday-Friday only
        
        # Test on weekend (Saturday 12:00 UTC)
        saturday_noon = datetime(2023, 6, 17, 12, 0, 0, tzinfo=timezone.utc)  # Saturday
        should_execute, result, reason = self.scheduler.should_execute_trade(saturday_noon, "GOLD")
        
        assert should_execute == False
        assert result == TimeFilterResult.BLOCKED_WEEKDAY
        assert "not allowed on" in reason.lower()
        
        # Test on Sunday
        sunday_noon = datetime(2023, 6, 18, 12, 0, 0, tzinfo=timezone.utc)  # Sunday
        should_execute, result, reason = self.scheduler.should_execute_trade(sunday_noon, "GOLD")
        
        assert should_execute == False
        assert result == TimeFilterResult.BLOCKED_WEEKDAY
    
    def test_pattern_matching(self):
        """Test symbol pattern matching"""
        # Test exact match
        assert self.scheduler._match_symbol_pattern("EURUSD", "EURUSD") == True
        assert self.scheduler._match_symbol_pattern("GBPUSD", "EURUSD") == False
        
        # Test wildcard patterns
        assert self.scheduler._match_symbol_pattern("EURUSD", "EUR*") == True
        assert self.scheduler._match_symbol_pattern("EURJPY", "EUR*") == True
        assert self.scheduler._match_symbol_pattern("GBPUSD", "EUR*") == False
        
        assert self.scheduler._match_symbol_pattern("XAUUSD", "*USD") == True
        assert self.scheduler._match_symbol_pattern("EURJPY", "*USD") == False
        
        # Test default pattern
        assert self.scheduler._match_symbol_pattern("ANYSYMBOL", "DEFAULT") == True
    
    def test_rule_priority(self):
        """Test rule priority system"""
        # Add high priority rule for EURUSD
        high_priority_rule = ScheduleRule(
            symbol_pattern="EURUSD",
            time_windows=[TimeWindow(time(1, 0), time(2, 0), "UTC")],  # Very restrictive
            allowed_weekdays=[1],  # Only Tuesday
            priority=100
        )
        
        self.scheduler.schedule_rules.append(high_priority_rule)
        self.scheduler.schedule_rules.sort(key=lambda r: r.priority, reverse=True)
        
        # Test on Tuesday within high priority window
        tuesday_window = datetime(2023, 6, 13, 1, 30, 0, tzinfo=timezone.utc)  # Tuesday 01:30
        should_execute, result, reason = self.scheduler.should_execute_trade(tuesday_window, "EURUSD")
        
        assert should_execute == True  # High priority rule should take precedence
        
        # Test on Tuesday outside high priority window
        tuesday_outside = datetime(2023, 6, 13, 10, 0, 0, tzinfo=timezone.utc)  # Tuesday 10:00
        should_execute, result, reason = self.scheduler.should_execute_trade(tuesday_outside, "EURUSD")
        
        assert should_execute == False  # High priority rule blocks it
    
    def test_add_remove_time_rule(self):
        """Test dynamic rule management"""
        initial_rule_count = len(self.scheduler.schedule_rules)
        
        # Add new rule
        success = self.scheduler.add_time_rule(
            symbol_pattern="BTCUSD",
            start_time="09:00",
            end_time="16:00",
            weekdays=[0, 1, 2, 3, 4],
            timezone="UTC",
            priority=10
        )
        
        assert success == True
        assert len(self.scheduler.schedule_rules) == initial_rule_count + 1
        
        # Test the new rule works
        monday_crypto = datetime(2023, 6, 12, 12, 0, 0, tzinfo=timezone.utc)  # Monday 12:00
        should_execute, result, reason = self.scheduler.should_execute_trade(monday_crypto, "BTCUSD")
        assert should_execute == True
        
        # Remove the rule
        removed = self.scheduler.remove_time_rule("BTCUSD")
        assert removed == True
        assert len(self.scheduler.schedule_rules) == initial_rule_count
    
    def test_disabled_scheduler(self):
        """Test scheduler when disabled"""
        self.scheduler.config['enabled'] = False
        
        # Any time should be allowed when disabled
        any_time = datetime(2023, 6, 18, 23, 59, 0, tzinfo=timezone.utc)  # Sunday night
        should_execute, result, reason = self.scheduler.should_execute_trade(any_time, "GOLD")
        
        assert should_execute == True
        assert result == TimeFilterResult.ALLOWED
        assert "disabled" in reason.lower()
    
    def test_provider_pattern_matching(self):
        """Test provider-specific rules"""
        # Add provider-specific rule
        provider_rule = ScheduleRule(
            symbol_pattern="default",
            provider_pattern="TEST_PROVIDER",
            time_windows=[TimeWindow(time(10, 0), time(14, 0), "UTC")],
            allowed_weekdays=[0, 1, 2, 3, 4],
            priority=50
        )
        
        self.scheduler.schedule_rules.append(provider_rule)
        self.scheduler.schedule_rules.sort(key=lambda r: r.priority, reverse=True)
        
        # Test with matching provider
        weekday_time = datetime(2023, 6, 15, 12, 0, 0, tzinfo=timezone.utc)  # Thursday 12:00
        should_execute, result, reason = self.scheduler.should_execute_trade(
            weekday_time, "ANYSYMBOL", "TEST_PROVIDER"
        )
        assert should_execute == True
        
        # Test with non-matching provider (should fall back to default rules)
        should_execute, result, reason = self.scheduler.should_execute_trade(
            weekday_time, "ANYSYMBOL", "OTHER_PROVIDER"
        )
        assert should_execute == True  # Default rule allows 24/7
    
    def test_get_time_statistics(self):
        """Test time filtering statistics"""
        # Generate some test filtering actions
        test_times = [
            (datetime(2023, 6, 15, 12, 0, 0, tzinfo=timezone.utc), "GOLD", None),  # Should be allowed
            (datetime(2023, 6, 15, 16, 0, 0, tzinfo=timezone.utc), "GOLD", None),  # Should be blocked (time)
            (datetime(2023, 6, 17, 12, 0, 0, tzinfo=timezone.utc), "GOLD", None),  # Should be blocked (weekend)
        ]
        
        for test_time, symbol, provider in test_times:
            self.scheduler.should_execute_trade(test_time, symbol, provider)
        
        stats = self.scheduler.get_time_statistics()
        
        assert 'total_checks' in stats
        assert 'allowed_trades' in stats
        assert 'blocked_trades' in stats
        assert 'block_reasons' in stats
        assert stats['total_checks'] >= 3
    
    def test_list_active_rules(self):
        """Test listing active rules"""
        active_rules = self.scheduler.list_active_rules()
        
        assert isinstance(active_rules, list)
        assert len(active_rules) >= 3  # Should have GOLD, EURUSD, and default rules
        
        # Check rule structure
        for rule in active_rules:
            assert 'symbol_pattern' in rule
            assert 'time_windows' in rule
            assert 'weekdays' in rule
            assert 'priority' in rule
            
            # Check time window structure
            for window in rule['time_windows']:
                assert 'start' in window
                assert 'end' in window
                assert 'timezone' in window
    
    def test_convenience_function(self):
        """Test global convenience function"""
        # Test allowed trade
        friday_noon = datetime(2023, 6, 16, 12, 0, 0, tzinfo=timezone.utc)
        allowed = should_execute_trade(friday_noon, "GOLD")
        assert allowed == True
        
        # Test blocked trade
        friday_evening = datetime(2023, 6, 16, 16, 0, 0, tzinfo=timezone.utc)
        blocked = should_execute_trade(friday_evening, "GOLD")
        assert blocked == False
    
    def test_module_injection(self):
        """Test module injection"""
        mock_strategy_runtime = MagicMock()
        mock_parser = MagicMock()
        
        self.scheduler.inject_modules(
            strategy_runtime=mock_strategy_runtime,
            parser=mock_parser
        )
        
        assert self.scheduler.strategy_runtime == mock_strategy_runtime
        assert self.scheduler.parser == mock_parser
    
    def test_edge_case_times(self):
        """Test edge cases for time validation"""
        # Test exactly at window boundaries
        gold_start = datetime(2023, 6, 15, 8, 30, 0, tzinfo=timezone.utc)  # Exactly 08:30
        should_execute, result, reason = self.scheduler.should_execute_trade(gold_start, "GOLD")
        assert should_execute == True
        
        gold_end = datetime(2023, 6, 15, 15, 0, 0, tzinfo=timezone.utc)  # Exactly 15:00
        should_execute, result, reason = self.scheduler.should_execute_trade(gold_end, "GOLD")
        assert should_execute == True
        
        # Test one minute after end
        gold_after = datetime(2023, 6, 15, 15, 1, 0, tzinfo=timezone.utc)  # 15:01
        should_execute, result, reason = self.scheduler.should_execute_trade(gold_after, "GOLD")
        assert should_execute == False
    
    def test_unknown_symbol_fallback(self):
        """Test fallback to default rules for unknown symbols"""
        # Test unknown symbol on weekday
        unknown_weekday = datetime(2023, 6, 15, 12, 0, 0, tzinfo=timezone.utc)  # Thursday
        should_execute, result, reason = self.scheduler.should_execute_trade(unknown_weekday, "UNKNOWN_SYMBOL")
        assert should_execute == True  # Default rule allows 24/7 on weekdays
        
        # Test unknown symbol on weekend (default allows weekends)
        unknown_weekend = datetime(2023, 6, 17, 12, 0, 0, tzinfo=timezone.utc)  # Saturday
        should_execute, result, reason = self.scheduler.should_execute_trade(unknown_weekend, "UNKNOWN_SYMBOL")
        assert should_execute == True  # Default rule allows weekends


if __name__ == "__main__":
    pytest.main([__file__])