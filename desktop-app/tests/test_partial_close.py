"""
Test Suite for Partial Close Engine
Tests percentage-based and lot-based partial trade closures
"""

import unittest
import asyncio
import json
import tempfile
import os
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from partial_close import PartialCloseEngine, PartialCloseRequest, CloseType, PartialCloseResult


class TestPartialCloseEngine(unittest.TestCase):
    
    def setUp(self):
        """Set up test environment"""
        # Create temporary config file
        self.temp_config = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        self.temp_log = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        
        config_data = {
            'partial_close': {
                'min_lot_size': 0.01,
                'max_percentage': 95.0,
                'min_percentage': 5.0,
                'precision_digits': 2,
                'max_retries': 3,
                'retry_delay': 0.1
            }
        }
        
        json.dump(config_data, self.temp_config)
        self.temp_config.close()
        
        json.dump([], self.temp_log)
        self.temp_log.close()
        
        self.engine = PartialCloseEngine(
            config_file=self.temp_config.name,
            log_file=self.temp_log.name
        )
        
        # Mock MT5 bridge
        self.mock_mt5_bridge = Mock()
        self.mock_mt5_bridge.get_position_info = AsyncMock()
        self.mock_mt5_bridge.partial_close_position = AsyncMock()
        self.engine.inject_modules(mt5_bridge=self.mock_mt5_bridge)
    
    def tearDown(self):
        """Clean up test environment"""
        os.unlink(self.temp_config.name)
        os.unlink(self.temp_log.name)
    
    def test_parse_percentage_commands(self):
        """Test parsing percentage-based close commands"""
        test_cases = [
            ("/CLOSE 50%", CloseType.PERCENTAGE, 50.0),
            ("CLOSE 25%", CloseType.PERCENTAGE, 25.0),
            ("/PARTIAL 75%", CloseType.PERCENTAGE, 75.0),
            ("PARTIAL 10%", CloseType.PERCENTAGE, 10.0),
            ("close 33.5%", CloseType.PERCENTAGE, 33.5),
        ]
        
        for command, expected_type, expected_value in test_cases:
            with self.subTest(command=command):
                result = self.engine.parse_close_command(command)
                self.assertIsNotNone(result)
                self.assertEqual(result.close_type, expected_type)
                self.assertEqual(result.close_value, expected_value)
    
    def test_parse_lot_commands(self):
        """Test parsing lot-based close commands"""
        test_cases = [
            ("/CLOSE 1.0", CloseType.LOT_SIZE, 1.0),
            ("CLOSE 0.5 lots", CloseType.LOT_SIZE, 0.5),
            ("/PARTIAL 2.5", CloseType.LOT_SIZE, 2.5),
            ("PARTIAL 0.1 lot", CloseType.LOT_SIZE, 0.1),
            ("close 1.75", CloseType.LOT_SIZE, 1.75),
        ]
        
        for command, expected_type, expected_value in test_cases:
            with self.subTest(command=command):
                result = self.engine.parse_close_command(command)
                self.assertIsNotNone(result)
                self.assertEqual(result.close_type, expected_type)
                self.assertEqual(result.close_value, expected_value)
    
    def test_parse_invalid_commands(self):
        """Test parsing invalid commands"""
        invalid_commands = [
            "/CLOSE 200%",  # Over max percentage
            "CLOSE 2%",     # Under min percentage
            "/CLOSE 0.001", # Under min lot size
            "CLOSE",        # Missing value
            "INVALID",      # Not a close command
            "",             # Empty string
            None,           # None value
        ]
        
        for command in invalid_commands:
            with self.subTest(command=command):
                result = self.engine.parse_close_command(command)
                self.assertIsNone(result)
    
    def test_calculate_close_lots_percentage(self):
        """Test lot calculation for percentage-based closes"""
        test_cases = [
            (50.0, 1.0, 0.5),   # 50% of 1.0 lot
            (25.0, 2.0, 0.5),   # 25% of 2.0 lots
            (75.0, 0.4, 0.3),   # 75% of 0.4 lots
            (10.0, 0.05, 0.01), # 10% of 0.05 lots (min lot applied)
        ]
        
        for percentage, current_lots, expected_close in test_cases:
            with self.subTest(percentage=percentage, current_lots=current_lots):
                request = PartialCloseRequest(
                    signal_id=1,
                    ticket=12345,
                    close_type=CloseType.PERCENTAGE,
                    close_value=percentage,
                    symbol="EURUSD",
                    original_lots=current_lots
                )
                
                result = self.engine.calculate_close_lots(request, current_lots)
                self.assertEqual(result, expected_close)
    
    def test_calculate_close_lots_lot_size(self):
        """Test lot calculation for lot-based closes"""
        test_cases = [
            (0.5, 1.0, 0.5),   # Close 0.5 lots from 1.0 lot
            (2.0, 1.5, 1.5),   # Close 2.0 lots from 1.5 lots (capped)
            (0.25, 0.3, 0.25), # Close 0.25 lots from 0.3 lots
            (0.005, 0.1, 0.01), # Close 0.005 lots (min lot applied)
        ]
        
        for close_lots, current_lots, expected_close in test_cases:
            with self.subTest(close_lots=close_lots, current_lots=current_lots):
                request = PartialCloseRequest(
                    signal_id=1,
                    ticket=12345,
                    close_type=CloseType.LOT_SIZE,
                    close_value=close_lots,
                    symbol="EURUSD",
                    original_lots=current_lots
                )
                
                result = self.engine.calculate_close_lots(request, current_lots)
                self.assertEqual(result, expected_close)
    
    @patch('partial_close.datetime')
    async def test_execute_partial_close_success(self, mock_datetime):
        """Test successful partial close execution"""
        # Mock datetime
        mock_now = datetime(2025, 6, 23, 10, 0, 0)
        mock_datetime.now.return_value = mock_now
        
        # Setup mock responses
        self.mock_mt5_bridge.get_position_info.return_value = {
            'success': True,
            'data': {
                'lots': 1.0,
                'current_price': 1.2500
            }
        }
        
        self.mock_mt5_bridge.partial_close_position.return_value = {
            'success': True,
            'new_ticket': 67890
        }
        
        # Create test request
        request = PartialCloseRequest(
            signal_id=1,
            ticket=12345,
            close_type=CloseType.PERCENTAGE,
            close_value=50.0,
            symbol="EURUSD",
            original_lots=1.0,
            comment="Test partial close"
        )
        
        # Execute partial close
        result = await self.engine.execute_partial_close(request)
        
        # Verify result
        self.assertTrue(result.success)
        self.assertEqual(result.new_ticket, 67890)
        self.assertEqual(result.closed_lots, 0.5)
        self.assertEqual(result.remaining_lots, 0.5)
        self.assertEqual(result.close_price, 1.2500)
        self.assertEqual(result.execution_time, mock_now)
        
        # Verify MT5 bridge calls
        self.mock_mt5_bridge.get_position_info.assert_called_once_with(12345)
        self.mock_mt5_bridge.partial_close_position.assert_called_once_with(
            ticket=12345,
            lots=0.5,
            price=1.2500,
            comment="Test partial close"
        )
    
    async def test_execute_partial_close_position_not_found(self):
        """Test partial close when position is not found"""
        # Setup mock response
        self.mock_mt5_bridge.get_position_info.return_value = {
            'success': False,
            'error': 'Position not found'
        }
        
        # Create test request
        request = PartialCloseRequest(
            signal_id=1,
            ticket=12345,
            close_type=CloseType.PERCENTAGE,
            close_value=50.0,
            symbol="EURUSD",
            original_lots=1.0
        )
        
        # Execute partial close
        result = await self.engine.execute_partial_close(request)
        
        # Verify result
        self.assertFalse(result.success)
        self.assertEqual(result.error_message, "Could not retrieve position information")
    
    async def test_execute_partial_close_mt5_error(self):
        """Test partial close when MT5 returns error"""
        # Setup mock responses
        self.mock_mt5_bridge.get_position_info.return_value = {
            'success': True,
            'data': {
                'lots': 1.0,
                'current_price': 1.2500
            }
        }
        
        self.mock_mt5_bridge.partial_close_position.return_value = {
            'success': False,
            'error': 'Insufficient margin'
        }
        
        # Create test request
        request = PartialCloseRequest(
            signal_id=1,
            ticket=12345,
            close_type=CloseType.PERCENTAGE,
            close_value=50.0,
            symbol="EURUSD",
            original_lots=1.0
        )
        
        # Execute partial close
        result = await self.engine.execute_partial_close(request)
        
        # Verify result
        self.assertFalse(result.success)
        self.assertEqual(result.error_message, "Insufficient margin")
    
    async def test_execute_partial_close_no_mt5_bridge(self):
        """Test partial close without MT5 bridge"""
        # Remove MT5 bridge
        self.engine.mt5_bridge = None
        
        # Create test request
        request = PartialCloseRequest(
            signal_id=1,
            ticket=12345,
            close_type=CloseType.PERCENTAGE,
            close_value=50.0,
            symbol="EURUSD",
            original_lots=1.0
        )
        
        # Execute partial close
        result = await self.engine.execute_partial_close(request)
        
        # Verify result
        self.assertFalse(result.success)
        self.assertEqual(result.error_message, "MT5 bridge not available")
    
    def test_get_statistics_empty(self):
        """Test statistics with no close history"""
        stats = self.engine.get_close_statistics()
        
        expected = {
            'total_operations': 0,
            'successful_operations': 0,
            'failed_operations': 0,
            'success_rate': 0.0,
            'total_lots_closed': 0.0,
            'most_common_close_type': None
        }
        
        self.assertEqual(stats, expected)
    
    def test_get_statistics_with_history(self):
        """Test statistics with close history"""
        # Add test history
        self.engine.close_history = [
            {
                'success': True,
                'closed_lots': 0.5,
                'close_type': 'percentage'
            },
            {
                'success': True,
                'closed_lots': 1.0,
                'close_type': 'percentage'
            },
            {
                'success': False,
                'closed_lots': 0.0,
                'close_type': 'lot_size'
            }
        ]
        
        stats = self.engine.get_close_statistics()
        
        self.assertEqual(stats['total_operations'], 3)
        self.assertEqual(stats['successful_operations'], 2)
        self.assertEqual(stats['failed_operations'], 1)
        self.assertEqual(stats['success_rate'], 66.67)  # Rounded
        self.assertEqual(stats['total_lots_closed'], 1.5)
        self.assertEqual(stats['most_common_close_type'], 'percentage')
    
    def test_get_recent_closes(self):
        """Test getting recent close operations"""
        # Add test history
        test_history = [
            {'id': 1, 'timestamp': '2025-06-23T09:00:00'},
            {'id': 2, 'timestamp': '2025-06-23T09:01:00'},
            {'id': 3, 'timestamp': '2025-06-23T09:02:00'},
        ]
        
        self.engine.close_history = test_history
        
        # Test default limit
        recent = self.engine.get_recent_closes()
        self.assertEqual(len(recent), 3)
        self.assertEqual(recent, test_history)
        
        # Test custom limit
        recent = self.engine.get_recent_closes(limit=2)
        self.assertEqual(len(recent), 2)
        self.assertEqual(recent, test_history[-2:])


