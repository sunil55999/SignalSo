#!/usr/bin/env python3
"""
Backtesting Engine for SignalOS Desktop Application

Simulates trading signals from historical data and calculates performance metrics.
Includes win-rate, drawdown, risk-reward calculations, and equity curve generation.
"""

import os
import json
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import sqlite3
import random
import math

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class Trade:
    """Individual trade record"""
    id: str
    symbol: str
    entry_time: datetime
    exit_time: Optional[datetime]
    entry_price: float
    exit_price: Optional[float]
    lot_size: float
    direction: str  # 'buy' or 'sell'
    stop_loss: Optional[float]
    take_profit: Optional[float]
    pnl: Optional[float]
    pnl_pips: Optional[float]
    status: str  # 'open', 'closed', 'cancelled'
    signal_provider: str
    signal_text: str
    confidence: float
    risk_reward: Optional[float]

@dataclass
class BacktestResult:
    """Complete backtest results"""
    summary: Dict[str, Any]
    trades: List[Trade]
    equity_curve: List[Dict[str, Any]]
    drawdown_curve: List[Dict[str, Any]]
    monthly_returns: List[Dict[str, Any]]
    statistics: Dict[str, Any]
    performance_metrics: Dict[str, Any]

class MockPriceData:
    """Generate mock price data for backtesting"""
    
    def __init__(self, symbols: List[str] = None):
        self.symbols = symbols or ['EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF', 'AUDUSD', 'USDCAD', 'NZDUSD']
        self.price_data = {}
        self._generate_price_data()
    
    def _generate_price_data(self):
        """Generate realistic forex price data"""
        for symbol in self.symbols:
            # Base prices for major currency pairs
            base_prices = {
                'EURUSD': 1.0800,
                'GBPUSD': 1.2700,
                'USDJPY': 150.00,
                'USDCHF': 0.9200,
                'AUDUSD': 0.6600,
                'USDCAD': 1.3500,
                'NZDUSD': 0.6200
            }
            
            base_price = base_prices.get(symbol, 1.0000)
            
            # Generate 1 year of hourly data
            start_date = datetime.now() - timedelta(days=365)
            data = []
            
            current_price = base_price
            volatility = 0.001  # 0.1% volatility per hour
            
            for i in range(365 * 24):  # 1 year of hourly data
                timestamp = start_date + timedelta(hours=i)
                
                # Generate realistic price movement
                change = random.gauss(0, volatility)
                current_price = current_price * (1 + change)
                
                # Generate OHLC data
                high = current_price * (1 + random.uniform(0, 0.0005))
                low = current_price * (1 - random.uniform(0, 0.0005))
                open_price = current_price
                close_price = current_price
                
                data.append({
                    'timestamp': timestamp,
                    'open': open_price,
                    'high': high,
                    'low': low,
                    'close': close_price,
                    'volume': random.randint(1000, 10000)
                })
            
            self.price_data[symbol] = pd.DataFrame(data)
            logger.info(f"Generated {len(data)} price points for {symbol}")
    
    def get_price_at_time(self, symbol: str, timestamp: datetime) -> Optional[float]:
        """Get price for symbol at specific time"""
        if symbol not in self.price_data:
            return None
        
        df = self.price_data[symbol]
        # Find closest timestamp
        closest_idx = df.iloc[(df['timestamp'] - timestamp).abs().argsort()[:1]].index[0]
        return df.iloc[closest_idx]['close']
    
    def get_price_range(self, symbol: str, start_time: datetime, end_time: datetime) -> pd.DataFrame:
        """Get price data for a time range"""
        if symbol not in self.price_data:
            return pd.DataFrame()
        
        df = self.price_data[symbol]
        mask = (df['timestamp'] >= start_time) & (df['timestamp'] <= end_time)
        return df.loc[mask]

