"""
Test Suite for Margin Level Checker Engine
Tests margin monitoring, threshold detection, and trade blocking functionality
"""

import unittest
import asyncio
import json
import tempfile
import os
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from margin_level_checker import (
    MarginLevelChecker, MarginStatus, TradeBlockReason, MarginThresholds,
    AccountInfo, MarginCheckResult, MarginAlert, SymbolMarginRequirement
)

class MockMT5Bridge:
    """Mock MT5 bridge for testing"""
    
    def __init__(self):
        self.mock_account_info = {}
        self.mock_symbol_info = {}
        self.mock_positions = []
        self.close_results = {}
        
    def set_mock_account_info(self, account_data: dict):
        """Set mock account information"""
        self.mock_account_info = account_data
        
    async def get_account_info(self):
        """Mock implementation of get_account_info"""
        return self.mock_account_info
        
    def set_mock_symbol_info(self, symbol: str, symbol_data: dict):
        """Set mock symbol information"""
        self.mock_symbol_info[symbol] = symbol_data
        
    async def get_symbol_info(self, symbol: str):
        """Mock implementation of get_symbol_info"""
        return self.mock_symbol_info.get(symbol, {})
        
    def set_mock_positions(self, positions: list):
        """Set mock open positions"""
        self.mock_positions = positions
        
    async def get_open_positions(self):
        """Mock implementation of get_open_positions"""
        return self.mock_positions
        
    async def close_position(self, ticket: int):
        """Mock position closing"""
        if ticket in self.close_results:
            return self.close_results[ticket]
        return {'success': True, 'ticket': ticket}
        
    def set_close_result(self, ticket: int, result: dict):
        """Set mock close result"""
        self.close_results[ticket] = result

class TestMarginLevelChecker(unittest.TestCase):
    
    def setUp(self):
        """Set up test environment"""
        # Create temporary config file
        self.temp_config = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        self.temp_log = tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False)
        
        # Test configuration
        test_config = {
            "margin_level_checker": {
                "enabled": True,
                "monitoring_interval": 0.1,  # Fast for testing
                "account_update_interval": 0.1,
                "alert_cooldown_minutes": 1,  # Short for testing
                "emergency_close_enabled": True,
                "margin_thresholds": {
                    "safe_level": 300.0,
                    "warning_level": 200.0,
                    "critical_level": 150.0,
                    "margin_call_level": 100.0,
                    "emergency_close_level": 110.0
                },
                "symbol_groups": {
                    "major_pairs": {
                        "symbols": ["EURUSD", "GBPUSD"],
                        "risk_multiplier": 1.0,
                        "max_exposure": 50.0
                    },
                    "commodities": {
                        "symbols": ["XAUUSD"],
                        "risk_multiplier": 1.5,
                        "max_exposure": 25.0
                    }
                }
            }
        }
        
        json.dump(test_config, self.temp_config)
        self.temp_config.close()
        
        # Initialize margin checker
        self.checker = MarginLevelChecker(
            config_path=self.temp_config.name,
            log_path=self.temp_log.name
        )
        
        # Setup mocks
        self.setup_mocks()
        
    def tearDown(self):
        """Clean up test environment"""
        self.checker.stop_monitoring()
        os.unlink(self.temp_config.name)
        os.unlink(self.temp_log.name)
        
        # Clean up data file if created
        data_file = self.temp_log.name.replace('.log', '_data.json')
        if os.path.exists(data_file):
            os.unlink(data_file)
        
    def setup_mocks(self):
        """Setup mock dependencies"""
        self.mock_mt5 = MockMT5Bridge()
        self.checker.set_dependencies(mt5_bridge=self.mock_mt5)

