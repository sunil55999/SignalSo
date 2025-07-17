#!/usr/bin/env python3
"""
Advanced Strategy Core Engine for SignalOS Desktop Application

Core strategy engine that handles risk management, breakeven logic, 
partial closes, TP1/2/3 management, and prop firm rules integration.
"""

import json
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
import sqlite3
import math

# Local imports
from strategy.prop_firm_mode import PropFirmMode, PropFirmConfig, RuleViolation

class StrategyType(Enum):
    """Strategy execution types"""
    CONSERVATIVE = "conservative"
    BALANCED = "balanced"
    AGGRESSIVE = "aggressive"
    CUSTOM = "custom"

class RiskLevel(Enum):
    """Risk level categories"""
    VERY_LOW = "very_low"    # 0.5% per trade
    LOW = "low"              # 1% per trade
    MEDIUM = "medium"        # 2% per trade
    HIGH = "high"            # 3% per trade
    VERY_HIGH = "very_high"  # 5% per trade

class TradePhase(Enum):
    """Trade execution phases"""
    ENTRY = "entry"
    BREAKEVEN = "breakeven"
    PARTIAL_CLOSE = "partial_close"
    FULL_CLOSE = "full_close"
    STOPPED_OUT = "stopped_out"

class ExitReason(Enum):
    """Trade exit reasons"""
    TP1_HIT = "tp1_hit"
    TP2_HIT = "tp2_hit"
    TP3_HIT = "tp3_hit"
    STOP_LOSS = "stop_loss"
    BREAKEVEN = "breakeven"
    MANUAL_CLOSE = "manual_close"
    PROP_FIRM_RULE = "prop_firm_rule"
    TIME_EXPIRY = "time_expiry"

@dataclass
class RiskParameters:
    """Risk management parameters"""
    account_risk_percent: float = 2.0
    max_daily_risk_percent: float = 10.0
    max_drawdown_percent: float = 20.0
    position_correlation_limit: float = 0.7
    max_positions_per_symbol: int = 3
    max_total_positions: int = 10
    emergency_stop_loss_percent: float = 25.0

@dataclass
class BreakevenConfig:
    """Breakeven configuration"""
    enabled: bool = True
    trigger_distance_pips: float = 10.0
    trigger_percentage: float = 50.0  # % of distance to TP1
    buffer_pips: float = 2.0
    only_when_profitable: bool = True
    min_profit_pips: float = 5.0

@dataclass
class PartialCloseConfig:
    """Partial close configuration"""
    enabled: bool = True
    tp1_close_percent: float = 50.0
    tp2_close_percent: float = 30.0
    tp3_close_percent: float = 20.0
    trail_remaining_position: bool = True
    trail_start_pips: float = 15.0
    trail_step_pips: float = 5.0

@dataclass
class PositionSize:
    """Position sizing calculation"""
    lot_size: float
    risk_amount: float
    risk_percent: float
    stop_loss_pips: float
    pip_value: float
    account_balance: float
    calculation_method: str

@dataclass
class TradeExecution:
    """Trade execution plan"""
    symbol: str
    direction: str
    entry_price: float
    stop_loss: float
    take_profits: List[float]
    position_size: PositionSize
    risk_parameters: RiskParameters
    strategy_type: StrategyType
    execution_time: datetime
    expiry_time: Optional[datetime] = None
    
    # Execution state
    phase: TradePhase = TradePhase.ENTRY
    breakeven_triggered: bool = False
    partial_closes: List[Dict[str, Any]] = None
    current_sl: float = None
    remaining_lots: float = None
    
    def __post_init__(self):
        if self.partial_closes is None:
            self.partial_closes = []
        if self.current_sl is None:
            self.current_sl = self.stop_loss
        if self.remaining_lots is None:
            self.remaining_lots = self.position_size.lot_size

