"""
Signal Simulator for SignalOS
Dry-run system for testing signal processing without executing real trades
"""

import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
import asyncio

class SimulationMode(Enum):
    DRY_RUN = "dry_run"
    BACKTEST = "backtest"
    FORWARD_TEST = "forward_test"
    VALIDATION = "validation"

class SimulationStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class SimulationConfig:
    mode: SimulationMode = SimulationMode.DRY_RUN
    starting_balance: float = 10000.0
    leverage: float = 100.0
    spread_simulation: bool = True
    slippage_simulation: bool = True
    latency_simulation: bool = True
    commission_per_lot: float = 7.0
    max_simulated_trades: int = 1000
    enable_logging: bool = True
    log_file: str = "logs/signal_simulator.log"
    output_format: str = "json"  # json, csv, html

@dataclass
class SimulatedTrade:
    signal_id: str
    symbol: str
    action: str  # BUY, SELL
    volume: float
    entry_price: float
    exit_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    entry_time: datetime = None
    exit_time: Optional[datetime] = None
    pips: Optional[float] = None
    profit_usd: Optional[float] = None
    commission: float = 0.0
    swap: float = 0.0
    status: str = "open"
    comment: str = ""
    
    def __post_init__(self):
        if self.entry_time is None:
            self.entry_time = datetime.now()

@dataclass
class SimulationResult:
    simulation_id: str
    config: SimulationConfig
    trades: List[SimulatedTrade]
    starting_balance: float
    ending_balance: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_pips: float
    max_drawdown: float
    profit_factor: float
    sharpe_ratio: float
    execution_time: float
    start_time: datetime
    end_time: datetime
    status: SimulationStatus