class TestBasicFunctionality(TestMarginLevelChecker):
    """Test basic margin checker functionality"""
    
    def test_initialization(self):
        """Test margin checker initialization"""
        self.assertTrue(self.checker.config['enabled'])
        self.assertEqual(self.checker.thresholds.safe_level, 300.0)
        self.assertEqual(self.checker.thresholds.warning_level, 200.0)
        self.assertEqual(self.checker.thresholds.critical_level, 150.0)
        
    def test_margin_thresholds_creation(self):
        """Test margin thresholds object creation"""
        thresholds = MarginThresholds(
            safe_level=400.0,
            warning_level=250.0,
            critical_level=180.0,
            margin_call_level=120.0,
            emergency_close_level=130.0
        )
        
        self.assertEqual(thresholds.safe_level, 400.0)
        self.assertEqual(thresholds.warning_level, 250.0)
        self.assertEqual(thresholds.critical_level, 180.0)
        
    def test_determine_margin_status(self):
        """Test margin status determination"""
        # Safe level
        status = self.checker._determine_margin_status(350.0)
        self.assertEqual(status, MarginStatus.SAFE)
        
        # Warning level
        status = self.checker._determine_margin_status(250.0)
        self.assertEqual(status, MarginStatus.WARNING)
        
        # Critical level
        status = self.checker._determine_margin_status(140.0)
        self.assertEqual(status, MarginStatus.CRITICAL)
        
        # Margin call level
        status = self.checker._determine_margin_status(90.0)
        self.assertEqual(status, MarginStatus.MARGIN_CALL)
        
    def test_symbol_requirements_loading(self):
        """Test loading of symbol margin requirements"""
        self.assertIn('EURUSD', self.checker.symbol_requirements)
        self.assertIn('XAUUSD', self.checker.symbol_requirements)
        
        eurusd_req = self.checker.symbol_requirements['EURUSD']
        self.assertEqual(eurusd_req.risk_multiplier, 1.0)
        self.assertEqual(eurusd_req.max_exposure, 50.0)
        
        xauusd_req = self.checker.symbol_requirements['XAUUSD']
        self.assertEqual(xauusd_req.risk_multiplier, 1.5)
        self.assertEqual(xauusd_req.max_exposure, 25.0)

class TestAccountInfoUpdate(TestMarginLevelChecker):
    """Test account information update functionality"""
    
    def test_update_account_info_success(self):
        """Test successful account info update"""
        async def run_test():
            # Set mock account data
            mock_account = {
                'balance': 10000.0,
                'equity': 9500.0,
                'margin': 2000.0,
                'free_margin': 7500.0,
                'margin_level': 475.0,
                'credit': 0.0,
                'profit': -500.0
            }
            self.mock_mt5.set_mock_account_info(mock_account)
            
            # Update account info
            success = await self.checker._update_account_info()
            
            self.assertTrue(success)
            self.assertIsNotNone(self.checker.current_account_info)
            
            account_info = self.checker.current_account_info
            self.assertEqual(account_info.balance, 10000.0)
            self.assertEqual(account_info.equity, 9500.0)
            self.assertEqual(account_info.margin_level, 475.0)
            
        asyncio.run(run_test())
        
    def test_update_account_info_failure(self):
        """Test account info update failure"""
        async def run_test():
            # Set MT5 bridge to return None
            self.mock_mt5.set_mock_account_info(None)
            
            # Update account info
            success = await self.checker._update_account_info()
            
            self.assertFalse(success)
            
        asyncio.run(run_test())

class TestMarginCalculations(TestMarginLevelChecker):
    """Test margin calculation functionality"""
    
    def test_calculate_required_margin_default(self):
        """Test margin calculation for unknown symbol"""
        required_margin = self.checker._calculate_required_margin("UNKNOWN", 0.5)
        
        # Should use default calculation
        self.assertEqual(required_margin, 500.0)  # 0.5 * 1000.0
        
    def test_calculate_required_margin_with_multiplier(self):
        """Test margin calculation with risk multiplier"""
        # Set specific margin requirement for XAUUSD
        self.checker.symbol_requirements['XAUUSD'].margin_required = 2000.0
        
        required_margin = self.checker._calculate_required_margin("XAUUSD", 0.1)
        
        # Base: 2000.0 * 0.1 = 200.0, with 1.5 multiplier = 300.0
        expected = 200.0 * 1.5
        self.assertEqual(required_margin, expected)