@dataclass
class StrategyConfig:
    """Strategy configuration"""
    # Core settings
    strategy_type: StrategyType = StrategyType.BALANCED
    risk_level: RiskLevel = RiskLevel.MEDIUM
    
    # Risk management
    risk_params: RiskParameters = None
    breakeven_config: BreakevenConfig = None
    partial_close_config: PartialCloseConfig = None
    
    # Prop firm integration
    prop_firm_mode: bool = False
    prop_firm_config: Optional[PropFirmConfig] = None
    
    # Advanced features
    enable_correlation_filter: bool = True
    enable_news_filter: bool = True
    enable_time_filter: bool = True
    enable_spread_filter: bool = True
    
    # Performance settings
    max_concurrent_trades: int = 10
    position_sizing_method: str = "fixed_percent"
    
    def __post_init__(self):
        if self.risk_params is None:
            self.risk_params = RiskParameters()
        if self.breakeven_config is None:
            self.breakeven_config = BreakevenConfig()
        if self.partial_close_config is None:
            self.partial_close_config = PartialCloseConfig()

class StrategyCore:
    """Advanced Strategy Core Engine"""
    
    def __init__(self, config_file: str = "config.json", log_file: str = "logs/strategy_core.log"):
        self.config_file = config_file
        self.log_file = log_file
        self.config = self._load_config()
        self._setup_logging()
        
        # Initialize prop firm mode if enabled
        self.prop_firm = PropFirmMode(config_file) if self.config.prop_firm_mode else None
        
        # Initialize strategy database
        self.strategy_db = self._init_strategy_database()
        
        # Active trades tracking
        self.active_trades: Dict[str, TradeExecution] = {}
        
        # Performance tracking
        self.performance_stats = {
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "breakeven_trades": 0,
            "total_pnl": 0.0,
            "max_drawdown": 0.0,
            "win_rate": 0.0,
            "avg_win": 0.0,
            "avg_loss": 0.0,
            "profit_factor": 0.0
        }
        
        self.logger.info("Strategy Core Engine initialized")
    
    def _load_config(self) -> StrategyConfig:
        """Load strategy configuration"""
        try:
            with open(self.config_file, 'r') as f:
                config_data = json.load(f)
                strategy_config = config_data.get('strategy_core', {})
                
                # Convert nested configurations
                if 'risk_params' in strategy_config:
                    strategy_config['risk_params'] = RiskParameters(**strategy_config['risk_params'])
                if 'breakeven_config' in strategy_config:
                    strategy_config['breakeven_config'] = BreakevenConfig(**strategy_config['breakeven_config'])
                if 'partial_close_config' in strategy_config:
                    strategy_config['partial_close_config'] = PartialCloseConfig(**strategy_config['partial_close_config'])
                
                return StrategyConfig(**strategy_config)
                
        except Exception as e:
            self.logger.warning(f"Failed to load strategy config, using defaults: {e}")
            return StrategyConfig()
    
    def _setup_logging(self):
        """Setup logging for strategy core"""
        self.logger = logging.getLogger('StrategyCore')
        self.logger.setLevel(logging.INFO)
        
        if not self.logger.handlers:
            Path(self.log_file).parent.mkdir(parents=True, exist_ok=True)
            
            file_handler = logging.FileHandler(self.log_file)
            file_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            file_handler.setFormatter(file_formatter)
            self.logger.addHandler(file_handler)
    
    def _init_strategy_database(self) -> sqlite3.Connection:
        """Initialize strategy database"""
        try:
            db_path = Path("logs/strategy_core.db")
            db_path.parent.mkdir(parents=True, exist_ok=True)
            
            db = sqlite3.connect(str(db_path))
            
            # Create tables
            db.execute('''
                CREATE TABLE IF NOT EXISTS trade_executions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trade_id TEXT UNIQUE,
                    symbol TEXT,
                    direction TEXT,
                    entry_price REAL,
                    stop_loss REAL,
                    take_profits TEXT,
                    lot_size REAL,
                    risk_amount REAL,
                    execution_time TEXT,
                    exit_time TEXT,
                    exit_reason TEXT,
                    pnl REAL,
                    phase TEXT,
                    breakeven_triggered INTEGER,
                    partial_closes TEXT
                )
            ''')
            
            db.execute('''
                CREATE TABLE IF NOT EXISTS strategy_performance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT,
                    total_trades INTEGER,
                    winning_trades INTEGER,
                    losing_trades INTEGER,
                    total_pnl REAL,
                    max_drawdown REAL,
                    win_rate REAL,
                    profit_factor REAL
                )
            ''')
            
            db.commit()
            return db
            
        except Exception as e:
            self.logger.error(f"Failed to initialize strategy database: {e}")
            return None
    
    def calculate_position_size(self, symbol: str, entry_price: float, stop_loss: float, 
                              account_balance: float, risk_percent: Optional[float] = None) -> PositionSize:
        """
        Calculate optimal position size based on risk management rules
        
        Args:
            symbol: Trading symbol
            entry_price: Entry price
            stop_loss: Stop loss price
            account_balance: Account balance
            risk_percent: Risk percentage (override config default)
            
        Returns:
            PositionSize object with calculation details
        """
        try:
            # Use provided risk or config default
            if risk_percent is None:
                risk_percent = self.config.risk_params.account_risk_percent
            
            # Calculate risk amount
            risk_amount = account_balance * (risk_percent / 100)
            
            # Calculate stop loss distance in pips
            pip_multiplier = self._get_pip_multiplier(symbol)
            sl_distance_pips = abs(entry_price - stop_loss) * pip_multiplier
            
            # Calculate pip value (for standard lot)
            pip_value = self._calculate_pip_value(symbol, account_balance)
            
            # Calculate lot size
            if sl_distance_pips > 0 and pip_value > 0:
                lot_size = risk_amount / (sl_distance_pips * pip_value)
            else:
                lot_size = 0.01  # Minimum lot size
            
            # Apply position limits
            lot_size = self._apply_position_limits(lot_size, symbol)
            
            return PositionSize(
                lot_size=round(lot_size, 2),
                risk_amount=risk_amount,
                risk_percent=risk_percent,
                stop_loss_pips=sl_distance_pips,
                pip_value=pip_value,
                account_balance=account_balance,
                calculation_method=self.config.position_sizing_method
            )
            
        except Exception as e:
            self.logger.error(f"Error calculating position size: {e}")
            return PositionSize(
                lot_size=0.01,
                risk_amount=0.0,
                risk_percent=0.0,
                stop_loss_pips=0.0,
                pip_value=0.0,
                account_balance=account_balance,
                calculation_method="fallback"
            )
    
    def _get_pip_multiplier(self, symbol: str) -> float:
        """Get pip multiplier for symbol"""
        if "JPY" in symbol:
            return 100  # 2 decimal places
        elif "XAU" in symbol or "XAG" in symbol:
            return 10   # 1 decimal place
        else:
            return 10000  # 4 decimal places
    
    def _calculate_pip_value(self, symbol: str, account_balance: float) -> float:
        """Calculate pip value for position sizing"""
        # Simplified pip value calculation
        # In production, this would query real-time rates
        base_currency = symbol[:3]
        quote_currency = symbol[3:]
        
        if quote_currency == "USD":
            return 10.0  # $10 per pip for standard lot
        elif base_currency == "USD":
            return 10.0  # Approximate value
        else:
            return 10.0  # Default value
    
    def _apply_position_limits(self, lot_size: float, symbol: str) -> float:
        """Apply position size limits"""
        # Minimum lot size
        lot_size = max(lot_size, 0.01)
        
        # Maximum lot size based on risk parameters
        max_lot_size = self.config.risk_params.max_daily_risk_percent / 100
        lot_size = min(lot_size, max_lot_size)
        
        # Prop firm limits
        if self.prop_firm:
            prop_limit = self.prop_firm.get_max_position_size(symbol)
            lot_size = min(lot_size, prop_limit)
        
        return lot_size
    
    async def create_trade_execution(self, signal_data: Dict[str, Any], 
                                   account_balance: float) -> Optional[TradeExecution]:
        """
        Create trade execution plan from parsed signal
        
        Args:
            signal_data: Parsed signal data
            account_balance: Current account balance
            
        Returns:
            TradeExecution plan or None if validation fails
        """
        try:
            # Validate signal data
            if not self._validate_signal_data(signal_data):
                return None
            
            # Check prop firm rules
            if self.prop_firm and not await self.prop_firm.validate_trade_rules(signal_data):
                self.logger.warning("Trade blocked by prop firm rules")
                return None
            
            # Calculate position size
            position_size = self.calculate_position_size(
                signal_data['symbol'],
                signal_data['entry_price'],
                signal_data['stop_loss'],
                account_balance
            )
            
            # Create trade execution
            trade_execution = TradeExecution(
                symbol=signal_data['symbol'],
                direction=signal_data['direction'],
                entry_price=signal_data['entry_price'],
                stop_loss=signal_data['stop_loss'],
                take_profits=signal_data.get('take_profits', []),
                position_size=position_size,
                risk_parameters=self.config.risk_params,
                strategy_type=self.config.strategy_type,
                execution_time=datetime.now()
            )
            
            # Generate trade ID
            trade_id = self._generate_trade_id(trade_execution)
            
            # Store in active trades
            self.active_trades[trade_id] = trade_execution
            
            # Log trade creation
            self.logger.info(f"Created trade execution: {trade_id} - {signal_data['symbol']}")
            
            return trade_execution
            
        except Exception as e:
            self.logger.error(f"Error creating trade execution: {e}")
            return None
    
    def _validate_signal_data(self, signal_data: Dict[str, Any]) -> bool:
        """Validate signal data completeness"""
        required_fields = ['symbol', 'direction', 'entry_price', 'stop_loss']
        
        for field in required_fields:
            if field not in signal_data or signal_data[field] is None:
                self.logger.warning(f"Missing required field: {field}")
                return False
        
        # Validate price logic
        entry = signal_data['entry_price']
        sl = signal_data['stop_loss']
        direction = signal_data['direction'].upper()
        
        if direction == "BUY" and entry <= sl:
            self.logger.warning("Invalid BUY signal: entry price <= stop loss")
            return False
        elif direction == "SELL" and entry >= sl:
            self.logger.warning("Invalid SELL signal: entry price >= stop loss")
            return False
        
        return True
    
    def _generate_trade_id(self, trade: TradeExecution) -> str:
        """Generate unique trade ID"""
        timestamp = trade.execution_time.strftime("%Y%m%d_%H%M%S")
        return f"{trade.symbol}_{trade.direction}_{timestamp}"
    
    async def process_breakeven(self, trade_id: str, current_price: float) -> bool:
        """
        Process breakeven logic for active trade
        
        Args:
            trade_id: Trade identifier
            current_price: Current market price
            
        Returns:
            True if breakeven was triggered
        """
        try:
            if trade_id not in self.active_trades:
                return False
            
            trade = self.active_trades[trade_id]
            
            # Skip if already triggered or disabled
            if trade.breakeven_triggered or not self.config.breakeven_config.enabled:
                return False
            
            # Calculate breakeven trigger distance
            trigger_distance = self._calculate_breakeven_trigger(trade, current_price)
            
            if trigger_distance <= 0:
                return False
            
            # Check if trigger conditions are met
            if self._should_trigger_breakeven(trade, current_price, trigger_distance):
                # Calculate new stop loss
                new_sl = self._calculate_breakeven_sl(trade, current_price)
                
                # Update trade
                trade.current_sl = new_sl
                trade.breakeven_triggered = True
                trade.phase = TradePhase.BREAKEVEN
                
                # Log breakeven
                self.logger.info(f"Breakeven triggered for {trade_id}: SL moved to {new_sl}")
                
                # Update database
                self._update_trade_in_db(trade_id, trade)
                
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error processing breakeven: {e}")
            return False
    
    def _calculate_breakeven_trigger(self, trade: TradeExecution, current_price: float) -> float:
        """Calculate breakeven trigger distance"""
        if not trade.take_profits:
            return 0
        
        tp1 = trade.take_profits[0]
        entry = trade.entry_price
        
        # Calculate distance to TP1
        tp_distance = abs(tp1 - entry)
        
        # Calculate trigger distance based on configuration
        trigger_distance = tp_distance * (self.config.breakeven_config.trigger_percentage / 100)
        
        return trigger_distance
    
    def _should_trigger_breakeven(self, trade: TradeExecution, current_price: float, 
                                trigger_distance: float) -> bool:
        """Check if breakeven should be triggered"""
        entry = trade.entry_price
        direction = trade.direction.upper()
        
        if direction == "BUY":
            return current_price >= entry + trigger_distance
        else:  # SELL
            return current_price <= entry - trigger_distance
    
    def _calculate_breakeven_sl(self, trade: TradeExecution, current_price: float) -> float:
        """Calculate breakeven stop loss level"""
        entry = trade.entry_price
        direction = trade.direction.upper()
        buffer = self.config.breakeven_config.buffer_pips / self._get_pip_multiplier(trade.symbol)
        
        if direction == "BUY":
            return entry + buffer
        else:  # SELL
            return entry - buffer
    
    async def process_partial_close(self, trade_id: str, current_price: float) -> List[Dict[str, Any]]:
        """
        Process partial close logic for active trade
        
        Args:
            trade_id: Trade identifier
            current_price: Current market price
            
        Returns:
            List of partial close actions
        """
        try:
            if trade_id not in self.active_trades:
                return []
            
            trade = self.active_trades[trade_id]
            
            if not self.config.partial_close_config.enabled or not trade.take_profits:
                return []
            
            partial_closes = []
            
            # Check each TP level
            for i, tp_level in enumerate(trade.take_profits):
                # Skip if already closed
                if any(pc.get('tp_level') == i + 1 for pc in trade.partial_closes):
                    continue
                
                # Check if TP level is hit
                if self._is_tp_hit(trade, current_price, tp_level):
                    close_percent = self._get_close_percent(i + 1)
                    lots_to_close = trade.remaining_lots * (close_percent / 100)
                    
                    # Create partial close action
                    partial_close = {
                        'tp_level': i + 1,
                        'close_percent': close_percent,
                        'lots_to_close': lots_to_close,
                        'price': tp_level,
                        'timestamp': datetime.now().isoformat()
                    }
                    
                    # Update trade
                    trade.partial_closes.append(partial_close)
                    trade.remaining_lots -= lots_to_close
                    trade.phase = TradePhase.PARTIAL_CLOSE
                    
                    partial_closes.append(partial_close)
                    
                    self.logger.info(f"Partial close triggered for {trade_id}: TP{i+1} at {tp_level}")
            
            # Update database if partial closes occurred
            if partial_closes:
                self._update_trade_in_db(trade_id, trade)
            
            return partial_closes
            
        except Exception as e:
            self.logger.error(f"Error processing partial close: {e}")
            return []
    
    def _is_tp_hit(self, trade: TradeExecution, current_price: float, tp_level: float) -> bool:
        """Check if TP level is hit"""
        direction = trade.direction.upper()
        
        if direction == "BUY":
            return current_price >= tp_level
        else:  # SELL
            return current_price <= tp_level
    
    def _get_close_percent(self, tp_level: int) -> float:
        """Get close percentage for TP level"""
        if tp_level == 1:
            return self.config.partial_close_config.tp1_close_percent
        elif tp_level == 2:
            return self.config.partial_close_config.tp2_close_percent
        elif tp_level == 3:
            return self.config.partial_close_config.tp3_close_percent
        else:
            return 20.0  # Default for additional TPs
    
    def _update_trade_in_db(self, trade_id: str, trade: TradeExecution):
        """Update trade in database"""
        try:
            if self.strategy_db:
                self.strategy_db.execute(
                    '''INSERT OR REPLACE INTO trade_executions 
                       (trade_id, symbol, direction, entry_price, stop_loss, take_profits, 
                        lot_size, risk_amount, execution_time, phase, breakeven_triggered, partial_closes)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                    (trade_id, trade.symbol, trade.direction, trade.entry_price, 
                     trade.stop_loss, json.dumps(trade.take_profits), trade.position_size.lot_size,
                     trade.position_size.risk_amount, trade.execution_time.isoformat(),
                     trade.phase.value, int(trade.breakeven_triggered), json.dumps(trade.partial_closes))
                )
                self.strategy_db.commit()
        except Exception as e:
            self.logger.error(f"Failed to update trade in database: {e}")
    
    def record_trade_exit(self, trade_id: str, exit_price: float, exit_reason: ExitReason, 
                         pnl: float):
        """Record trade exit"""
        try:
            if trade_id in self.active_trades:
                trade = self.active_trades[trade_id]
                trade.phase = TradePhase.FULL_CLOSE
                
                # Update statistics
                self.performance_stats["total_trades"] += 1
                self.performance_stats["total_pnl"] += pnl
                
                if pnl > 0:
                    self.performance_stats["winning_trades"] += 1
                elif pnl < 0:
                    self.performance_stats["losing_trades"] += 1
                else:
                    self.performance_stats["breakeven_trades"] += 1
                
                # Update database
                if self.strategy_db:
                    self.strategy_db.execute(
                        '''UPDATE trade_executions 
                           SET exit_time = ?, exit_reason = ?, pnl = ?, phase = ?
                           WHERE trade_id = ?''',
                        (datetime.now().isoformat(), exit_reason.value, pnl, 
                         TradePhase.FULL_CLOSE.value, trade_id)
                    )
                    self.strategy_db.commit()
                
                # Remove from active trades
                del self.active_trades[trade_id]
                
                self.logger.info(f"Trade exit recorded: {trade_id} - PnL: {pnl}")
                
        except Exception as e:
            self.logger.error(f"Error recording trade exit: {e}")
    
    def get_active_trades(self) -> Dict[str, TradeExecution]:
        """Get all active trades"""
        return self.active_trades.copy()
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        stats = self.performance_stats.copy()
        
        # Calculate derived metrics
        if stats["total_trades"] > 0:
            stats["win_rate"] = stats["winning_trades"] / stats["total_trades"] * 100
            
            if stats["losing_trades"] > 0:
                stats["profit_factor"] = abs(stats["total_pnl"] / stats["losing_trades"])
            else:
                stats["profit_factor"] = float('inf')
        
        return stats
    
    def cleanup(self):
        """Cleanup resources"""
        if self.strategy_db:
            self.strategy_db.close()
        self.logger.info("Strategy core cleanup completed")

# Configuration example
def create_default_strategy_config() -> Dict[str, Any]:
    """Create default strategy configuration"""
    return {
        "strategy_core": {
            "strategy_type": "balanced",
            "risk_level": "medium",
            "prop_firm_mode": False,
            "enable_correlation_filter": True,
            "enable_news_filter": True,
            "max_concurrent_trades": 10,
            "position_sizing_method": "fixed_percent",
            "risk_params": {
                "account_risk_percent": 2.0,
                "max_daily_risk_percent": 10.0,
                "max_drawdown_percent": 20.0,
                "max_positions_per_symbol": 3,
                "max_total_positions": 10
            },
            "breakeven_config": {
                "enabled": True,
                "trigger_distance_pips": 10.0,
                "trigger_percentage": 50.0,
                "buffer_pips": 2.0,
                "only_when_profitable": True
            },
            "partial_close_config": {
                "enabled": True,
                "tp1_close_percent": 50.0,
                "tp2_close_percent": 30.0,
                "tp3_close_percent": 20.0,
                "trail_remaining_position": True
            }
        }
    }

if __name__ == "__main__":
    # Example usage
    async def main():
        strategy = StrategyCore()
        
        # Test signal data
        signal_data = {
            'symbol': 'EURUSD',
            'direction': 'BUY',
            'entry_price': 1.0850,
            'stop_loss': 1.0800,
            'take_profits': [1.0900, 1.0950, 1.1000]
        }
        
        # Create trade execution
        trade_execution = await strategy.create_trade_execution(signal_data, 10000.0)
        
        if trade_execution:
            print(f"Trade created: {trade_execution.symbol}")
            print(f"Position size: {trade_execution.position_size.lot_size}")
            print(f"Risk amount: ${trade_execution.position_size.risk_amount}")
        
        strategy.cleanup()
    
    asyncio.run(main())