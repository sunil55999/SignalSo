"""
Tests for End of Week SL Remover module
"""

import pytest
import json
import tempfile
import os
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone, timedelta
from desktop_app.end_of_week_sl_remover import EndOfWeekSLRemover, SLRemovalMode, MarketType, TradeInfo


class TestEndOfWeekSLRemover:
    
    def setup_method(self):
        """Setup test environment"""
        self.temp_config = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        self.temp_log = tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False)
        
        # Create test config
        test_config = {
            'end_of_week_sl_remover': {
                'enabled': True,
                'mode': 'widen',
                'activation_window_start': '15:30',
                'activation_window_end': '16:59',
                'widen_distance_pips': 300,
                'excluded_pairs': [],
                'excluded_market_types': ['crypto'],
                'prop_firm_mode': True,
                'log_actions': True,
                'notify_copilot': True
            }
        }
        
        json.dump(test_config, self.temp_config)
        self.temp_config.close()
        self.temp_log.close()
        
        self.eow_remover = EndOfWeekSLRemover(
            config_file=self.temp_config.name,
            log_file=self.temp_log.name
        )
    
    def teardown_method(self):
        """Cleanup test files"""
        os.unlink(self.temp_config.name)
        os.unlink(self.temp_log.name)
    
    def test_is_friday_close_window(self):
        """Test Friday close window detection"""
        # Test Friday within window (15:30-16:59 UTC)
        friday_within = datetime(2023, 6, 16, 16, 0, 0, tzinfo=timezone.utc)  # Friday 16:00
        assert self.eow_remover._is_friday_close_window(friday_within) == True
        
        # Test Friday exactly at start
        friday_start = datetime(2023, 6, 16, 15, 30, 0, tzinfo=timezone.utc)  # Friday 15:30
        assert self.eow_remover._is_friday_close_window(friday_start) == True
        
        # Test Friday exactly at end
        friday_end = datetime(2023, 6, 16, 16, 59, 0, tzinfo=timezone.utc)  # Friday 16:59
        assert self.eow_remover._is_friday_close_window(friday_end) == True
        
        # Test Friday outside window
        friday_outside = datetime(2023, 6, 16, 17, 0, 0, tzinfo=timezone.utc)  # Friday 17:00
        assert self.eow_remover._is_friday_close_window(friday_outside) == False
        
        # Test Friday before window
        friday_before = datetime(2023, 6, 16, 15, 29, 0, tzinfo=timezone.utc)  # Friday 15:29
        assert self.eow_remover._is_friday_close_window(friday_before) == False
        
        # Test non-Friday
        thursday = datetime(2023, 6, 15, 16, 0, 0, tzinfo=timezone.utc)  # Thursday 16:00
        assert self.eow_remover._is_friday_close_window(thursday) == False
    
    def test_get_market_type(self):
        """Test market type detection"""
        # Forex majors
        assert self.eow_remover._get_market_type('EURUSD') == MarketType.FOREX
        assert self.eow_remover._get_market_type('GBPUSD') == MarketType.FOREX
        assert self.eow_remover._get_market_type('USDJPY') == MarketType.FOREX
        
        # Crypto
        assert self.eow_remover._get_market_type('BTCUSD') == MarketType.CRYPTO
        assert self.eow_remover._get_market_type('ETHUSD') == MarketType.CRYPTO
        
        # Indices
        assert self.eow_remover._get_market_type('US30') == MarketType.INDICES
        assert self.eow_remover._get_market_type('SPX500') == MarketType.INDICES
        
        # Commodities
        assert self.eow_remover._get_market_type('XAUUSD') == MarketType.COMMODITIES
        assert self.eow_remover._get_market_type('USOIL') == MarketType.COMMODITIES
        
        # Pattern matching
        assert self.eow_remover._get_market_type('BITCOIN') == MarketType.CRYPTO
        assert self.eow_remover._get_market_type('GOLD123') == MarketType.COMMODITIES
        
        # Unknown defaults to forex
        assert self.eow_remover._get_market_type('UNKNOWN') == MarketType.FOREX
    
    def test_get_pip_value(self):
        """Test pip value calculation"""
        # JPY pairs
        assert self.eow_remover._get_pip_value('USDJPY') == 0.01
        assert self.eow_remover._get_pip_value('EURJPY') == 0.01
        
        # Standard forex
        assert self.eow_remover._get_pip_value('EURUSD') == 0.0001
        assert self.eow_remover._get_pip_value('GBPUSD') == 0.0001
        
        # Gold
        assert self.eow_remover._get_pip_value('XAUUSD') == 0.1
        assert self.eow_remover._get_pip_value('GOLD') == 0.1
        
        # Silver
        assert self.eow_remover._get_pip_value('XAGUSD') == 0.001
        
        # Oil
        assert self.eow_remover._get_pip_value('USOIL') == 0.01
        
        # Indices
        assert self.eow_remover._get_pip_value('US30') == 1.0
        assert self.eow_remover._get_pip_value('SPX500') == 0.1
        
        # Default
        assert self.eow_remover._get_pip_value('UNKNOWN') == 0.0001
    
    def test_should_process_symbol(self):
        """Test symbol processing logic"""
        # Normal forex pair should be processed
        should_process, reason = self.eow_remover._should_process_symbol('EURUSD')
        assert should_process == True
        assert "approved" in reason.lower()
        
        # Excluded pair
        self.eow_remover.config.excluded_pairs = ['GBPUSD']
        should_process, reason = self.eow_remover._should_process_symbol('GBPUSD')
        assert should_process == False
        assert "excluded pairs" in reason.lower()
        
        # Excluded market type (crypto)
        should_process, reason = self.eow_remover._should_process_symbol('BTCUSD')
        assert should_process == False
        assert "excluded" in reason.lower()
        
        # Reset config
        self.eow_remover.config.excluded_pairs = []
    
    def test_calculate_widened_sl_buy(self):
        """Test SL widening calculation for BUY trades"""
        trade = TradeInfo(
            ticket=12345,
            symbol='EURUSD',
            action='BUY',
            entry_price=1.1000,
            current_sl=1.0950,  # 50 pips below entry
            current_tp=1.1100,
            lot_size=0.1,
            open_time=datetime.now()
        )
        
        # Config: widen by 300 pips
        new_sl = self.eow_remover._calculate_widened_sl(trade)
        
        # For BUY, SL should move further down
        pip_value = 0.0001  # EURUSD
        widen_amount = 300 * pip_value  # 0.03
        expected_sl = 1.0950 - 0.03  # 1.0920
        
        assert abs(new_sl - expected_sl) < 1e-6, f"Expected {expected_sl}, got {new_sl}"
    
    def test_calculate_widened_sl_sell(self):
        """Test SL widening calculation for SELL trades"""
        trade = TradeInfo(
            ticket=12346,
            symbol='EURUSD',
            action='SELL',
            entry_price=1.1000,
            current_sl=1.1050,  # 50 pips above entry
            current_tp=1.0900,
            lot_size=0.1,
            open_time=datetime.now()
        )
        
        # Config: widen by 300 pips
        new_sl = self.eow_remover._calculate_widened_sl(trade)
        
        # For SELL, SL should move further up
        pip_value = 0.0001  # EURUSD
        widen_amount = 300 * pip_value  # 0.03
        expected_sl = 1.1050 + 0.03  # 1.1080
        
        assert abs(new_sl - expected_sl) < 1e-6, f"Expected {expected_sl}, got {new_sl}"
    
    def test_calculate_widened_sl_no_sl(self):
        """Test SL widening when no SL is set"""
        trade = TradeInfo(
            ticket=12347,
            symbol='EURUSD',
            action='BUY',
            entry_price=1.1000,
            current_sl=None,  # No SL
            current_tp=1.1100,
            lot_size=0.1,
            open_time=datetime.now()
        )
        
        new_sl = self.eow_remover._calculate_widened_sl(trade)
        assert new_sl is None, "Should return None when no SL is set"
    
    @pytest.mark.asyncio
    async def test_run_end_of_week_check_outside_window(self):
        """Test EOW check outside Friday window"""
        # Test on Thursday
        thursday = datetime(2023, 6, 15, 16, 0, 0, tzinfo=timezone.utc)
        
        result = await self.eow_remover.run_end_of_week_check(thursday)
        
        assert result['executed'] == False
        assert 'Outside Friday close window' in result['reason']
        assert result['current_time'] == thursday.isoformat()
    
    @pytest.mark.asyncio
    async def test_run_end_of_week_check_disabled(self):
        """Test EOW check when disabled"""
        self.eow_remover.config.enabled = False
        
        friday_window = datetime(2023, 6, 16, 16, 0, 0, tzinfo=timezone.utc)
        result = await self.eow_remover.run_end_of_week_check(friday_window)
        
        assert result['executed'] == False
        assert 'disabled' in result['reason'].lower()
    
    @pytest.mark.asyncio
    async def test_run_end_of_week_check_no_trades(self):
        """Test EOW check with no open trades"""
        # Mock empty trades list
        self.eow_remover._get_open_trades = AsyncMock(return_value=[])
        
        friday_window = datetime(2023, 6, 16, 16, 0, 0, tzinfo=timezone.utc)
        result = await self.eow_remover.run_end_of_week_check(friday_window)
        
        assert result['executed'] == True
        assert 'No open trades' in result['reason']
        assert result['trades_processed'] == 0
    
    @pytest.mark.asyncio
    async def test_run_end_of_week_check_widen_mode(self):
        """Test EOW check in widen mode"""
        # Create mock trades
        mock_trades = [
            TradeInfo(
                ticket=12345,
                symbol='EURUSD',
                action='BUY',
                entry_price=1.1000,
                current_sl=1.0950,
                current_tp=1.1100,
                lot_size=0.1,
                open_time=datetime.now()
            ),
            TradeInfo(
                ticket=12346,
                symbol='GBPUSD',
                action='SELL',
                entry_price=1.2500,
                current_sl=1.2550,
                current_tp=1.2400,
                lot_size=0.05,
                open_time=datetime.now()
            )
        ]
        
        # Mock methods
        self.eow_remover._get_open_trades = AsyncMock(return_value=mock_trades)
        self.eow_remover._update_trade_sl = AsyncMock(return_value=True)
        
        # Set mode to WIDEN
        self.eow_remover.config.mode = SLRemovalMode.WIDEN
        
        friday_window = datetime(2023, 6, 16, 16, 0, 0, tzinfo=timezone.utc)
        result = await self.eow_remover.run_end_of_week_check(friday_window)
        
        assert result['executed'] == True
        assert result['trades_processed'] == 2
        assert result['successful_modifications'] == 2
        assert result['mode'] == 'widen'
        
        # Verify SL update calls
        assert self.eow_remover._update_trade_sl.call_count == 2
    
    @pytest.mark.asyncio
    async def test_run_end_of_week_check_remove_mode(self):
        """Test EOW check in remove mode"""
        # Create mock trade
        mock_trades = [
            TradeInfo(
                ticket=12345,
                symbol='EURUSD',
                action='BUY',
                entry_price=1.1000,
                current_sl=1.0950,
                current_tp=1.1100,
                lot_size=0.1,
                open_time=datetime.now()
            )
        ]
        
        # Mock methods
        self.eow_remover._get_open_trades = AsyncMock(return_value=mock_trades)
        self.eow_remover._update_trade_sl = AsyncMock(return_value=True)
        
        # Set mode to REMOVE
        self.eow_remover.config.mode = SLRemovalMode.REMOVE
        
        friday_window = datetime(2023, 6, 16, 16, 0, 0, tzinfo=timezone.utc)
        result = await self.eow_remover.run_end_of_week_check(friday_window)
        
        assert result['executed'] == True
        assert result['trades_processed'] == 1
        assert result['mode'] == 'remove'
        
        # Verify SL removal call (None value)
        self.eow_remover._update_trade_sl.assert_called_with(12345, None)
    
    @pytest.mark.asyncio
    async def test_run_end_of_week_check_ignore_mode(self):
        """Test EOW check in ignore mode"""
        # Create mock trade
        mock_trades = [
            TradeInfo(
                ticket=12345,
                symbol='EURUSD',
                action='BUY',
                entry_price=1.1000,
                current_sl=1.0950,
                current_tp=1.1100,
                lot_size=0.1,
                open_time=datetime.now()
            )
        ]
        
        # Mock methods
        self.eow_remover._get_open_trades = AsyncMock(return_value=mock_trades)
        self.eow_remover._update_trade_sl = AsyncMock(return_value=True)
        
        # Set mode to IGNORE
        self.eow_remover.config.mode = SLRemovalMode.IGNORE
        
        friday_window = datetime(2023, 6, 16, 16, 0, 0, tzinfo=timezone.utc)
        result = await self.eow_remover.run_end_of_week_check(friday_window)
        
        assert result['executed'] == True
        assert result['trades_processed'] == 0  # Trade ignored
        
        # Verify no SL update calls
        self.eow_remover._update_trade_sl.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_run_end_of_week_check_excluded_symbols(self):
        """Test EOW check with excluded symbols"""
        # Create mock trades with excluded symbol
        mock_trades = [
            TradeInfo(
                ticket=12345,
                symbol='BTCUSD',  # Crypto - excluded by default
                action='BUY',
                entry_price=50000.0,
                current_sl=49000.0,
                current_tp=52000.0,
                lot_size=0.01,
                open_time=datetime.now()
            ),
            TradeInfo(
                ticket=12346,
                symbol='EURUSD',  # Should be processed
                action='BUY',
                entry_price=1.1000,
                current_sl=1.0950,
                current_tp=1.1100,
                lot_size=0.1,
                open_time=datetime.now()
            )
        ]
        
        # Mock methods
        self.eow_remover._get_open_trades = AsyncMock(return_value=mock_trades)
        self.eow_remover._update_trade_sl = AsyncMock(return_value=True)
        
        friday_window = datetime(2023, 6, 16, 16, 0, 0, tzinfo=timezone.utc)
        result = await self.eow_remover.run_end_of_week_check(friday_window)
        
        assert result['executed'] == True
        assert result['trades_processed'] == 1  # Only EURUSD processed
        
        # Verify only one SL update call (for EURUSD)
        assert self.eow_remover._update_trade_sl.call_count == 1
    
    @pytest.mark.asyncio
    async def test_run_end_of_week_check_no_sl_trades(self):
        """Test EOW check with trades that have no SL"""
        # Create mock trades without SL
        mock_trades = [
            TradeInfo(
                ticket=12345,
                symbol='EURUSD',
                action='BUY',
                entry_price=1.1000,
                current_sl=None,  # No SL
                current_tp=1.1100,
                lot_size=0.1,
                open_time=datetime.now()
            )
        ]
        
        # Mock methods
        self.eow_remover._get_open_trades = AsyncMock(return_value=mock_trades)
        self.eow_remover._update_trade_sl = AsyncMock(return_value=True)
        
        friday_window = datetime(2023, 6, 16, 16, 0, 0, tzinfo=timezone.utc)
        result = await self.eow_remover.run_end_of_week_check(friday_window)
        
        assert result['executed'] == True
        assert result['trades_processed'] == 0  # No trades with SL to process
        
        # Verify no SL update calls
        self.eow_remover._update_trade_sl.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_update_trade_sl_success(self):
        """Test successful SL update"""
        # Mock MT5 bridge
        mock_mt5_bridge = AsyncMock()
        self.eow_remover.inject_modules(mt5_bridge=mock_mt5_bridge)
        
        # Test SL update
        success = await self.eow_remover._update_trade_sl(12345, 1.0920)
        
        assert success == True
    
    @pytest.mark.asyncio
    async def test_update_trade_sl_no_bridge(self):
        """Test SL update without MT5 bridge"""
        # No MT5 bridge injected
        success = await self.eow_remover._update_trade_sl(12345, 1.0920)
        
        assert success == False
    
    def test_module_injection(self):
        """Test module injection"""
        mock_mt5_bridge = MagicMock()
        mock_copilot_bot = MagicMock()
        mock_market_data = MagicMock()
        
        self.eow_remover.inject_modules(
            mt5_bridge=mock_mt5_bridge,
            copilot_bot=mock_copilot_bot,
            market_data=mock_market_data
        )
        
        assert self.eow_remover.mt5_bridge == mock_mt5_bridge
        assert self.eow_remover.copilot_bot == mock_copilot_bot
        assert self.eow_remover.market_data == mock_market_data
    
    def test_schedule_with_auto_sync(self):
        """Test scheduling integration with auto_sync"""
        mock_auto_sync = MagicMock()
        
        result = self.eow_remover.schedule_with_auto_sync(mock_auto_sync)
        
        # Should return True indicating successful scheduling
        assert result == True
    
    @pytest.mark.asyncio
    async def test_send_copilot_notification(self):
        """Test copilot notification sending"""
        from desktop_app.end_of_week_sl_remover import SLRemovalAction
        
        # Mock copilot bot
        mock_copilot_bot = AsyncMock()
        self.eow_remover.inject_modules(copilot_bot=mock_copilot_bot)
        
        # Test removal notification
        removal_action = SLRemovalAction(
            ticket=12345,
            symbol='EURUSD',
            original_sl=1.0950,
            new_sl=None,
            action_type='remove',
            reason='EOW protection',
            timestamp=datetime.now(),
            trade_direction='BUY',
            entry_price=1.1000,
            pip_value=0.0001
        )
        
        await self.eow_remover._send_copilot_notification(removal_action)
        
        # Test widening notification
        widening_action = SLRemovalAction(
            ticket=12346,
            symbol='EURUSD',
            original_sl=1.0950,
            new_sl=1.0920,
            action_type='widen',
            reason='EOW protection',
            timestamp=datetime.now(),
            trade_direction='BUY',
            entry_price=1.1000,
            pip_value=0.0001
        )
        
        await self.eow_remover._send_copilot_notification(widening_action)
        
        # Both notifications should have been processed without error
        assert True  # If we reach here, no exceptions were thrown
    
    def test_config_validation(self):
        """Test configuration validation and defaults"""
        # Test default excluded market types
        assert MarketType.CRYPTO in self.eow_remover.config.excluded_market_types
        
        # Test config modes
        assert self.eow_remover.config.mode == SLRemovalMode.WIDEN
        assert self.eow_remover.config.widen_distance_pips == 300
        assert self.eow_remover.config.enabled == True
    
    def test_weekend_edge_cases(self):
        """Test edge cases for weekend detection"""
        # Test Saturday (day after Friday)
        saturday = datetime(2023, 6, 17, 16, 0, 0, tzinfo=timezone.utc)
        assert self.eow_remover._is_friday_close_window(saturday) == False
        
        # Test Sunday
        sunday = datetime(2023, 6, 18, 16, 0, 0, tzinfo=timezone.utc)
        assert self.eow_remover._is_friday_close_window(sunday) == False
        
        # Test Monday
        monday = datetime(2023, 6, 19, 16, 0, 0, tzinfo=timezone.utc)
        assert self.eow_remover._is_friday_close_window(monday) == False


if __name__ == "__main__":
    pytest.main([__file__])