class TestTradeChecking(TestMarginLevelChecker):
    """Test trade margin checking functionality"""
    
    def test_check_margin_safe_conditions(self):
        """Test margin check under safe conditions"""
        async def run_test():
            # Set good account conditions
            mock_account = {
                'balance': 10000.0,
                'equity': 10000.0,
                'margin': 1000.0,
                'free_margin': 9000.0,
                'margin_level': 1000.0,  # Very safe
                'credit': 0.0,
                'profit': 0.0
            }
            self.mock_mt5.set_mock_account_info(mock_account)
            
            # Check margin for small trade
            result = await self.checker.check_margin_for_trade("EURUSD", 0.1)
            
            self.assertTrue(result.allowed)
            self.assertEqual(result.reason, TradeBlockReason.ALLOWED)
            self.assertEqual(result.margin_status, MarginStatus.SAFE)
            self.assertGreater(result.current_margin_level, 300.0)
            
        asyncio.run(run_test())
        
    def test_check_margin_critical_level(self):
        """Test margin check at critical level"""
        async def run_test():
            # Set critical margin conditions
            mock_account = {
                'balance': 10000.0,
                'equity': 8000.0,
                'margin': 6000.0,
                'free_margin': 2000.0,
                'margin_level': 133.0,  # Critical level
                'credit': 0.0,
                'profit': -2000.0
            }
            self.mock_mt5.set_mock_account_info(mock_account)
            
            # Check margin for trade
            result = await self.checker.check_margin_for_trade("EURUSD", 0.1)
            
            self.assertFalse(result.allowed)
            self.assertEqual(result.reason, TradeBlockReason.CRITICAL_LEVEL)
            self.assertEqual(result.margin_status, MarginStatus.CRITICAL)
            
        asyncio.run(run_test())
        
    def test_check_margin_insufficient_margin(self):
        """Test margin check with insufficient margin"""
        async def run_test():
            # Set low free margin
            mock_account = {
                'balance': 1000.0,
                'equity': 1000.0,
                'margin': 800.0,
                'free_margin': 200.0,  # Very low free margin
                'margin_level': 125.0,
                'credit': 0.0,
                'profit': 0.0
            }
            self.mock_mt5.set_mock_account_info(mock_account)
            
            # Check margin for large trade
            result = await self.checker.check_margin_for_trade("EURUSD", 1.0)  # Large volume
            
            self.assertFalse(result.allowed)
            self.assertEqual(result.reason, TradeBlockReason.INSUFFICIENT_MARGIN)
            self.assertGreater(result.required_margin, result.available_margin)
            
        asyncio.run(run_test())
        
    def test_check_margin_emergency_block(self):
        """Test margin check with emergency block active"""
        async def run_test():
            # Set good account conditions
            mock_account = {
                'balance': 10000.0,
                'equity': 10000.0,
                'margin': 1000.0,
                'free_margin': 9000.0,
                'margin_level': 1000.0,
                'credit': 0.0,
                'profit': 0.0
            }
            self.mock_mt5.set_mock_account_info(mock_account)
            
            # Enable emergency block
            self.checker.enable_emergency_block("Test emergency", 30)
            
            # Check margin for trade
            result = await self.checker.check_margin_for_trade("EURUSD", 0.1)
            
            self.assertFalse(result.allowed)
            self.assertEqual(result.reason, TradeBlockReason.EMERGENCY_BLOCK)
            self.assertIn("Test emergency", result.risk_assessment)
            
        asyncio.run(run_test())

class TestAlertSystem(TestMarginLevelChecker):
    """Test margin alert functionality"""
    
    def test_create_margin_alert(self):
        """Test creating margin alerts"""
        initial_count = len(self.checker.margin_alerts)
        
        # Create warning alert
        self.checker._create_margin_alert(
            MarginStatus.WARNING,
            250.0,
            "Test warning message"
        )
        
        self.assertEqual(len(self.checker.margin_alerts), initial_count + 1)
        
        alert = self.checker.margin_alerts[-1]
        self.assertEqual(alert.alert_type, MarginStatus.WARNING)
        self.assertEqual(alert.margin_level, 250.0)
        self.assertEqual(alert.message, "Test warning message")
        self.assertFalse(alert.acknowledged)
        
    def test_alert_cooldown_prevention(self):
        """Test alert cooldown prevents duplicate alerts"""
        # Create first alert
        self.checker._create_margin_alert(
            MarginStatus.WARNING,
            250.0,
            "First warning"
        )
        
        initial_count = len(self.checker.margin_alerts)
        
        # Try to create similar alert immediately
        self.checker._create_margin_alert(
            MarginStatus.WARNING,
            245.0,
            "Second warning"
        )
        
        # Should not create duplicate
        self.assertEqual(len(self.checker.margin_alerts), initial_count)
        
    def test_acknowledge_alert(self):
        """Test acknowledging alerts"""
        # Create alert
        self.checker._create_margin_alert(
            MarginStatus.CRITICAL,
            140.0,
            "Critical test"
        )
        
        alert = self.checker.margin_alerts[-1]
        alert_id = alert.alert_id
        
        # Acknowledge alert
        success = self.checker.acknowledge_alert(alert_id)
        
        self.assertTrue(success)
        self.assertTrue(alert.acknowledged)
        
        # Try to acknowledge non-existent alert
        fail_success = self.checker.acknowledge_alert("non_existent")
        self.assertFalse(fail_success)