class TestPartialCloseIntegration(unittest.TestCase):
    """Integration tests for partial close functionality"""
    
    def setUp(self):
        """Set up integration test environment"""
        self.temp_config = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        self.temp_log = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        
        config_data = {
            'partial_close': {
                'min_lot_size': 0.01,
                'max_percentage': 95.0,
                'min_percentage': 5.0,
                'precision_digits': 2,
                'max_retries': 2,
                'retry_delay': 0.1
            }
        }
        
        json.dump(config_data, self.temp_config)
        self.temp_config.close()
        
        json.dump([], self.temp_log)
        self.temp_log.close()
        
        self.engine = PartialCloseEngine(
            config_file=self.temp_config.name,
            log_file=self.temp_log.name
        )
    
    def tearDown(self):
        """Clean up integration test environment"""
        os.unlink(self.temp_config.name)
        os.unlink(self.temp_log.name)
    
    def test_end_to_end_percentage_flow(self):
        """Test complete flow from command parsing to lot calculation"""
        # Parse command
        command = "/CLOSE 60%"
        parsed_request = self.engine.parse_close_command(command)
        
        self.assertIsNotNone(parsed_request)
        if parsed_request:
            self.assertEqual(parsed_request.close_type, CloseType.PERCENTAGE)
            self.assertEqual(parsed_request.close_value, 60.0)
            
            # Calculate lots
            current_lots = 1.5
            close_lots = self.engine.calculate_close_lots(parsed_request, current_lots)
        
        self.assertEqual(close_lots, 0.9)  # 60% of 1.5
    
    def test_end_to_end_lot_flow(self):
        """Test complete flow for lot-based commands"""
        # Parse command
        command = "PARTIAL 0.75 lots"
        parsed_request = self.engine.parse_close_command(command)
        
        self.assertIsNotNone(parsed_request)
        if parsed_request:
            self.assertEqual(parsed_request.close_type, CloseType.LOT_SIZE)
            self.assertEqual(parsed_request.close_value, 0.75)
            
            # Calculate lots
            current_lots = 1.0
            close_lots = self.engine.calculate_close_lots(parsed_request, current_lots)
        
        self.assertEqual(close_lots, 0.75)
    
    def test_edge_case_very_small_position(self):
        """Test edge case with very small position size"""
        command = "/CLOSE 50%"
        parsed_request = self.engine.parse_close_command(command)
        
        if parsed_request:
            # Very small position
            current_lots = 0.02
            close_lots = self.engine.calculate_close_lots(parsed_request, current_lots)
        
        # Should apply minimum lot size
        self.assertEqual(close_lots, 0.01)
    
    def test_edge_case_close_more_than_available(self):
        """Test edge case when trying to close more than available"""
        command = "/CLOSE 2.0"
        parsed_request = self.engine.parse_close_command(command)
        
        if parsed_request:
            # Position smaller than close request
            current_lots = 1.0
            close_lots = self.engine.calculate_close_lots(parsed_request, current_lots)
        
        # Should be capped at available lots
        self.assertEqual(close_lots, 1.0)


if __name__ == '__main__':
    # Run tests
    unittest.main(verbosity=2)