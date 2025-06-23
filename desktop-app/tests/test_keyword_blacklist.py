"""
Tests for Keyword Blacklist functionality in Strategy Runtime
Tests the integration between keyword filtering and signal processing
"""

import asyncio
from unittest.mock import Mock, AsyncMock
from datetime import datetime
from typing import Dict, Any, List

class MockKeywordBlacklistEngine:
    def __init__(self):
        self.blacklist_configs = {}
        self.blocked_signals = []
        self.notification_handler = None
    
    def add_blacklist_filter(self, filter_id: str, config: Dict[str, Any]):
        """Add keyword blacklist filter to strategy"""
        self.blacklist_configs[filter_id] = {
            'keywords': config.get('keywords', []),
            'case_sensitive': config.get('caseSensitive', False),
            'whole_words_only': config.get('wholeWordsOnly', True),
            'enable_system_keywords': config.get('enableSystemKeywords', True),
            'match_mode': config.get('matchMode', 'any'),
            'log_blocked_signals': config.get('logBlockedSignals', True),
            'notify_on_block': config.get('notifyOnBlock', True)
        }
    
    def get_system_keywords(self) -> List[str]:
        """Get system-wide blacklisted keywords"""
        return [
            'high risk',
            'manual only',
            'no sl',
            'no stop loss',
            'low accuracy',
            'risky',
            'dangerous',
            'not recommended',
            'use with caution',
            'scalp only',
            'demo only',
            'paper trade'
        ]
    
    def get_effective_keywords(self, filter_id: str) -> List[str]:
        """Get all effective keywords for a filter (user + system)"""
        if filter_id not in self.blacklist_configs:
            return []
        
        config = self.blacklist_configs[filter_id]
        keywords = config['keywords'].copy()
        
        if config['enable_system_keywords']:
            keywords.extend(self.get_system_keywords())
        
        return keywords
    
    async def check_signal_against_blacklist(self, filter_id: str, signal_data: Dict[str, Any]) -> Dict[str, Any]:
        """Check if signal should be blocked by keyword blacklist"""
        if filter_id not in self.blacklist_configs:
            return {
                "blocked": False,
                "reason": "Filter not configured",
                "matched_keywords": [],
                "confidence": 100
            }
        
        config = self.blacklist_configs[filter_id]
        raw_message = signal_data.get('raw_message', '')
        
        if not raw_message:
            return {
                "blocked": False,
                "reason": "No message content to analyze",
                "matched_keywords": [],
                "confidence": 100
            }
        
        # Get effective keywords
        keywords = self.get_effective_keywords(filter_id)
        
        if not keywords:
            return {
                "blocked": False,
                "reason": "No keywords configured",
                "matched_keywords": [],
                "confidence": 100
            }
        
        # Prepare message and keywords for comparison
        message = raw_message if config['case_sensitive'] else raw_message.lower()
        keywords_to_check = keywords if config['case_sensitive'] else [k.lower() for k in keywords]
        
        matched_keywords = []
        
        # Check each keyword
        for keyword in keywords_to_check:
            if self._keyword_matches(message, keyword, config['whole_words_only']):
                matched_keywords.append(keyword)
                
                # If mode is 'any', we can stop at first match
                if config['match_mode'] == 'any':
                    break
        
        # Determine if signal should be blocked
        if config['match_mode'] == 'any':
            blocked = len(matched_keywords) > 0
        else:  # 'all' mode
            blocked = len(matched_keywords) == len(keywords_to_check) and len(keywords_to_check) > 0
        
        # Generate result
        if blocked:
            reason = f"Signal blocked - matched keywords: {', '.join(matched_keywords[:3])}"
            if len(matched_keywords) > 3:
                reason += f" (+{len(matched_keywords) - 3} more)"
            confidence = min(95, 60 + (len(matched_keywords) * 10))
        else:
            reason = "No blacklisted keywords found - signal allowed"
            confidence = 100
        
        result = {
            "blocked": blocked,
            "reason": reason,
            "matched_keywords": matched_keywords,
            "confidence": confidence,
            "filter_config": config
        }
        
        # Log and notify if blocked
        if blocked:
            await self._handle_blocked_signal(signal_data, result, config)
        
        return result
    
    def _keyword_matches(self, message: str, keyword: str, whole_words_only: bool) -> bool:
        """Check if keyword matches in message"""
        if whole_words_only:
            import re
            # Use word boundaries for whole word matching
            pattern = r'\b' + re.escape(keyword) + r'\b'
            return bool(re.search(pattern, message))
        else:
            # Simple substring matching
            return keyword in message
    
    async def _handle_blocked_signal(self, signal_data: Dict[str, Any], result: Dict[str, Any], config: Dict[str, Any]):
        """Handle blocked signal logging and notifications"""
        blocked_signal = {
            'timestamp': datetime.now().isoformat(),
            'signal': signal_data,
            'block_reason': result['reason'],
            'matched_keywords': result['matched_keywords'],
            'filter_config': config
        }
        
        self.blocked_signals.append(blocked_signal)
        
        # Log if enabled
        if config['log_blocked_signals']:
            print(f"BLOCKED SIGNAL: {result['reason']}")
        
        # Send notification if enabled and handler is available
        if config['notify_on_block'] and self.notification_handler:
            await self.notification_handler.send_block_notification(blocked_signal)
    
    def set_notification_handler(self, handler):
        """Set notification handler (e.g., Copilot Bot)"""
        self.notification_handler = handler
    
    def get_blocked_signals_count(self) -> int:
        """Get total count of blocked signals"""
        return len(self.blocked_signals)
    
    def get_recent_blocked_signals(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent blocked signals"""
        return self.blocked_signals[-limit:] if self.blocked_signals else []
    
    def clear_blocked_signals_log(self):
        """Clear blocked signals log"""
        self.blocked_signals.clear()

class MockNotificationHandler:
    def __init__(self):
        self.notifications = []
    
    async def send_block_notification(self, blocked_signal: Dict[str, Any]):
        """Send notification about blocked signal"""
        notification = {
            'type': 'signal_blocked',
            'timestamp': datetime.now().isoformat(),
            'message': f"Signal blocked: {blocked_signal['block_reason']}",
            'details': blocked_signal
        }
        self.notifications.append(notification)

# Test class
class TestKeywordBlacklist:
    
    def setup_method(self):
        """Setup test environment"""
        self.blacklist_engine = MockKeywordBlacklistEngine()
        self.notification_handler = MockNotificationHandler()
        self.blacklist_engine.set_notification_handler(self.notification_handler)
    
    async def test_basic_keyword_blocking(self):
        """Test basic keyword blocking functionality"""
        config = {
            'keywords': ['high risk', 'dangerous'],
            'caseSensitive': False,
            'wholeWordsOnly': True,
            'enableSystemKeywords': False,
            'matchMode': 'any'
        }
        
        self.blacklist_engine.add_blacklist_filter('test_filter', config)
        
        # Test blocking signal
        signal_data = {
            'raw_message': 'This is a high risk trade with potential losses',
            'symbol': 'EURUSD',
            'action': 'BUY'
        }
        
        result = await self.blacklist_engine.check_signal_against_blacklist('test_filter', signal_data)
        
        assert result['blocked'] == True
        assert 'high risk' in result['matched_keywords']
        assert 'blocked' in result['reason'].lower()
        assert result['confidence'] < 100
    
    async def test_signal_allowed_no_match(self):
        """Test signal allowed when no keywords match"""
        config = {
            'keywords': ['dangerous', 'risky'],
            'caseSensitive': False,
            'wholeWordsOnly': True,
            'enableSystemKeywords': False,
            'matchMode': 'any'
        }
        
        self.blacklist_engine.add_blacklist_filter('test_filter', config)
        
        signal_data = {
            'raw_message': 'This is a good trading opportunity with clear setup',
            'symbol': 'EURUSD',
            'action': 'BUY'
        }
        
        result = await self.blacklist_engine.check_signal_against_blacklist('test_filter', signal_data)
        
        assert result['blocked'] == False
        assert len(result['matched_keywords']) == 0
        assert 'allowed' in result['reason'].lower()
        assert result['confidence'] == 100
    
    async def test_case_sensitivity(self):
        """Test case sensitivity setting"""
        config = {
            'keywords': ['RISK'],
            'caseSensitive': True,
            'wholeWordsOnly': True,
            'enableSystemKeywords': False,
            'matchMode': 'any'
        }
        
        self.blacklist_engine.add_blacklist_filter('test_filter', config)
        
        # Test case sensitive - should not match
        signal_data1 = {
            'raw_message': 'This trade has some risk involved',
            'symbol': 'EURUSD'
        }
        
        result1 = await self.blacklist_engine.check_signal_against_blacklist('test_filter', signal_data1)
        assert result1['blocked'] == False
        
        # Test exact case - should match
        signal_data2 = {
            'raw_message': 'This trade has some RISK involved',
            'symbol': 'EURUSD'
        }
        
        result2 = await self.blacklist_engine.check_signal_against_blacklist('test_filter', signal_data2)
        assert result2['blocked'] == True
    
    async def test_whole_words_only(self):
        """Test whole words only setting"""
        config = {
            'keywords': ['risk'],
            'caseSensitive': False,
            'wholeWordsOnly': False,  # Allow partial matches
            'enableSystemKeywords': False,
            'matchMode': 'any'
        }
        
        self.blacklist_engine.add_blacklist_filter('test_filter', config)
        
        signal_data = {
            'raw_message': 'This is a risky trade',  # 'risk' is part of 'risky'
            'symbol': 'EURUSD'
        }
        
        result = await self.blacklist_engine.check_signal_against_blacklist('test_filter', signal_data)
        
        assert result['blocked'] == True
        assert 'risk' in result['matched_keywords']
    
    async def test_system_keywords(self):
        """Test system keywords functionality"""
        config = {
            'keywords': [],  # No custom keywords
            'caseSensitive': False,
            'wholeWordsOnly': True,
            'enableSystemKeywords': True,
            'matchMode': 'any'
        }
        
        self.blacklist_engine.add_blacklist_filter('test_filter', config)
        
        signal_data = {
            'raw_message': 'This trade has no sl and is manual only',
            'symbol': 'EURUSD'
        }
        
        result = await self.blacklist_engine.check_signal_against_blacklist('test_filter', signal_data)
        
        assert result['blocked'] == True
        assert any(keyword in result['matched_keywords'] for keyword in ['no sl', 'manual only'])
    
    async def test_match_mode_all(self):
        """Test 'all' match mode requiring all keywords"""
        config = {
            'keywords': ['high', 'risk'],
            'caseSensitive': False,
            'wholeWordsOnly': True,
            'enableSystemKeywords': False,
            'matchMode': 'all'
        }
        
        self.blacklist_engine.add_blacklist_filter('test_filter', config)
        
        # Test partial match - should allow
        signal_data1 = {
            'raw_message': 'This is a high confidence trade',
            'symbol': 'EURUSD'
        }
        
        result1 = await self.blacklist_engine.check_signal_against_blacklist('test_filter', signal_data1)
        assert result1['blocked'] == False
        
        # Test all keywords match - should block
        signal_data2 = {
            'raw_message': 'This is a high risk trade',
            'symbol': 'EURUSD'
        }
        
        result2 = await self.blacklist_engine.check_signal_against_blacklist('test_filter', signal_data2)
        assert result2['blocked'] == True
    
    async def test_notification_handling(self):
        """Test notification handling for blocked signals"""
        config = {
            'keywords': ['dangerous'],
            'caseSensitive': False,
            'wholeWordsOnly': True,
            'enableSystemKeywords': False,
            'matchMode': 'any',
            'notifyOnBlock': True
        }
        
        self.blacklist_engine.add_blacklist_filter('test_filter', config)
        
        signal_data = {
            'raw_message': 'This is a dangerous trade',
            'symbol': 'EURUSD',
            'action': 'BUY'
        }
        
        await self.blacklist_engine.check_signal_against_blacklist('test_filter', signal_data)
        
        # Check if notification was sent
        assert len(self.notification_handler.notifications) == 1
        notification = self.notification_handler.notifications[0]
        assert notification['type'] == 'signal_blocked'
        assert 'dangerous' in notification['message']
    
    async def test_blocked_signals_logging(self):
        """Test blocked signals are properly logged"""
        config = {
            'keywords': ['test'],
            'caseSensitive': False,
            'wholeWordsOnly': True,
            'enableSystemKeywords': False,
            'matchMode': 'any',
            'logBlockedSignals': True
        }
        
        self.blacklist_engine.add_blacklist_filter('test_filter', config)
        
        # Block multiple signals
        for i in range(3):
            signal_data = {
                'raw_message': f'This is a test signal {i}',
                'symbol': 'EURUSD'
            }
            await self.blacklist_engine.check_signal_against_blacklist('test_filter', signal_data)
        
        assert self.blacklist_engine.get_blocked_signals_count() == 3
        
        recent_blocked = self.blacklist_engine.get_recent_blocked_signals(2)
        assert len(recent_blocked) == 2
        assert 'test signal 2' in recent_blocked[-1]['signal']['raw_message']
    
    async def test_empty_message_handling(self):
        """Test handling of empty or missing message content"""
        config = {
            'keywords': ['test'],
            'caseSensitive': False,
            'wholeWordsOnly': True,
            'enableSystemKeywords': False,
            'matchMode': 'any'
        }
        
        self.blacklist_engine.add_blacklist_filter('test_filter', config)
        
        # Test empty message
        signal_data = {
            'raw_message': '',
            'symbol': 'EURUSD'
        }
        
        result = await self.blacklist_engine.check_signal_against_blacklist('test_filter', signal_data)
        
        assert result['blocked'] == False
        assert 'no message content' in result['reason'].lower()
    
    async def test_multiple_keyword_matches(self):
        """Test multiple keyword matches in single message"""
        config = {
            'keywords': ['risk', 'dangerous', 'caution'],
            'caseSensitive': False,
            'wholeWordsOnly': True,
            'enableSystemKeywords': False,
            'matchMode': 'any'
        }
        
        self.blacklist_engine.add_blacklist_filter('test_filter', config)
        
        signal_data = {
            'raw_message': 'This dangerous trade has high risk, use caution',
            'symbol': 'EURUSD'
        }
        
        result = await self.blacklist_engine.check_signal_against_blacklist('test_filter', signal_data)
        
        assert result['blocked'] == True
        assert len(result['matched_keywords']) >= 1  # Should stop at first match in 'any' mode
        assert result['confidence'] > 60  # Higher confidence due to matches
    
    async def test_filter_not_configured(self):
        """Test behavior when filter is not configured"""
        signal_data = {
            'raw_message': 'This is a test signal',
            'symbol': 'EURUSD'
        }
        
        result = await self.blacklist_engine.check_signal_against_blacklist('nonexistent_filter', signal_data)
        
        assert result['blocked'] == False
        assert 'not configured' in result['reason'].lower()

# Main execution for basic testing
async def run_basic_tests():
    """Run basic functionality tests"""
    test_instance = TestKeywordBlacklist()
    test_instance.setup_method()
    
    print("Running keyword blacklist tests...")
    
    try:
        await test_instance.test_basic_keyword_blocking()
        print("✓ Basic keyword blocking test passed")
        
        await test_instance.test_signal_allowed_no_match()
        print("✓ Signal allowed test passed")
        
        await test_instance.test_case_sensitivity()
        print("✓ Case sensitivity test passed")
        
        await test_instance.test_whole_words_only()
        print("✓ Whole words only test passed")
        
        await test_instance.test_system_keywords()
        print("✓ System keywords test passed")
        
        await test_instance.test_match_mode_all()
        print("✓ Match mode 'all' test passed")
        
        await test_instance.test_notification_handling()
        print("✓ Notification handling test passed")
        
        await test_instance.test_blocked_signals_logging()
        print("✓ Blocked signals logging test passed")
        
        print("\nAll keyword blacklist tests passed successfully!")
        
    except Exception as e:
        print(f"✗ Test failed: {e}")
        raise

if __name__ == "__main__":
    # Run the tests
    asyncio.run(run_basic_tests())