class TestEmergencyHandling(TestMarginLevelChecker):
    """Test emergency situation handling"""
    
    def test_emergency_block_functionality(self):
        """Test emergency block enable/disable"""
        # Enable emergency block
        self.checker.enable_emergency_block("Test emergency", 60)
        
        self.assertTrue(self.checker.emergency_block_active)
        self.assertEqual(self.checker.emergency_block_reason, "Test emergency")
        self.assertIsNotNone(self.checker.emergency_block_expires)
        
        # Disable emergency block
        self.checker.disable_emergency_block()
        
        self.assertFalse(self.checker.emergency_block_active)
        self.assertEqual(self.checker.emergency_block_reason, "")
        self.assertIsNone(self.checker.emergency_block_expires)
        
    def test_emergency_close_handling(self):
        """Test emergency position closing"""
        async def run_test():
            # Set emergency margin level
            mock_account = {
                'balance': 1000.0,
                'equity': 900.0,
                'margin': 850.0,
                'free_margin': 50.0,
                'margin_level': 105.0,  # Below emergency close level
                'credit': 0.0,
                'profit': -100.0
            }
            self.mock_mt5.set_mock_account_info(mock_account)
            
            # Set mock positions
            positions = [
                {'ticket': 12345, 'profit': -50.0, 'margin': 400.0},
                {'ticket': 12346, 'profit': -30.0, 'margin': 450.0}
            ]
            self.mock_mt5.set_mock_positions(positions)
            
            # Handle emergency
            result = await self.checker._handle_emergency_situation(105.0)
            
            self.assertTrue(result)
            
        asyncio.run(run_test())

class TestStatusAndReporting(TestMarginLevelChecker):
    """Test status reporting functionality"""
    
    def test_get_current_status_no_data(self):
        """Test status when no account data available"""
        status = self.checker.get_current_status()
        
        self.assertEqual(status['status'], 'no_data')
        self.assertIn('No account information', status['message'])
        
    def test_get_current_status_with_data(self):
        """Test status with account data"""
        async def run_test():
            # Set account data
            mock_account = {
                'balance': 10000.0,
                'equity': 9500.0,
                'margin': 2000.0,
                'free_margin': 7500.0,
                'margin_level': 475.0,
                'credit': 0.0,
                'profit': -500.0
            }
            self.mock_mt5.set_mock_account_info(mock_account)
            await self.checker._update_account_info()
            
            # Get status
            status = self.checker.get_current_status()
            
            self.assertEqual(status['margin_level'], 475.0)
            self.assertEqual(status['margin_status'], 'safe')
            self.assertEqual(status['account_balance'], 10000.0)
            self.assertEqual(status['account_equity'], 9500.0)
            self.assertEqual(status['free_margin'], 7500.0)
            self.assertFalse(status['emergency_block_active'])
            
        asyncio.run(run_test())
        
    def test_get_recent_alerts(self):
        """Test getting recent alerts"""
        # Create multiple alerts
        self.checker._create_margin_alert(MarginStatus.WARNING, 250.0, "Warning 1")
        self.checker._create_margin_alert(MarginStatus.CRITICAL, 140.0, "Critical 1")
        
        # Get recent alerts
        alerts = self.checker.get_recent_alerts(5)
        
        self.assertEqual(len(alerts), 2)
        # Should be sorted by timestamp (newest first)
        self.assertEqual(alerts[0]['alert_type'], 'critical')
        self.assertEqual(alerts[1]['alert_type'], 'warning')

class TestDataPersistence(TestMarginLevelChecker):
    """Test data persistence functionality"""
    
    def test_margin_data_persistence(self):
        """Test saving and loading margin data"""
        async def run_test():
            # Create account info
            mock_account = {
                'balance': 5000.0,
                'equity': 4800.0,
                'margin': 1000.0,
                'free_margin': 3800.0,
                'margin_level': 480.0,
                'credit': 0.0,
                'profit': -200.0
            }
            self.mock_mt5.set_mock_account_info(mock_account)
            await self.checker._update_account_info()
            
            # Create alert
            self.checker._create_margin_alert(MarginStatus.WARNING, 250.0, "Test persistence")
            
            # Save data
            self.checker._save_margin_data()
            
            # Create new checker instance
            new_checker = MarginLevelChecker(
                config_path=self.temp_config.name,
                log_path=self.temp_log.name
            )
            
            # Check data was loaded
            self.assertGreater(len(new_checker.account_history), 0)
            self.assertGreater(len(new_checker.margin_alerts), 0)
            
            # Check specific data
            last_account = new_checker.account_history[-1]
            self.assertEqual(last_account.balance, 5000.0)
            self.assertEqual(last_account.margin_level, 480.0)
            
            last_alert = new_checker.margin_alerts[-1]
            self.assertEqual(last_alert.alert_type, MarginStatus.WARNING)
            self.assertEqual(last_alert.message, "Test persistence")
            
        asyncio.run(run_test())

if __name__ == '__main__':
    unittest.main()