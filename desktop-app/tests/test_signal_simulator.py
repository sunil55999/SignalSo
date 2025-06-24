"""
Test Suite for Signal Simulator
Tests dry-run signal processing and trade simulation functionality
"""

import unittest
import json
import tempfile
import os
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from signal_simulator import (
    SignalSimulator, SimulationMode, SimulationStatus, SimulationConfig, 
    SimulatedTrade, SimulationResult
)


class TestSignalSimulator(unittest.TestCase):
    """Unit tests for Signal Simulator"""
    
    def setUp(self):
        """Set up test environment"""
        self.temp_config = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        
        config_data = {
            'signal_simulator': {
                'mode': 'dry_run',
                'starting_balance': 10000.0,
                'leverage': 100.0,
                'commission_per_lot': 7.0,
                'enable_logging': True,
                'log_file': 'logs/test_signal_simulator.log'
            }
        }
        
        json.dump(config_data, self.temp_config)
        self.temp_config.close()
        
        self.simulator = SignalSimulator(config_file=self.temp_config.name)
    
    def tearDown(self):
        """Clean up test environment"""
        os.unlink(self.temp_config.name)
    
    def test_config_loading(self):
        """Test configuration loading from file"""
        self.assertEqual(self.simulator.config.starting_balance, 10000.0)
        self.assertEqual(self.simulator.config.leverage, 100.0)
        self.assertEqual(self.simulator.config.commission_per_lot, 7.0)
    
    def test_create_simulation(self):
        """Test simulation creation"""
        sim_id = self.simulator.create_simulation("Test Simulation")
        
        self.assertIn(sim_id, self.simulator.simulations)
        simulation = self.simulator.simulations[sim_id]
        
        self.assertEqual(simulation['name'], "Test Simulation")
        self.assertEqual(simulation['current_balance'], 10000.0)
        self.assertEqual(simulation['status'], SimulationStatus.PENDING)
        self.assertEqual(len(simulation['trades']), 0)
    
    def test_market_data_simulation(self):
        """Test simulated market data generation"""
        market_data = self.simulator._get_simulated_market_data('EURUSD')
        
        self.assertIn('bid', market_data)
        self.assertIn('ask', market_data)
        self.assertIn('spread_pips', market_data)
        self.assertGreater(market_data['ask'], market_data['bid'])
        self.assertEqual(market_data['symbol'], 'EURUSD')
    
    def test_margin_calculation(self):
        """Test margin requirement calculation"""
        margin = self.simulator._calculate_required_margin('EURUSD', 1.0, 1.1000)
        
        # 1 lot EURUSD = 100,000 units * 1.1000 = 110,000 notional
        # At 1:100 leverage = 1,100 margin requirement
        expected_margin = 110000 / 100
        self.assertAlmostEqual(margin, expected_margin, places=2)
    
    def test_execution_price_simulation(self):
        """Test execution price simulation with spread and slippage"""
        market_data = self.simulator._get_simulated_market_data('EURUSD')
        
        # Test BUY execution (should use ask price + slippage)
        buy_price = self.simulator._apply_execution_simulation(
            'EURUSD', 'BUY', market_data, self.simulator.config
        )
        self.assertGreaterEqual(buy_price, market_data['ask'])
        
        # Test SELL execution (should use bid price - slippage) 
        sell_price = self.simulator._apply_execution_simulation(
            'EURUSD', 'SELL', market_data, self.simulator.config
        )
        self.assertLessEqual(sell_price, market_data['bid'])
    
    def test_signal_processing_without_modules(self):
        """Test signal processing without injected modules"""
        sim_id = self.simulator.create_simulation("Basic Test")
        
        signal_data = {
            'id': 'test_signal',
            'symbol': 'EURUSD',
            'action': 'BUY',
            'lot_size': 0.1,
            'stop_loss': 1.0950,
            'take_profit': 1.1050
        }
        
        result = self.simulator.simulate_signal_processing(sim_id, signal_data)
        
        self.assertTrue(result['signal_processed'])
        self.assertTrue(result['trade_executed'])
        self.assertEqual(result['simulation_id'], sim_id)
        self.assertIn('trade_details', result)
    
    def test_signal_processing_with_strategy_runtime(self):
        """Test signal processing with mocked strategy runtime"""
        # Mock strategy runtime
        mock_strategy = Mock()
        mock_strategy.evaluate_signal.return_value = {
            'action': 'execute_normal',
            'signal': {
                'symbol': 'EURUSD',
                'action': 'BUY', 
                'lot_size': 0.1,
                'stop_loss': 1.0950,
                'take_profit': 1.1050
            },
            'parameters': {},
            'applied_rules': []
        }
        
        self.simulator.inject_modules(strategy_runtime=mock_strategy)
        
        sim_id = self.simulator.create_simulation("Strategy Test")
        signal_data = {
            'id': 'strategy_signal',
            'symbol': 'EURUSD',
            'action': 'BUY',
            'lot_size': 0.1
        }
        
        result = self.simulator.simulate_signal_processing(sim_id, signal_data)
        
        self.assertTrue(result['signal_processed'])
        self.assertEqual(result['strategy_action'], 'execute_normal')
        mock_strategy.evaluate_signal.assert_called_once()
    
    def test_signal_processing_skip_trade(self):
        """Test signal processing when strategy skips trade"""
        # Mock strategy that skips trade
        mock_strategy = Mock()
        mock_strategy.evaluate_signal.return_value = {
            'action': 'skip_trade',
            'signal': {'symbol': 'EURUSD'},
            'parameters': {},
            'applied_rules': [{'rule_name': 'risk_filter', 'reason': 'High risk'}]
        }
        
        self.simulator.inject_modules(strategy_runtime=mock_strategy)
        
        sim_id = self.simulator.create_simulation("Skip Test")
        signal_data = {'id': 'skip_signal', 'symbol': 'EURUSD'}
        
        result = self.simulator.simulate_signal_processing(sim_id, signal_data)
        
        self.assertTrue(result['signal_processed'])
        self.assertFalse(result['trade_executed'])
        self.assertEqual(result['strategy_action'], 'skip_trade')
    
    def test_insufficient_margin_handling(self):
        """Test handling of insufficient margin scenarios"""
        # Create simulation with low balance
        config = SimulationConfig(starting_balance=100.0)  # Very low balance
        sim_id = self.simulator.create_simulation("Low Margin Test", config)
        
        # Try to place large trade
        signal_data = {
            'id': 'large_trade',
            'symbol': 'EURUSD',
            'action': 'BUY',
            'lot_size': 10.0  # Very large lot size
        }
        
        result = self.simulator.simulate_signal_processing(sim_id, signal_data)
        
        self.assertTrue(result['signal_processed'])
        self.assertFalse(result['trade_executed'])
        self.assertIn('Insufficient margin', result['trade_details']['reason'])
    
    def test_trade_closure(self):
        """Test trade closure functionality"""
        sim_id = self.simulator.create_simulation("Closure Test")
        
        # Execute a trade first
        signal_data = {
            'id': 'close_test_signal',
            'symbol': 'EURUSD', 
            'action': 'BUY',
            'lot_size': 0.1
        }
        
        self.simulator.simulate_signal_processing(sim_id, signal_data)
        
        # Close the trade
        close_result = self.simulator.close_simulated_trade(
            sim_id, 'close_test_signal', 'Test closure'
        )
        
        self.assertTrue(close_result['closed'])
        self.assertIn('profit_usd', close_result)
        self.assertIn('pips', close_result)
        
        # Verify trade is marked as closed
        simulation = self.simulator.simulations[sim_id]
        trade = simulation['trades'][0]
        self.assertEqual(trade.status, 'closed')
        self.assertIsNotNone(trade.exit_price)
        self.assertIsNotNone(trade.profit_usd)
    
    def test_batch_simulation(self):
        """Test batch simulation with multiple signals"""
        sim_id = self.simulator.create_simulation("Batch Test")
        
        signals = [
            {
                'id': 'batch_1',
                'symbol': 'EURUSD',
                'action': 'BUY',
                'lot_size': 0.1
            },
            {
                'id': 'batch_2',
                'symbol': 'GBPUSD',
                'action': 'SELL', 
                'lot_size': 0.05
            },
            {
                'id': 'batch_3',
                'symbol': 'USDJPY',
                'action': 'BUY',
                'lot_size': 0.02
            }
        ]
        
        result = self.simulator.run_batch_simulation(sim_id, signals)
        
        self.assertIsInstance(result, SimulationResult)
        self.assertEqual(result.total_trades, 3)
        self.assertEqual(result.status, SimulationStatus.COMPLETED)
        self.assertGreater(result.execution_time, 0)
    
    def test_simulation_statistics_calculation(self):
        """Test simulation statistics calculations"""
        sim_id = self.simulator.create_simulation("Stats Test")
        
        # Add some simulated trades manually for testing
        simulation = self.simulator.simulations[sim_id]
        
        # Winning trade
        winning_trade = SimulatedTrade(
            signal_id='win_1',
            symbol='EURUSD',
            action='BUY',
            volume=0.1,
            entry_price=1.1000,
            exit_price=1.1050,
            profit_usd=50.0,
            status='closed'
        )
        
        # Losing trade
        losing_trade = SimulatedTrade(
            signal_id='loss_1',
            symbol='GBPUSD',
            action='SELL',
            volume=0.1,
            entry_price=1.2500,
            exit_price=1.2530,
            profit_usd=-30.0,
            status='closed'
        )
        
        simulation['trades'] = [winning_trade, losing_trade]
        
        # Update statistics
        self.simulator._update_simulation_statistics(sim_id)
        
        stats = simulation['statistics']
        self.assertEqual(stats['total_trades'], 2)
        self.assertEqual(stats['closed_trades'], 2)
        self.assertEqual(stats['gross_profit'], 50.0)
        self.assertEqual(stats['gross_loss'], -30.0)
        self.assertEqual(stats['net_profit'], 20.0)
    
    def test_simulation_result_generation(self):
        """Test comprehensive simulation result generation"""
        sim_id = self.simulator.create_simulation("Result Test")
        start_time = datetime.now()
        
        # Add test trades
        simulation = self.simulator.simulations[sim_id]
        test_trades = [
            SimulatedTrade('t1', 'EURUSD', 'BUY', 0.1, 1.1000, 1.1050, profit_usd=50.0, pips=50.0, status='closed'),
            SimulatedTrade('t2', 'GBPUSD', 'SELL', 0.1, 1.2500, 1.2480, profit_usd=20.0, pips=20.0, status='closed'),
            SimulatedTrade('t3', 'USDJPY', 'BUY', 0.1, 110.00, 109.50, profit_usd=-50.0, pips=-50.0, status='closed')
        ]
        simulation['trades'] = test_trades
        simulation['current_balance'] = 10020.0  # Starting + net profit
        
        result = self.simulator._generate_simulation_result(sim_id, start_time)
        
        self.assertEqual(result.total_trades, 3)
        self.assertEqual(result.winning_trades, 2)
        self.assertEqual(result.losing_trades, 1)
        self.assertAlmostEqual(result.win_rate, 66.67, places=1)
        self.assertEqual(result.total_pips, 20.0)
        self.assertEqual(result.ending_balance, 10020.0)
        self.assertGreater(result.profit_factor, 0)
    
    def test_simulation_status_reporting(self):
        """Test simulation status reporting"""
        sim_id = self.simulator.create_simulation("Status Test")
        
        status = self.simulator.get_simulation_status(sim_id)
        
        self.assertEqual(status['simulation_id'], sim_id)
        self.assertEqual(status['name'], "Status Test")
        self.assertEqual(status['current_balance'], 10000.0)
        self.assertEqual(status['total_trades'], 0)
        self.assertEqual(status['open_trades'], 0)
    
    def test_simulation_export(self):
        """Test simulation results export"""
        sim_id = self.simulator.create_simulation("Export Test")
        
        # Add a test trade
        self.simulator.simulate_signal_processing(sim_id, {
            'id': 'export_signal',
            'symbol': 'EURUSD',
            'action': 'BUY',
            'lot_size': 0.1
        })
        
        # Export results
        export_path = self.simulator.export_simulation_results(sim_id, "json")
        
        self.assertTrue(os.path.exists(export_path))
        
        # Verify export content
        with open(export_path, 'r') as f:
            export_data = json.load(f)
        
        self.assertEqual(export_data['simulation_id'], sim_id)
        self.assertIn('trades', export_data)
        self.assertIn('statistics', export_data)
        
        # Clean up export file
        os.unlink(export_path)
    
    def test_overall_statistics(self):
        """Test overall simulator statistics"""
        # Create multiple simulations
        sim1 = self.simulator.create_simulation("Test 1")
        sim2 = self.simulator.create_simulation("Test 2")
        
        # Process one simulation
        self.simulator.simulations[sim1]['status'] = SimulationStatus.PROCESSING
        self.simulator.simulations[sim2]['status'] = SimulationStatus.COMPLETED
        
        stats = self.simulator.get_statistics()
        
        self.assertEqual(stats['total_simulations'], 2)
        self.assertEqual(stats['active_simulations'], 1)
        self.assertEqual(stats['completed_simulations'], 1)
        self.assertIn('simulation_modes', stats)
        self.assertIn('config', stats)
    
    def test_error_handling(self):
        """Test error handling scenarios"""
        # Test invalid simulation ID
        status = self.simulator.get_simulation_status("invalid_id")
        self.assertIn('error', status)
        
        # Test closing non-existent trade
        sim_id = self.simulator.create_simulation("Error Test")
        close_result = self.simulator.close_simulated_trade(sim_id, "non_existent", "Test")
        self.assertFalse(close_result['closed'])
        
        # Test export with invalid simulation
        with self.assertRaises(ValueError):
            self.simulator.export_simulation_results("invalid_id")
    
    def test_different_symbols_and_calculations(self):
        """Test different symbol types and their calculations"""
        symbols_to_test = ['EURUSD', 'USDJPY', 'XAUUSD', 'GBPUSD']
        
        for symbol in symbols_to_test:
            with self.subTest(symbol=symbol):
                market_data = self.simulator._get_simulated_market_data(symbol)
                
                self.assertEqual(market_data['symbol'], symbol)
                self.assertGreater(market_data['ask'], market_data['bid'])
                self.assertGreater(market_data['spread_pips'], 0)
                
                # Test margin calculation
                margin = self.simulator._calculate_required_margin(symbol, 1.0, market_data['ask'])
                self.assertGreater(margin, 0)