class BacktestEngine:
    """
    Comprehensive backtesting engine for trading signals
    """
    
    def __init__(self, config_file: str = "config.json", log_file: str = "logs/backtest.log"):
        self.config_file = config_file
        self.log_file = log_file
        self.config = self._load_config()
        self._setup_logging()
        
        # Backtesting parameters
        self.initial_balance = self.config.get("initial_balance", 10000.0)
        self.risk_per_trade = self.config.get("risk_per_trade", 0.02)  # 2% per trade
        self.spread_pips = self.config.get("spread_pips", 2)  # 2 pip spread
        self.commission_per_lot = self.config.get("commission_per_lot", 7.0)  # $7 per lot
        
        # Market data
        self.price_data = MockPriceData()
        
        # Results storage
        self.trades = []
        self.equity_curve = []
        self.current_balance = self.initial_balance
        self.peak_balance = self.initial_balance
        self.max_drawdown = 0.0
        
        # Statistics
        self.statistics = {
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'win_rate': 0.0,
            'average_win': 0.0,
            'average_loss': 0.0,
            'profit_factor': 0.0,
            'max_drawdown': 0.0,
            'sharpe_ratio': 0.0,
            'total_pnl': 0.0,
            'total_pips': 0.0
        }
        
        logger.info("BacktestEngine initialized")
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            return {}
    
    def _setup_logging(self):
        """Setup logging configuration"""
        try:
            log_dir = Path(self.log_file).parent
            log_dir.mkdir(exist_ok=True)
            
            file_handler = logging.FileHandler(self.log_file)
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            file_handler.setFormatter(formatter)
            
            logger.addHandler(file_handler)
            logger.setLevel(logging.INFO)
            
        except Exception as e:
            print(f"Failed to setup logging: {e}")
    
    def load_signals_from_file(self, signals_file: str) -> List[Dict[str, Any]]:
        """Load historical signals from file"""
        try:
            with open(signals_file, 'r') as f:
                signals = json.load(f)
            
            logger.info(f"Loaded {len(signals)} signals from {signals_file}")
            return signals
            
        except Exception as e:
            logger.error(f"Failed to load signals: {e}")
            return []
    
    def generate_sample_signals(self, count: int = 100) -> List[Dict[str, Any]]:
        """Generate sample trading signals for testing"""
        signals = []
        base_time = datetime.now() - timedelta(days=30)
        
        signal_templates = [
            "BUY {symbol} @ {price}, SL: {sl}, TP: {tp}",
            "SELL {symbol} @ {price}, SL: {sl}, TP: {tp}",
            "{symbol} BUY SIGNAL - Entry: {price} - SL: {sl} - TP: {tp}",
            "{symbol} SELL SIGNAL - Entry: {price} - SL: {sl} - TP: {tp}",
            "🟢 BUY {symbol} Entry: {price} SL: {sl} TP: {tp}",
            "🔴 SELL {symbol} Entry: {price} SL: {sl} TP: {tp}"
        ]
        
        providers = ["TradingGuru", "ForexPro", "SignalMaster", "PipHunter", "MarketWizard"]
        
        for i in range(count):
            symbol = random.choice(self.price_data.symbols)
            direction = random.choice(['BUY', 'SELL'])
            
            # Generate realistic signal time
            signal_time = base_time + timedelta(hours=random.randint(0, 30 * 24))
            
            # Get price at signal time
            entry_price = self.price_data.get_price_at_time(symbol, signal_time)
            if not entry_price:
                continue
            
            # Generate SL and TP based on direction
            if direction == 'BUY':
                sl = entry_price * (1 - random.uniform(0.005, 0.015))  # 0.5-1.5% SL
                tp = entry_price * (1 + random.uniform(0.01, 0.03))    # 1-3% TP
            else:
                sl = entry_price * (1 + random.uniform(0.005, 0.015))  # 0.5-1.5% SL
                tp = entry_price * (1 - random.uniform(0.01, 0.03))    # 1-3% TP
            
            # Create signal text
            template = random.choice(signal_templates)
            signal_text = template.format(
                symbol=symbol,
                price=f"{entry_price:.5f}",
                sl=f"{sl:.5f}",
                tp=f"{tp:.5f}"
            )
            
            signal = {
                'id': f"signal_{i+1}",
                'timestamp': signal_time.isoformat(),
                'symbol': symbol,
                'direction': direction,
                'entry_price': entry_price,
                'stop_loss': sl,
                'take_profit': tp,
                'signal_text': signal_text,
                'provider': random.choice(providers),
                'confidence': random.uniform(0.6, 0.95),
                'channel': f"@{random.choice(providers).lower()}"
            }
            
            signals.append(signal)
        
        logger.info(f"Generated {len(signals)} sample signals")
        return signals
    
    def calculate_lot_size(self, symbol: str, entry_price: float, stop_loss: float, 
                          risk_amount: float) -> float:
        """Calculate lot size based on risk management"""
        try:
            # Calculate pip value (simplified for major pairs)
            pip_value = 10  # $10 per pip for 1 standard lot
            
            # Calculate distance to stop loss in pips
            if symbol.endswith('JPY'):
                pip_multiplier = 0.01
            else:
                pip_multiplier = 0.0001
            
            sl_distance_pips = abs(entry_price - stop_loss) / pip_multiplier
            
            # Calculate lot size
            if sl_distance_pips > 0:
                lot_size = risk_amount / (sl_distance_pips * pip_value)
                return min(lot_size, 10.0)  # Cap at 10 lots
            
            return 0.1  # Default lot size
            
        except Exception as e:
            logger.error(f"Lot size calculation error: {e}")
            return 0.1
    
    def simulate_trade(self, signal: Dict[str, Any]) -> Trade:
        """Simulate a single trade from signal"""
        try:
            # Parse signal
            symbol = signal['symbol']
            direction = signal['direction'].upper()
            entry_price = signal['entry_price']
            stop_loss = signal.get('stop_loss')
            take_profit = signal.get('take_profit')
            signal_time = datetime.fromisoformat(signal['timestamp'])
            
            # Calculate risk amount
            risk_amount = self.current_balance * self.risk_per_trade
            
            # Calculate lot size
            lot_size = self.calculate_lot_size(symbol, entry_price, stop_loss, risk_amount)
            
            # Create trade
            trade = Trade(
                id=f"trade_{len(self.trades) + 1}",
                symbol=symbol,
                entry_time=signal_time,
                exit_time=None,
                entry_price=entry_price,
                exit_price=None,
                lot_size=lot_size,
                direction=direction,
                stop_loss=stop_loss,
                take_profit=take_profit,
                pnl=None,
                pnl_pips=None,
                status='open',
                signal_provider=signal.get('provider', 'Unknown'),
                signal_text=signal.get('signal_text', ''),
                confidence=signal.get('confidence', 0.5),
                risk_reward=None
            )
            
            # Simulate trade execution over time
            self._simulate_trade_execution(trade)
            
            return trade
            
        except Exception as e:
            logger.error(f"Trade simulation error: {e}")
            return None
    
    def _simulate_trade_execution(self, trade: Trade):
        """Simulate the execution of a trade over time"""
        try:
            # Find exit point within next 24 hours
            max_duration = timedelta(hours=24)
            end_time = trade.entry_time + max_duration
            
            # Get price data for the duration
            price_data = self.price_data.get_price_range(
                trade.symbol, trade.entry_time, end_time
            )
            
            if price_data.empty:
                # Close at entry price if no data
                trade.exit_time = trade.entry_time + timedelta(hours=1)
                trade.exit_price = trade.entry_price
                trade.status = 'closed'
                trade.pnl = 0.0
                trade.pnl_pips = 0.0
                return
            
            # Check each price point for SL/TP hit
            for idx, row in price_data.iterrows():
                current_price = row['close']
                high_price = row['high']
                low_price = row['low']
                
                # Check stop loss and take profit
                if trade.direction == 'BUY':
                    # Check stop loss (price goes down)
                    if trade.stop_loss and low_price <= trade.stop_loss:
                        trade.exit_time = row['timestamp']
                        trade.exit_price = trade.stop_loss
                        trade.status = 'closed'
                        break
                    # Check take profit (price goes up)
                    elif trade.take_profit and high_price >= trade.take_profit:
                        trade.exit_time = row['timestamp']
                        trade.exit_price = trade.take_profit
                        trade.status = 'closed'
                        break
                
                else:  # SELL
                    # Check stop loss (price goes up)
                    if trade.stop_loss and high_price >= trade.stop_loss:
                        trade.exit_time = row['timestamp']
                        trade.exit_price = trade.stop_loss
                        trade.status = 'closed'
                        break
                    # Check take profit (price goes down)
                    elif trade.take_profit and low_price <= trade.take_profit:
                        trade.exit_time = row['timestamp']
                        trade.exit_price = trade.take_profit
                        trade.status = 'closed'
                        break
            
            # If no SL/TP hit, close at last price
            if trade.status == 'open':
                last_row = price_data.iloc[-1]
                trade.exit_time = last_row['timestamp']
                trade.exit_price = last_row['close']
                trade.status = 'closed'
            
            # Calculate P&L
            self._calculate_trade_pnl(trade)
            
        except Exception as e:
            logger.error(f"Trade execution simulation error: {e}")
            trade.status = 'cancelled'
    
    def _calculate_trade_pnl(self, trade: Trade):
        """Calculate trade P&L and update account balance"""
        try:
            if not trade.exit_price:
                return
            
            # Calculate pip difference
            if trade.symbol.endswith('JPY'):
                pip_multiplier = 0.01
            else:
                pip_multiplier = 0.0001
            
            # Calculate pips
            if trade.direction == 'BUY':
                pips = (trade.exit_price - trade.entry_price) / pip_multiplier
            else:
                pips = (trade.entry_price - trade.exit_price) / pip_multiplier
            
            # Apply spread
            pips -= self.spread_pips
            
            # Calculate P&L in dollars
            pip_value = 10  # $10 per pip for 1 standard lot
            gross_pnl = pips * pip_value * trade.lot_size
            commission = self.commission_per_lot * trade.lot_size
            net_pnl = gross_pnl - commission
            
            # Update trade
            trade.pnl = net_pnl
            trade.pnl_pips = pips
            
            # Calculate risk-reward ratio
            if trade.stop_loss:
                risk_pips = abs(trade.entry_price - trade.stop_loss) / pip_multiplier
                reward_pips = pips if pips > 0 else abs(pips)
                if risk_pips > 0:
                    trade.risk_reward = reward_pips / risk_pips
            
            # Update account balance
            self.current_balance += net_pnl
            
            # Update peak balance and drawdown
            if self.current_balance > self.peak_balance:
                self.peak_balance = self.current_balance
            
            current_drawdown = (self.peak_balance - self.current_balance) / self.peak_balance * 100
            self.max_drawdown = max(self.max_drawdown, current_drawdown)
            
            # Log trade
            logger.info(f"Trade {trade.id}: {trade.symbol} {trade.direction} "
                       f"P&L: ${net_pnl:.2f} ({pips:.1f} pips)")
            
        except Exception as e:
            logger.error(f"P&L calculation error: {e}")
    
    def run_backtest(self, signals: List[Dict[str, Any]]) -> BacktestResult:
        """Run complete backtest on provided signals"""
        try:
            logger.info(f"Starting backtest with {len(signals)} signals")
            
            # Reset state
            self.trades = []
            self.equity_curve = []
            self.current_balance = self.initial_balance
            self.peak_balance = self.initial_balance
            self.max_drawdown = 0.0
            
            # Sort signals by timestamp
            signals = sorted(signals, key=lambda x: x['timestamp'])
            
            # Process each signal
            for signal in signals:
                trade = self.simulate_trade(signal)
                if trade:
                    self.trades.append(trade)
                    
                    # Record equity point
                    self.equity_curve.append({
                        'timestamp': trade.exit_time.isoformat() if trade.exit_time else trade.entry_time.isoformat(),
                        'balance': self.current_balance,
                        'drawdown': (self.peak_balance - self.current_balance) / self.peak_balance * 100,
                        'trade_pnl': trade.pnl or 0.0
                    })
            
            # Calculate statistics
            self._calculate_statistics()
            
            # Generate monthly returns
            monthly_returns = self._calculate_monthly_returns()
            
            # Create backtest result
            result = BacktestResult(
                summary=self._generate_summary(),
                trades=self.trades,
                equity_curve=self.equity_curve,
                drawdown_curve=self.equity_curve,  # Same data, different view
                monthly_returns=monthly_returns,
                statistics=self.statistics,
                performance_metrics=self._calculate_performance_metrics()
            )
            
            logger.info(f"Backtest completed. Total trades: {len(self.trades)}, "
                       f"Final balance: ${self.current_balance:.2f}")
            
            return result
            
        except Exception as e:
            logger.error(f"Backtest execution error: {e}")
            return None
    
    def _calculate_statistics(self):
        """Calculate comprehensive trading statistics"""
        try:
            closed_trades = [t for t in self.trades if t.status == 'closed' and t.pnl is not None]
            
            if not closed_trades:
                return
            
            # Basic statistics
            self.statistics['total_trades'] = len(closed_trades)
            winning_trades = [t for t in closed_trades if t.pnl > 0]
            losing_trades = [t for t in closed_trades if t.pnl < 0]
            
            self.statistics['winning_trades'] = len(winning_trades)
            self.statistics['losing_trades'] = len(losing_trades)
            self.statistics['win_rate'] = (len(winning_trades) / len(closed_trades)) * 100
            
            # P&L statistics
            self.statistics['total_pnl'] = sum(t.pnl for t in closed_trades)
            self.statistics['total_pips'] = sum(t.pnl_pips for t in closed_trades if t.pnl_pips)
            
            if winning_trades:
                self.statistics['average_win'] = sum(t.pnl for t in winning_trades) / len(winning_trades)
            if losing_trades:
                self.statistics['average_loss'] = sum(t.pnl for t in losing_trades) / len(losing_trades)
            
            # Profit factor
            gross_profit = sum(t.pnl for t in winning_trades) if winning_trades else 0
            gross_loss = abs(sum(t.pnl for t in losing_trades)) if losing_trades else 0
            
            if gross_loss > 0:
                self.statistics['profit_factor'] = gross_profit / gross_loss
            else:
                self.statistics['profit_factor'] = float('inf') if gross_profit > 0 else 0
            
            # Drawdown
            self.statistics['max_drawdown'] = self.max_drawdown
            
            # Sharpe ratio (simplified)
            if self.equity_curve:
                returns = [point['trade_pnl'] for point in self.equity_curve]
                if returns:
                    avg_return = np.mean(returns)
                    std_return = np.std(returns)
                    self.statistics['sharpe_ratio'] = avg_return / std_return if std_return > 0 else 0
            
            logger.info(f"Statistics calculated: Win rate {self.statistics['win_rate']:.1f}%, "
                       f"Profit factor {self.statistics['profit_factor']:.2f}")
            
        except Exception as e:
            logger.error(f"Statistics calculation error: {e}")
    
    def _calculate_monthly_returns(self) -> List[Dict[str, Any]]:
        """Calculate monthly returns"""
        try:
            monthly_returns = []
            
            if not self.equity_curve:
                return monthly_returns
            
            # Group trades by month
            monthly_data = {}
            for point in self.equity_curve:
                date = datetime.fromisoformat(point['timestamp'])
                month_key = date.strftime('%Y-%m')
                
                if month_key not in monthly_data:
                    monthly_data[month_key] = []
                
                monthly_data[month_key].append(point['trade_pnl'])
            
            # Calculate monthly returns
            for month, pnl_list in monthly_data.items():
                monthly_return = sum(pnl_list)
                monthly_returns.append({
                    'month': month,
                    'return': monthly_return,
                    'trades': len(pnl_list),
                    'win_rate': (len([p for p in pnl_list if p > 0]) / len(pnl_list)) * 100
                })
            
            return monthly_returns
            
        except Exception as e:
            logger.error(f"Monthly returns calculation error: {e}")
            return []
    
    def _generate_summary(self) -> Dict[str, Any]:
        """Generate backtest summary"""
        return {
            'initial_balance': self.initial_balance,
            'final_balance': self.current_balance,
            'total_return': ((self.current_balance - self.initial_balance) / self.initial_balance) * 100,
            'total_trades': len(self.trades),
            'win_rate': self.statistics.get('win_rate', 0),
            'profit_factor': self.statistics.get('profit_factor', 0),
            'max_drawdown': self.max_drawdown,
            'sharpe_ratio': self.statistics.get('sharpe_ratio', 0),
            'backtest_period': f"{self.trades[0].entry_time.date()} to {self.trades[-1].entry_time.date()}" if self.trades else "N/A"
        }
    
    def _calculate_performance_metrics(self) -> Dict[str, Any]:
        """Calculate advanced performance metrics"""
        try:
            metrics = {}
            
            closed_trades = [t for t in self.trades if t.status == 'closed' and t.pnl is not None]
            
            if not closed_trades:
                return metrics
            
            # Return metrics
            metrics['total_return_pct'] = ((self.current_balance - self.initial_balance) / self.initial_balance) * 100
            metrics['annualized_return'] = metrics['total_return_pct']  # Simplified
            
            # Risk metrics
            metrics['max_drawdown_pct'] = self.max_drawdown
            metrics['recovery_factor'] = metrics['total_return_pct'] / self.max_drawdown if self.max_drawdown > 0 else 0
            
            # Trade metrics
            metrics['total_trades'] = len(closed_trades)
            metrics['winning_trades'] = len([t for t in closed_trades if t.pnl > 0])
            metrics['losing_trades'] = len([t for t in closed_trades if t.pnl < 0])
            
            # Average metrics
            metrics['avg_trade_pnl'] = sum(t.pnl for t in closed_trades) / len(closed_trades)
            metrics['avg_win'] = self.statistics.get('average_win', 0)
            metrics['avg_loss'] = self.statistics.get('average_loss', 0)
            
            # Risk-reward metrics
            rr_ratios = [t.risk_reward for t in closed_trades if t.risk_reward]
            if rr_ratios:
                metrics['avg_risk_reward'] = sum(rr_ratios) / len(rr_ratios)
            
            return metrics
            
        except Exception as e:
            logger.error(f"Performance metrics calculation error: {e}")
            return {}
    
    def save_results(self, result: BacktestResult, filename: str = None):
        """Save backtest results to file"""
        try:
            if not filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"backtest_results_{timestamp}.json"
            
            # Convert to serializable format
            data = {
                'summary': result.summary,
                'trades': [asdict(trade) for trade in result.trades],
                'equity_curve': result.equity_curve,
                'drawdown_curve': result.drawdown_curve,
                'monthly_returns': result.monthly_returns,
                'statistics': result.statistics,
                'performance_metrics': result.performance_metrics
            }
            
            with open(filename, 'w') as f:
                json.dump(data, f, indent=2, default=str)
            
            logger.info(f"Backtest results saved to {filename}")
            
        except Exception as e:
            logger.error(f"Failed to save results: {e}")


# Example usage
async def test_backtest():
    """Test the backtesting engine"""
    
    engine = BacktestEngine()
    
    # Generate sample signals
    signals = engine.generate_sample_signals(50)
    
    # Run backtest
    result = engine.run_backtest(signals)
    
    if result:
        print("Backtest Results:")
        print(f"Initial Balance: ${result.summary['initial_balance']:.2f}")
        print(f"Final Balance: ${result.summary['final_balance']:.2f}")
        print(f"Total Return: {result.summary['total_return']:.2f}%")
        print(f"Total Trades: {result.summary['total_trades']}")
        print(f"Win Rate: {result.summary['win_rate']:.1f}%")
        print(f"Profit Factor: {result.summary['profit_factor']:.2f}")
        print(f"Max Drawdown: {result.summary['max_drawdown']:.2f}%")
        print(f"Sharpe Ratio: {result.summary['sharpe_ratio']:.2f}")
        
        # Save results
        engine.save_results(result)
        print("Results saved to file")
    else:
        print("Backtest failed")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_backtest())