class SignalSimulator:
    def __init__(self, config_file: str = "config.json", log_file: str = "logs/signal_simulator.log"):
        self.config_file = config_file
        self.config = self._load_config()
        self.simulations = {}
        self.active_trades = {}
        self.simulation_history = []
        
        # Setup logging
        self._setup_logging(log_file)
        
        # Injected modules for integration
        self.strategy_runtime = None
        self.mt5_bridge = None
        self.parser = None
        
        # Market data simulation
        self.price_feeds = {}
        self.spread_data = {}
        
    def _load_config(self) -> SimulationConfig:
        """Load simulation configuration from file"""
        try:
            if Path(self.config_file).exists():
                with open(self.config_file, 'r') as f:
                    config_data = json.load(f)
                    sim_config = config_data.get('signal_simulator', {})
                    return SimulationConfig(**sim_config)
            else:
                return self._create_default_config()
        except Exception as e:
            logging.error(f"Failed to load config: {e}")
            return SimulationConfig()

    def _create_default_config(self) -> SimulationConfig:
        """Create default configuration and save to file"""
        default_config = SimulationConfig()
        
        try:
            config_data = {}
            if Path(self.config_file).exists():
                with open(self.config_file, 'r') as f:
                    config_data = json.load(f)
            
            config_data['signal_simulator'] = asdict(default_config)
            
            with open(self.config_file, 'w') as f:
                json.dump(config_data, f, indent=4)
                
        except Exception as e:
            logging.error(f"Failed to save default config: {e}")
        
        return default_config

    def _setup_logging(self, log_file: str):
        """Setup logging for simulation operations"""
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.logger = logging.getLogger('SignalSimulator')
        self.logger.setLevel(logging.INFO)
        
        if not self.logger.handlers:
            # File handler
            file_handler = logging.FileHandler(log_file)
            file_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            file_handler.setFormatter(file_formatter)
            self.logger.addHandler(file_handler)
            
            # Console handler  
            console_handler = logging.StreamHandler()
            console_formatter = logging.Formatter(
                '%(asctime)s - %(levelname)s - %(message)s'
            )
            console_handler.setFormatter(console_formatter)
            self.logger.addHandler(console_handler)

    def inject_modules(self, strategy_runtime=None, mt5_bridge=None, parser=None):
        """Inject module references for integration testing"""
        self.strategy_runtime = strategy_runtime
        self.mt5_bridge = mt5_bridge
        self.parser = parser

    def create_simulation(self, name: str, config: Optional[SimulationConfig] = None) -> str:
        """Create a new simulation session"""
        simulation_id = f"sim_{int(time.time())}_{len(self.simulations)}"
        
        if config is None:
            config = self.config
        
        simulation = {
            'id': simulation_id,
            'name': name,
            'config': config,
            'trades': [],
            'current_balance': config.starting_balance,
            'equity': config.starting_balance,
            'margin_used': 0.0,
            'free_margin': config.starting_balance,
            'start_time': datetime.now(),
            'end_time': None,
            'status': SimulationStatus.PENDING,
            'statistics': {}
        }
        
        self.simulations[simulation_id] = simulation
        self.logger.info(f"Created simulation: {simulation_id} - {name}")
        
        return simulation_id

    def simulate_signal_processing(self, simulation_id: str, signal_data: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate signal processing through the strategy pipeline"""
        if simulation_id not in self.simulations:
            raise ValueError(f"Simulation {simulation_id} not found")
        
        simulation = self.simulations[simulation_id]
        simulation['status'] = SimulationStatus.PROCESSING
        
        try:
            # Step 1: Parse signal (if parser is available)
            parsed_signal = signal_data
            if self.parser:
                try:
                    parsed_signal = self.parser.parse_signal(signal_data.get('content', ''))
                    self.logger.info(f"Signal parsed: {parsed_signal}")
                except Exception as e:
                    self.logger.warning(f"Parser failed, using raw signal: {e}")
            
            # Step 2: Apply strategy runtime logic (if available)
            strategy_result = {
                "action": "execute_normal",
                "signal": parsed_signal,
                "parameters": {},
                "applied_rules": []
            }
            
            if self.strategy_runtime:
                try:
                    # Create signal context for strategy evaluation
                    from strategy_runtime import SignalContext
                    context = SignalContext(
                        signal_data=parsed_signal,
                        market_data=self._get_simulated_market_data(parsed_signal.get('symbol', 'EURUSD')),
                        account_info={
                            'balance': simulation['current_balance'],
                            'equity': simulation['equity'],
                            'margin': simulation['margin_used']
                        }
                    )
                    
                    strategy_result = self.strategy_runtime.evaluate_signal(parsed_signal, context)
                    self.logger.info(f"Strategy evaluation: {strategy_result['action']}")
                    
                except Exception as e:
                    self.logger.warning(f"Strategy runtime failed: {e}")
            
            # Step 3: Simulate trade execution
            execution_result = self._simulate_trade_execution(simulation_id, strategy_result)
            
            # Step 4: Update simulation statistics
            self._update_simulation_statistics(simulation_id)
            
            return {
                'simulation_id': simulation_id,
                'signal_processed': True,
                'strategy_action': strategy_result['action'],
                'trade_executed': execution_result.get('executed', False),
                'trade_details': execution_result,
                'current_balance': simulation['current_balance'],
                'current_equity': simulation['equity']
            }
            
        except Exception as e:
            self.logger.error(f"Signal simulation failed: {e}")
            simulation['status'] = SimulationStatus.FAILED
            return {
                'simulation_id': simulation_id,
                'signal_processed': False,
                'error': str(e)
            }

    def _simulate_trade_execution(self, simulation_id: str, strategy_result: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate trade execution based on strategy result"""
        simulation = self.simulations[simulation_id]
        signal = strategy_result['signal']
        
        # Check if trade should be executed
        if strategy_result['action'] == 'skip_trade':
            return {
                'executed': False,
                'reason': 'Trade skipped by strategy',
                'action': strategy_result['action']
            }
        
        # Extract trade parameters
        symbol = signal.get('symbol', 'EURUSD')
        action = signal.get('action', 'BUY').upper()
        volume = float(signal.get('lot_size', 0.01))
        
        # Get current market price with simulation of spread/slippage
        market_data = self._get_simulated_market_data(symbol)
        entry_price = self._apply_execution_simulation(
            symbol, action, market_data, simulation['config']
        )
        
        # Check margin requirements
        required_margin = self._calculate_required_margin(symbol, volume, entry_price)
        if required_margin > simulation['free_margin']:
            return {
                'executed': False,
                'reason': 'Insufficient margin',
                'required_margin': required_margin,
                'available_margin': simulation['free_margin']
            }
        
        # Create simulated trade
        trade = SimulatedTrade(
            signal_id=signal.get('id', f"sig_{int(time.time())}"),
            symbol=symbol,
            action=action,
            volume=volume,
            entry_price=entry_price,
            stop_loss=signal.get('stop_loss'),
            take_profit=signal.get('take_profit'),
            commission=volume * simulation['config'].commission_per_lot,
            comment=f"Simulated trade from signal"
        )
        
        # Update simulation state
        simulation['trades'].append(trade)
        simulation['margin_used'] += required_margin
        simulation['free_margin'] -= required_margin
        
        self.logger.info(f"Simulated trade: {action} {volume} {symbol} @ {entry_price}")
        
        return {
            'executed': True,
            'trade': asdict(trade),
            'margin_used': required_margin,
            'new_balance': simulation['current_balance'],
            'new_equity': simulation['equity']
        }

    def _get_simulated_market_data(self, symbol: str) -> Dict[str, Any]:
        """Get simulated market data for symbol"""
        # Generate realistic price data
        base_prices = {
            'EURUSD': 1.1000,
            'GBPUSD': 1.2500,
            'USDJPY': 110.00,
            'USDCHF': 0.9200,
            'AUDUSD': 0.7500,
            'USDCAD': 1.2500,
            'NZDUSD': 0.7000,
            'XAUUSD': 2000.00
        }
        
        base_price = base_prices.get(symbol, 1.0000)
        
        # Add small random variation (±0.1%)
        import random
        variation = random.uniform(-0.001, 0.001)
        current_price = base_price * (1 + variation)
        
        # Calculate spread (in pips)
        spread_pips = {
            'EURUSD': 1.5,
            'GBPUSD': 2.0,
            'USDJPY': 1.8,
            'USDCHF': 2.2,
            'AUDUSD': 1.9,
            'USDCAD': 2.1,
            'NZDUSD': 2.5,
            'XAUUSD': 0.5
        }.get(symbol, 2.0)
        
        pip_size = 0.0001 if 'JPY' not in symbol else 0.01
        spread = spread_pips * pip_size
        
        return {
            'symbol': symbol,
            'bid': current_price - spread/2,
            'ask': current_price + spread/2,
            'spread_pips': spread_pips,
            'time': datetime.now().isoformat()
        }

    def _apply_execution_simulation(self, symbol: str, action: str, market_data: Dict[str, Any], config: SimulationConfig) -> float:
        """Apply execution simulation including spread and slippage"""
        bid = market_data['bid']
        ask = market_data['ask']
        
        # Determine execution price based on action
        if action == 'BUY':
            execution_price = ask
        else:  # SELL
            execution_price = bid
        
        # Apply slippage simulation if enabled
        if config.slippage_simulation:
            import random
            # Random slippage between 0-1 pip
            pip_size = 0.0001 if 'JPY' not in symbol else 0.01
            slippage_pips = random.uniform(0, 1)
            slippage = slippage_pips * pip_size
            
            if action == 'BUY':
                execution_price += slippage  # Worse for buyer
            else:
                execution_price -= slippage  # Worse for seller
        
        return execution_price

    def _calculate_required_margin(self, symbol: str, volume: float, price: float) -> float:
        """Calculate required margin for trade"""
        # Standard contract sizes
        contract_sizes = {
            'EURUSD': 100000,
            'GBPUSD': 100000,
            'USDJPY': 100000,
            'USDCHF': 100000,
            'AUDUSD': 100000,
            'USDCAD': 100000,
            'NZDUSD': 100000,
            'XAUUSD': 100
        }
        
        contract_size = contract_sizes.get(symbol, 100000)
        notional_value = volume * contract_size * price
        
        # Calculate margin requirement (assuming 1:100 leverage)
        margin_requirement = notional_value / self.config.leverage
        
        return margin_requirement

    def _update_simulation_statistics(self, simulation_id: str):
        """Update simulation statistics"""
        simulation = self.simulations[simulation_id]
        trades = simulation['trades']
        
        if not trades:
            return
        
        # Calculate basic statistics
        total_trades = len(trades)
        open_trades = len([t for t in trades if t.status == 'open'])
        closed_trades = len([t for t in trades if t.status == 'closed'])
        
        # Calculate P&L for closed trades
        closed_profit = sum([t.profit_usd or 0 for t in trades if t.status == 'closed'])
        
        # Update simulation statistics
        simulation['statistics'] = {
            'total_trades': total_trades,
            'open_trades': open_trades,
            'closed_trades': closed_trades,
            'gross_profit': max(0, closed_profit),
            'gross_loss': min(0, closed_profit),
            'net_profit': closed_profit,
            'balance': simulation['current_balance'] + closed_profit,
            'equity': simulation['equity'],
            'margin_level': (simulation['equity'] / simulation['margin_used']) * 100 if simulation['margin_used'] > 0 else 0
        }

    def close_simulated_trade(self, simulation_id: str, trade_signal_id: str, reason: str = "Manual close") -> Dict[str, Any]:
        """Close a simulated trade"""
        if simulation_id not in self.simulations:
            raise ValueError(f"Simulation {simulation_id} not found")
        
        simulation = self.simulations[simulation_id]
        
        # Find the trade
        trade = None
        for t in simulation['trades']:
            if t.signal_id == trade_signal_id and t.status == 'open':
                trade = t
                break
        
        if not trade:
            return {'closed': False, 'reason': 'Trade not found or already closed'}
        
        # Get current market price
        market_data = self._get_simulated_market_data(trade.symbol)
        
        # Determine exit price
        if trade.action == 'BUY':
            exit_price = market_data['bid']  # Sell at bid
        else:
            exit_price = market_data['ask']   # Buy back at ask
        
        # Calculate profit/loss
        if trade.action == 'BUY':
            price_diff = exit_price - trade.entry_price
        else:
            price_diff = trade.entry_price - exit_price
        
        # Calculate pip value and profit
        pip_size = 0.0001 if 'JPY' not in trade.symbol else 0.01
        pips = price_diff / pip_size
        
        # Standard lot value calculation
        contract_size = 100000 if 'XAU' not in trade.symbol else 100
        profit_usd = price_diff * trade.volume * contract_size
        
        # Apply commission
        total_commission = trade.commission * 2  # Entry + exit
        net_profit = profit_usd - total_commission
        
        # Update trade
        trade.exit_price = exit_price
        trade.exit_time = datetime.now()
        trade.pips = pips
        trade.profit_usd = net_profit
        trade.status = 'closed'
        trade.comment += f" | Closed: {reason}"
        
        # Update simulation balance
        simulation['current_balance'] += net_profit
        simulation['equity'] += net_profit
        
        # Free up margin
        required_margin = self._calculate_required_margin(trade.symbol, trade.volume, trade.entry_price)
        simulation['margin_used'] -= required_margin
        simulation['free_margin'] += required_margin
        
        self.logger.info(f"Closed trade {trade_signal_id}: {pips:.1f} pips, ${net_profit:.2f}")
        
        return {
            'closed': True,
            'trade': asdict(trade),
            'profit_usd': net_profit,
            'pips': pips,
            'new_balance': simulation['current_balance']
        }

    def run_batch_simulation(self, simulation_id: str, signals: List[Dict[str, Any]]) -> SimulationResult:
        """Run batch simulation with multiple signals"""
        if simulation_id not in self.simulations:
            raise ValueError(f"Simulation {simulation_id} not found")
        
        simulation = self.simulations[simulation_id]
        simulation['status'] = SimulationStatus.PROCESSING
        start_time = datetime.now()
        
        self.logger.info(f"Starting batch simulation with {len(signals)} signals")
        
        processed_signals = 0
        successful_trades = 0
        
        try:
            for signal in signals:
                result = self.simulate_signal_processing(simulation_id, signal)
                processed_signals += 1
                
                if result.get('trade_executed', False):
                    successful_trades += 1
                
                # Add small delay to simulate real-time processing
                time.sleep(0.1)
            
            # Close all remaining open trades
            for trade in simulation['trades']:
                if trade.status == 'open':
                    self.close_simulated_trade(simulation_id, trade.signal_id, "Simulation end")
            
            simulation['status'] = SimulationStatus.COMPLETED
            simulation['end_time'] = datetime.now()
            
            # Generate final result
            result = self._generate_simulation_result(simulation_id, start_time)
            
            self.logger.info(f"Batch simulation completed: {processed_signals} signals, {successful_trades} trades")
            
            return result
            
        except Exception as e:
            simulation['status'] = SimulationStatus.FAILED
            self.logger.error(f"Batch simulation failed: {e}")
            raise

    def _generate_simulation_result(self, simulation_id: str, start_time: datetime) -> SimulationResult:
        """Generate comprehensive simulation result"""
        simulation = self.simulations[simulation_id]
        trades = simulation['trades']
        
        # Basic statistics
        total_trades = len(trades)
        winning_trades = len([t for t in trades if t.profit_usd and t.profit_usd > 0])
        losing_trades = len([t for t in trades if t.profit_usd and t.profit_usd < 0])
        
        win_rate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0
        
        # Financial metrics
        starting_balance = simulation['config'].starting_balance
        ending_balance = simulation['current_balance']
        total_pips = sum([t.pips or 0 for t in trades])
        
        # Calculate drawdown
        balance_history = [starting_balance]
        running_balance = starting_balance
        for trade in trades:
            if trade.profit_usd:
                running_balance += trade.profit_usd
                balance_history.append(running_balance)
        
        peak_balance = starting_balance
        max_drawdown = 0
        for balance in balance_history:
            if balance > peak_balance:
                peak_balance = balance
            else:
                drawdown = ((peak_balance - balance) / peak_balance) * 100
                max_drawdown = max(max_drawdown, drawdown)
        
        # Profit factor
        gross_profit = sum([t.profit_usd for t in trades if t.profit_usd and t.profit_usd > 0])
        gross_loss = abs(sum([t.profit_usd for t in trades if t.profit_usd and t.profit_usd < 0]))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        # Sharpe ratio (simplified)
        if total_trades > 1:
            returns = [t.profit_usd / starting_balance for t in trades if t.profit_usd]
            avg_return = sum(returns) / len(returns) if returns else 0
            return_std = (sum([(r - avg_return) ** 2 for r in returns]) / len(returns)) ** 0.5 if returns else 0
            sharpe_ratio = avg_return / return_std if return_std > 0 else 0
        else:
            sharpe_ratio = 0
        
        return SimulationResult(
            simulation_id=simulation_id,
            config=simulation['config'],
            trades=trades,
            starting_balance=starting_balance,
            ending_balance=ending_balance,
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=win_rate,
            total_pips=total_pips,
            max_drawdown=max_drawdown,
            profit_factor=profit_factor,
            sharpe_ratio=sharpe_ratio,
            execution_time=(datetime.now() - start_time).total_seconds(),
            start_time=start_time,
            end_time=datetime.now(),
            status=simulation['status']
        )

    def get_simulation_status(self, simulation_id: str) -> Dict[str, Any]:
        """Get current simulation status"""
        if simulation_id not in self.simulations:
            return {'error': 'Simulation not found'}
        
        simulation = self.simulations[simulation_id]
        
        return {
            'simulation_id': simulation_id,
            'name': simulation['name'],
            'status': simulation['status'].value,
            'current_balance': simulation['current_balance'],
            'equity': simulation['equity'],
            'margin_used': simulation['margin_used'],
            'free_margin': simulation['free_margin'],
            'total_trades': len(simulation['trades']),
            'open_trades': len([t for t in simulation['trades'] if t.status == 'open']),
            'statistics': simulation.get('statistics', {})
        }

    def export_simulation_results(self, simulation_id: str, format: str = "json") -> str:
        """Export simulation results in specified format"""
        if simulation_id not in self.simulations:
            raise ValueError(f"Simulation {simulation_id} not found")
        
        simulation = self.simulations[simulation_id]
        
        if format.lower() == "json":
            export_data = {
                'simulation_id': simulation_id,
                'name': simulation['name'],
                'config': asdict(simulation['config']),
                'trades': [asdict(trade) for trade in simulation['trades']],
                'statistics': simulation.get('statistics', {}),
                'export_time': datetime.now().isoformat()
            }
            
            filename = f"simulation_{simulation_id}_{int(time.time())}.json"
            filepath = Path("logs") / filename
            filepath.parent.mkdir(parents=True, exist_ok=True)
            
            with open(filepath, 'w') as f:
                json.dump(export_data, f, indent=4, default=str)
            
            return str(filepath)
        
        else:
            raise ValueError(f"Unsupported export format: {format}")

    def get_statistics(self) -> Dict[str, Any]:
        """Get overall simulator statistics"""
        total_simulations = len(self.simulations)
        active_simulations = len([s for s in self.simulations.values() if s['status'] == SimulationStatus.PROCESSING])
        completed_simulations = len([s for s in self.simulations.values() if s['status'] == SimulationStatus.COMPLETED])
        
        return {
            'total_simulations': total_simulations,
            'active_simulations': active_simulations,
            'completed_simulations': completed_simulations,
            'available_symbols': list(self._get_simulated_market_data('EURUSD').keys()),
            'simulation_modes': [mode.value for mode in SimulationMode],
            'config': asdict(self.config)
        }


# Example usage
if __name__ == "__main__":
    import asyncio
    
    async def test_signal_simulator():
        """Test signal simulator functionality"""
        simulator = SignalSimulator()
        
        # Create simulation
        sim_id = simulator.create_simulation("Test Simulation")
        
        # Test signals
        test_signals = [
            {
                'id': 'signal_1',
                'content': 'BUY EURUSD Entry: 1.1000 SL: 1.0950 TP: 1.1050',
                'symbol': 'EURUSD',
                'action': 'BUY',
                'lot_size': 0.1,
                'stop_loss': 1.0950,
                'take_profit': 1.1050
            },
            {
                'id': 'signal_2', 
                'content': 'SELL GBPUSD Entry: 1.2500 SL: 1.2550 TP: 1.2450',
                'symbol': 'GBPUSD',
                'action': 'SELL',
                'lot_size': 0.05,
                'stop_loss': 1.2550,
                'take_profit': 1.2450
            }
        ]
        
        # Run batch simulation
        result = simulator.run_batch_simulation(sim_id, test_signals)
        
        print(f"Simulation completed: {result.total_trades} trades")
        print(f"Win rate: {result.win_rate:.1f}%")
        print(f"Total pips: {result.total_pips:.1f}")
        print(f"Final balance: ${result.ending_balance:.2f}")
        
        # Export results
        export_file = simulator.export_simulation_results(sim_id)
        print(f"Results exported to: {export_file}")
    
    # Run test
    asyncio.run(test_signal_simulator())