class TestSignalSimulatorIntegration(unittest.TestCase):
    """Integration tests for Signal Simulator"""
    
    def setUp(self):
        """Set up integration test environment"""
        self.simulator = SignalSimulator()
    
    def test_realistic_trading_scenario(self):
        """Test realistic trading scenario with mixed results"""
        sim_id = self.simulator.create_simulation("Realistic Trading")
        
        # Simulate a realistic trading day
        signals = [
            {'id': 'morning_eur', 'symbol': 'EURUSD', 'action': 'BUY', 'lot_size': 0.2},
            {'id': 'midday_gbp', 'symbol': 'GBPUSD', 'action': 'SELL', 'lot_size': 0.1},
            {'id': 'afternoon_jpy', 'symbol': 'USDJPY', 'action': 'BUY', 'lot_size': 0.15},
            {'id': 'evening_aud', 'symbol': 'AUDUSD', 'action': 'SELL', 'lot_size': 0.05},
            {'id': 'night_gold', 'symbol': 'XAUUSD', 'action': 'BUY', 'lot_size': 0.01}
        ]
        
        # Process signals
        for signal in signals:
            result = self.simulator.simulate_signal_processing(sim_id, signal)
            self.assertTrue(result['signal_processed'])
        
        # Verify simulation state
        simulation = self.simulator.simulations[sim_id]
        self.assertGreater(len(simulation['trades']), 0)
        self.assertGreater(simulation['margin_used'], 0)
        
        # Close some trades manually (simulate partial trading day)
        for i, trade in enumerate(simulation['trades'][:3]):
            if trade.status == 'open':
                close_result = self.simulator.close_simulated_trade(
                    sim_id, trade.signal_id, f"End of session {i+1}"
                )
                self.assertTrue(close_result['closed'])
        
        # Check final status
        final_status = self.simulator.get_simulation_status(sim_id)
        self.assertIn('current_balance', final_status)
        self.assertIn('total_trades', final_status)


if __name__ == '__main__':
    unittest.main(verbosity=2)