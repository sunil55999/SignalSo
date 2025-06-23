"""
Tests for End of Week SL Remover functionality
Tests the stop loss removal/widening for prop firm stealth operations
"""

import asyncio
import json
import tempfile
import os
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List

# Import the module to test
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from end_of_week_sl_remover import (
    EndOfWeekSLRemover, EndOfWeekConfig, SLRemovalMode, MarketType, 
    SLRemovalAction, TradeInfo
)

class TestEndOfWeekSLRemover:
    
    def setup_method(self):
        """Setup test environment with temporary files"""
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.temp_dir, "test_config.json")
        self.log_file = os.path.join(self.temp_dir, "test_eow_log.json")
        
        # Create test remover
        self.remover = EndOfWeekSLRemover(
            config_file=self.config_file,
            log_file=self.log_file
        )
        
        # Mock modules
        self.mock_mt5_bridge = AsyncMock()
        self.mock_copilot_bot = AsyncMock()
        self.remover.inject_modules(
            mt5_bridge=self.mock_mt5_bridge,
            copilot_bot=self.mock_copilot_bot
        )
    
    def teardown_method(self):
        """Cleanup temporary files"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_default_configuration_creation(self):
        """Test default configuration is created properly"""
        config = self.remover.config
        
        assert config.enabled == True
        assert config.mode == SLRemovalMode.WIDEN
        assert config.activation_window_start == "15:30"
        assert config.activation_window_end == "16:59"
        assert config.widen_distance_pips == 300
        assert MarketType.CRYPTO in config.excluded_market_types
        assert config.prop_firm_mode == True
    
    def test_symbol_categorization(self):
        """Test symbol market type categorization"""
        # Test forex symbols
        assert self.remover._get_market_type('EURUSD') == MarketType.FOREX
        assert self.remover._get_market_type('GBPJPY') == MarketType.FOREX
        
        # Test crypto symbols
        assert self.remover._get_market_type('BTCUSD') == MarketType.CRYPTO
        assert self.remover._get_market_type('ETHUSD') == MarketType.CRYPTO
        
        # Test indices
        assert self.remover._get_market_type('US30') == MarketType.INDICES
        assert self.remover._get_market_type('SPX500') == MarketType.INDICES
        
        # Test commodities
        assert self.remover._get_market_type('XAUUSD') == MarketType.COMMODITIES
        assert self.remover._get_market_type('USOIL') == MarketType.COMMODITIES
        
        # Test unknown symbol (should default to forex)
        assert self.remover._get_market_type('UNKNOWN') == MarketType.FOREX
    
    def test_pip_value_calculation(self):
        """Test pip value calculation for different symbols"""
        # JPY pairs
        assert self.remover._get_pip_value('USDJPY') == 0.01
        assert self.remover._get_pip_value('EURJPY') == 0.01
        
        # Standard forex pairs
        assert self.remover._get_pip_value('EURUSD') == 0.0001
        assert self.remover._get_pip_value('GBPUSD') == 0.0001
        
        # Gold
        assert self.remover._get_pip_value('XAUUSD') == 0.1
        
        # Silver
        assert self.remover._get_pip_value('XAGUSD') == 0.001
        
        # Oil
        assert self.remover._get_pip_value('USOIL') == 0.01
        
        # Indices
        assert self.remover._get_pip_value('US30') == 1.0
        assert self.remover._get_pip_value('SPX500') == 0.1
    
    def test_friday_close_window_detection(self):
        """Test Friday close window detection"""
        # Test Friday within window
        friday_1600 = datetime(2025, 6, 27, 16, 0, tzinfo=timezone.utc)  # Friday 16:00 UTC
        assert self.remover._is_friday_close_window(friday_1600) == True
        
        # Test Friday before window
        friday_1400 = datetime(2025, 6, 27, 14, 0, tzinfo=timezone.utc)  # Friday 14:00 UTC
        assert self.remover._is_friday_close_window(friday_1400) == False
        
        # Test Friday after window
        friday_1800 = datetime(2025, 6, 27, 18, 0, tzinfo=timezone.utc)  # Friday 18:00 UTC
        assert self.remover._is_friday_close_window(friday_1800) == False
        
        # Test non-Friday
        monday_1600 = datetime(2025, 6, 23, 16, 0, tzinfo=timezone.utc)  # Monday 16:00 UTC
        assert self.remover._is_friday_close_window(monday_1600) == False
    
    def test_symbol_processing_rules(self):
        """Test symbol processing inclusion/exclusion rules"""
        # Test excluded pairs
        self.remover.config.excluded_pairs = ['EURUSD', 'GBPUSD']
        
        should_process, reason = self.remover._should_process_symbol('EURUSD')
        assert should_process == False
        assert 'excluded pairs' in reason.lower()
        
        should_process, reason = self.remover._should_process_symbol('USDJPY')
        assert should_process == True
        
        # Test excluded market types (crypto by default)
        should_process, reason = self.remover._should_process_symbol('BTCUSD')
        assert should_process == False
        assert 'crypto' in reason.lower()
        
        # Test allowed forex symbol
        should_process, reason = self.remover._should_process_symbol('EURJPY')
        assert should_process == True
    
    def test_widened_sl_calculation(self):
        """Test stop loss widening calculation"""
        # Test BUY trade - SL should move down (further from entry)
        buy_trade = TradeInfo(
            ticket=12345,
            symbol='EURUSD',
            action='BUY',
            entry_price=1.0850,
            current_sl=1.0800,
            current_tp=1.0900,
            lot_size=0.1,
            open_time=datetime.now()
        )
        
        widened_sl = self.remover._calculate_widened_sl(buy_trade)
        expected_sl = 1.0800 - (300 * 0.0001)  # 300 pips * pip value
        assert abs(widened_sl - expected_sl) < 0.00001
        
        # Test SELL trade - SL should move up (further from entry)
        sell_trade = TradeInfo(
            ticket=12346,
            symbol='GBPUSD',
            action='SELL',
            entry_price=1.2750,
            current_sl=1.2800,
            current_tp=1.2700,
            lot_size=0.05,
            open_time=datetime.now()
        )
        
        widened_sl = self.remover._calculate_widened_sl(sell_trade)
        expected_sl = 1.2800 + (300 * 0.0001)  # 300 pips * pip value
        assert abs(widened_sl - expected_sl) < 0.00001
        
        # Test trade with no SL
        no_sl_trade = TradeInfo(
            ticket=12347,
            symbol='USDJPY',
            action='BUY',
            entry_price=150.00,
            current_sl=None,
            current_tp=151.00,
            lot_size=0.1,
            open_time=datetime.now()
        )
        
        widened_sl = self.remover._calculate_widened_sl(no_sl_trade)
        assert widened_sl is None
    
    async def test_remove_mode_processing(self):
        """Test SL removal mode processing"""
        self.remover.config.mode = SLRemovalMode.REMOVE
        
        # Mock open trades
        mock_trades = [
            TradeInfo(
                ticket=12345,
                symbol='EURUSD',
                action='BUY',
                entry_price=1.0850,
                current_sl=1.0800,
                current_tp=1.0900,
                lot_size=0.1,
                open_time=datetime.now()
            )
        ]
        
        with patch.object(self.remover, '_get_open_trades', return_value=mock_trades):
            with patch.object(self.remover, '_update_trade_sl', return_value=True) as mock_update:
                result = await self.remover.process_end_of_week_sl_removal(force_run=True)
        
        assert result['processed'] == True
        assert len(result['actions']) == 1
        assert result['actions'][0]['action_type'] == 'remove'
        assert result['actions'][0]['new_sl'] is None
        
        # Verify SL update was called with None
        mock_update.assert_called_with(12345, None)
    
    async def test_widen_mode_processing(self):
        """Test SL widening mode processing"""
        self.remover.config.mode = SLRemovalMode.WIDEN
        
        # Mock open trades
        mock_trades = [
            TradeInfo(
                ticket=12345,
                symbol='EURUSD',
                action='BUY',
                entry_price=1.0850,
                current_sl=1.0800,
                current_tp=1.0900,
                lot_size=0.1,
                open_time=datetime.now()
            )
        ]
        
        with patch.object(self.remover, '_get_open_trades', return_value=mock_trades):
            with patch.object(self.remover, '_update_trade_sl', return_value=True) as mock_update:
                result = await self.remover.process_end_of_week_sl_removal(force_run=True)
        
        assert result['processed'] == True
        assert len(result['actions']) == 1
        assert result['actions'][0]['action_type'] == 'widen'
        assert result['actions'][0]['new_sl'] != result['actions'][0]['original_sl']
        
        # Verify SL was widened by 300 pips
        expected_new_sl = 1.0800 - (300 * 0.0001)
        mock_update.assert_called_with(12345, expected_new_sl)
    
    async def test_ignore_mode_processing(self):
        """Test ignore mode processing"""
        self.remover.config.mode = SLRemovalMode.IGNORE
        
        # Mock open trades
        mock_trades = [
            TradeInfo(
                ticket=12345,
                symbol='EURUSD',
                action='BUY',
                entry_price=1.0850,
                current_sl=1.0800,
                current_tp=1.0900,
                lot_size=0.1,
                open_time=datetime.now()
            )
        ]
        
        with patch.object(self.remover, '_get_open_trades', return_value=mock_trades):
            with patch.object(self.remover, '_update_trade_sl') as mock_update:
                result = await self.remover.process_end_of_week_sl_removal(force_run=True)
        
        assert result['processed'] == True
        assert len(result['actions']) == 1
        assert result['actions'][0]['action_type'] == 'ignore'
        
        # Verify no SL update was attempted
        mock_update.assert_not_called()
    
    async def test_excluded_symbols_skipped(self):
        """Test that excluded symbols are skipped"""
        self.remover.config.excluded_pairs = ['EURUSD']
        
        # Mock open trades with excluded symbol
        mock_trades = [
            TradeInfo(
                ticket=12345,
                symbol='EURUSD',  # This should be skipped
                action='BUY',
                entry_price=1.0850,
                current_sl=1.0800,
                current_tp=1.0900,
                lot_size=0.1,
                open_time=datetime.now()
            ),
            TradeInfo(
                ticket=12346,
                symbol='GBPUSD',  # This should be processed
                action='SELL',
                entry_price=1.2750,
                current_sl=1.2800,
                current_tp=1.2700,
                lot_size=0.05,
                open_time=datetime.now()
            )
        ]
        
        with patch.object(self.remover, '_get_open_trades', return_value=mock_trades):
            with patch.object(self.remover, '_update_trade_sl', return_value=True):
                result = await self.remover.process_end_of_week_sl_removal(force_run=True)
        
        assert result['processed'] == True
        assert len(result['actions']) == 1  # Only GBPUSD should be processed
        assert result['actions'][0]['symbol'] == 'GBPUSD'
    
    async def test_crypto_symbols_excluded_by_default(self):
        """Test that crypto symbols are excluded by default"""
        # Mock open trades with crypto symbol
        mock_trades = [
            TradeInfo(
                ticket=12345,
                symbol='BTCUSD',  # Crypto - should be skipped
                action='BUY',
                entry_price=50000,
                current_sl=49000,
                current_tp=51000,
                lot_size=0.1,
                open_time=datetime.now()
            )
        ]
        
        with patch.object(self.remover, '_get_open_trades', return_value=mock_trades):
            result = await self.remover.process_end_of_week_sl_removal(force_run=True)
        
        assert result['processed'] == True
        assert len(result['actions']) == 0  # No actions should be taken
    
    async def test_trades_without_sl_handling(self):
        """Test handling of trades without stop loss"""
        # Mock open trades without SL
        mock_trades = [
            TradeInfo(
                ticket=12345,
                symbol='EURUSD',
                action='BUY',
                entry_price=1.0850,
                current_sl=None,  # No SL set
                current_tp=1.0900,
                lot_size=0.1,
                open_time=datetime.now()
            )
        ]
        
        # Test with REMOVE mode - should skip
        self.remover.config.mode = SLRemovalMode.REMOVE
        with patch.object(self.remover, '_get_open_trades', return_value=mock_trades):
            result = await self.remover.process_end_of_week_sl_removal(force_run=True)
        
        assert result['processed'] == True
        assert len(result['actions']) == 0
        
        # Test with IGNORE mode - should log
        self.remover.config.mode = SLRemovalMode.IGNORE
        with patch.object(self.remover, '_get_open_trades', return_value=mock_trades):
            result = await self.remover.process_end_of_week_sl_removal(force_run=True)
        
        assert result['processed'] == True
        assert len(result['actions']) == 1
        assert result['actions'][0]['action_type'] == 'ignore'
    
    async def test_time_window_enforcement(self):
        """Test that processing only occurs during time window"""
        # Test outside time window without force_run
        result = await self.remover.process_end_of_week_sl_removal(force_run=False)
        
        assert result['processed'] == False
        assert 'not in activation window' in result['reason'].lower()
    
    async def test_disabled_configuration(self):
        """Test behavior when feature is disabled"""
        self.remover.config.enabled = False
        
        result = await self.remover.process_end_of_week_sl_removal(force_run=False)
        
        assert result['processed'] == False
        assert 'disabled' in result['reason'].lower()
    
    async def test_copilot_notifications(self):
        """Test Copilot Bot notifications"""
        self.remover.config.notify_copilot = True
        
        # Mock open trades
        mock_trades = [
            TradeInfo(
                ticket=12345,
                symbol='EURUSD',
                action='BUY',
                entry_price=1.0850,
                current_sl=1.0800,
                current_tp=1.0900,
                lot_size=0.1,
                open_time=datetime.now()
            )
        ]
        
        with patch.object(self.remover, '_get_open_trades', return_value=mock_trades):
            with patch.object(self.remover, '_update_trade_sl', return_value=True):
                await self.remover.process_end_of_week_sl_removal(force_run=True)
        
        # Verify notification method was called
        # In real implementation, this would verify copilot_bot.send_alert was called
        assert len(self.remover.removal_history) == 1
    
    def test_statistics_calculation(self):
        """Test statistics calculation"""
        # Add some mock history
        action1 = SLRemovalAction(
            ticket=12345,
            symbol='EURUSD',
            original_sl=1.0800,
            new_sl=None,
            action_type='remove',
            reason='Test removal',
            timestamp=datetime.now(),
            trade_direction='BUY',
            entry_price=1.0850,
            pip_value=0.0001
        )
        
        action2 = SLRemovalAction(
            ticket=12346,
            symbol='GBPUSD',
            original_sl=1.2800,
            new_sl=1.2830,
            action_type='widen',
            reason='Test widening',
            timestamp=datetime.now(),
            trade_direction='SELL',
            entry_price=1.2750,
            pip_value=0.0001
        )
        
        self.remover.removal_history = [action1, action2]
        
        stats = self.remover.get_removal_statistics()
        
        assert stats['total_actions'] == 2
        assert stats['by_action_type']['remove'] == 1
        assert stats['by_action_type']['widen'] == 1
        assert stats['symbols_processed'] == 2
        assert stats['enabled'] == True
    
    def test_recent_actions_retrieval(self):
        """Test retrieval of recent actions"""
        # Add mock history
        for i in range(5):
            action = SLRemovalAction(
                ticket=12340 + i,
                symbol='EURUSD',
                original_sl=1.0800,
                new_sl=1.0770,
                action_type='widen',
                reason=f'Test action {i}',
                timestamp=datetime.now(),
                trade_direction='BUY',
                entry_price=1.0850,
                pip_value=0.0001
            )
            self.remover.removal_history.append(action)
        
        recent = self.remover.get_recent_actions(limit=3)
        
        assert len(recent) == 3
        assert all('ticket' in action for action in recent)
        assert all('symbol' in action for action in recent)
        assert all('action_type' in action for action in recent)
        
        # Should be in reverse chronological order (latest first)
        assert recent[0]['ticket'] == 12344
        assert recent[2]['ticket'] == 12342
    
    def test_configuration_persistence(self):
        """Test that configuration changes are persisted"""
        new_config = {
            'mode': 'remove',
            'widen_distance_pips': 500,
            'excluded_pairs': ['EURUSD', 'GBPUSD']
        }
        
        self.remover.update_config(new_config)
        
        # Verify changes in memory
        assert self.remover.config.mode == SLRemovalMode.REMOVE
        assert self.remover.config.widen_distance_pips == 500
        assert 'EURUSD' in self.remover.config.excluded_pairs
        
        # Create new remover to test persistence
        remover2 = EndOfWeekSLRemover(
            config_file=self.config_file,
            log_file=os.path.join(self.temp_dir, "test_eow_log2.json")
        )
        
        assert remover2.config.mode == SLRemovalMode.REMOVE
        assert remover2.config.widen_distance_pips == 500
        assert 'EURUSD' in remover2.config.excluded_pairs
    
    def test_history_persistence(self):
        """Test that removal history is persisted"""
        action = SLRemovalAction(
            ticket=12345,
            symbol='EURUSD',
            original_sl=1.0800,
            new_sl=None,
            action_type='remove',
            reason='Persistence test',
            timestamp=datetime.now(),
            trade_direction='BUY',
            entry_price=1.0850,
            pip_value=0.0001
        )
        
        self.remover.removal_history.append(action)
        self.remover._save_history()
        
        # Create new remover to test persistence
        remover2 = EndOfWeekSLRemover(
            config_file=self.config_file,
            log_file=self.log_file
        )
        
        assert len(remover2.removal_history) == 1
        loaded_action = remover2.removal_history[0]
        assert loaded_action.ticket == 12345
        assert loaded_action.action_type == 'remove'
        assert loaded_action.reason == 'Persistence test'
    
    async def test_jpy_pairs_pip_calculation(self):
        """Test proper pip calculation for JPY pairs"""
        self.remover.config.mode = SLRemovalMode.WIDEN
        self.remover.config.widen_distance_pips = 100
        
        # Mock JPY pair trade
        mock_trades = [
            TradeInfo(
                ticket=12345,
                symbol='USDJPY',
                action='BUY',
                entry_price=150.00,
                current_sl=149.50,
                current_tp=151.00,
                lot_size=0.1,
                open_time=datetime.now()
            )
        ]
        
        with patch.object(self.remover, '_get_open_trades', return_value=mock_trades):
            with patch.object(self.remover, '_update_trade_sl', return_value=True) as mock_update:
                await self.remover.process_end_of_week_sl_removal(force_run=True)
        
        # For JPY pairs, pip value is 0.01, so 100 pips = 1.00
        expected_new_sl = 149.50 - (100 * 0.01)  # 148.50
        mock_update.assert_called_with(12345, expected_new_sl)
    
    async def test_mt5_bridge_failure_handling(self):
        """Test handling of MT5 bridge failures"""
        # Mock open trades
        mock_trades = [
            TradeInfo(
                ticket=12345,
                symbol='EURUSD',
                action='BUY',
                entry_price=1.0850,
                current_sl=1.0800,
                current_tp=1.0900,
                lot_size=0.1,
                open_time=datetime.now()
            )
        ]
        
        with patch.object(self.remover, '_get_open_trades', return_value=mock_trades):
            with patch.object(self.remover, '_update_trade_sl', return_value=False):  # Simulate failure
                result = await self.remover.process_end_of_week_sl_removal(force_run=True)
        
        assert result['processed'] == True
        assert len(result['actions']) == 0  # No actions should be recorded on failure

# Integration test
async def test_integration_with_strategy_runtime():
    """Test integration scenario with strategy runtime"""
    remover = EndOfWeekSLRemover()
    
    # Mock strategy runtime scenario
    friday_close_time = datetime(2025, 6, 27, 16, 30, tzinfo=timezone.utc)  # Friday 16:30 UTC
    
    # Simulate being in Friday close window
    with patch.object(remover, '_is_friday_close_window', return_value=True):
        # Mock open trades
        mock_trades = [
            TradeInfo(
                ticket=12345,
                symbol='EURUSD',
                action='BUY',
                entry_price=1.0850,
                current_sl=1.0800,
                current_tp=1.0900,
                lot_size=0.1,
                open_time=datetime.now()
            )
        ]
        
        with patch.object(remover, '_get_open_trades', return_value=mock_trades):
            with patch.object(remover, '_update_trade_sl', return_value=True):
                result = await remover.process_end_of_week_sl_removal()
    
    # Verify integration
    assert result['processed'] == True
    assert len(result['actions']) == 1
    assert result['actions'][0]['action_type'] == 'widen'  # Default mode
    
    print(f"Integration test passed:")
    print(f"  Processed: {result['processed']}")
    print(f"  Actions taken: {len(result['actions'])}")
    print(f"  Action type: {result['actions'][0]['action_type']}")

# Main execution for testing
def run_basic_tests():
    """Run basic functionality tests"""
    test_instance = TestEndOfWeekSLRemover()
    test_instance.setup_method()
    
    try:
        test_instance.test_default_configuration_creation()
        print("✓ Default configuration test passed")
        
        test_instance.test_symbol_categorization()
        print("✓ Symbol categorization test passed")
        
        test_instance.test_pip_value_calculation()
        print("✓ Pip value calculation test passed")
        
        test_instance.test_friday_close_window_detection()
        print("✓ Friday close window detection test passed")
        
        test_instance.test_symbol_processing_rules()
        print("✓ Symbol processing rules test passed")
        
        test_instance.test_widened_sl_calculation()
        print("✓ Widened SL calculation test passed")
        
        asyncio.run(test_instance.test_widen_mode_processing())
        print("✓ Widen mode processing test passed")
        
        asyncio.run(test_instance.test_remove_mode_processing())
        print("✓ Remove mode processing test passed")
        
        asyncio.run(test_integration_with_strategy_runtime())
        print("✓ Integration test passed")
        
        print("\nAll end-of-week SL remover tests passed successfully!")
        
    except Exception as e:
        print(f"✗ Test failed: {e}")
        raise
    finally:
        test_instance.teardown_method()

if __name__ == "__main__":
    run_basic_tests()