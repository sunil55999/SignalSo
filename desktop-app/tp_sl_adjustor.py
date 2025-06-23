"""
TP/SL Adjustor Engine for SignalOS
Dynamically adjusts stop loss and take profit levels based on spread conditions, pip buffers, and market volatility
"""

import json
import time
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import os

class AdjustmentType(Enum):
    SPREAD_BASED = "spread_based"
    PIP_BUFFER = "pip_buffer"
    PERCENTAGE = "percentage"
    VOLATILITY = "volatility"
    MANUAL = "manual"

class AdjustmentReason(Enum):
    HIGH_SPREAD = "high_spread"
    LOW_SPREAD = "low_spread"
    VOLATILITY_INCREASE = "volatility_increase"
    VOLATILITY_DECREASE = "volatility_decrease"
    BROKER_MINIMUM = "broker_minimum"
    MANUAL_OVERRIDE = "manual_override"
    PERIODIC_REVIEW = "periodic_review"

@dataclass
class AdjustmentRule:
    symbol: str
    adjustment_type: AdjustmentType
    trigger_condition: float  # Spread threshold, volatility level, etc.
    sl_adjustment_pips: float
    tp_adjustment_pips: float
    min_distance_pips: float  # Minimum distance from current price
    max_adjustment_pips: float  # Maximum adjustment allowed
    enabled: bool = True

@dataclass
class AdjustmentEvent:
    ticket: int
    symbol: str
    adjustment_type: AdjustmentType
    reason: AdjustmentReason
    old_sl: Optional[float]
    new_sl: Optional[float]
    old_tp: Optional[float]
    new_tp: Optional[float]
    adjustment_pips_sl: float
    adjustment_pips_tp: float
    timestamp: datetime
    success: bool
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ticket": self.ticket,
            "symbol": self.symbol,
            "adjustment_type": self.adjustment_type.value,
            "reason": self.reason.value,
            "old_sl": self.old_sl,
            "new_sl": self.new_sl,
            "old_tp": self.old_tp,
            "new_tp": self.new_tp,
            "adjustment_pips_sl": self.adjustment_pips_sl,
            "adjustment_pips_tp": self.adjustment_pips_tp,
            "timestamp": self.timestamp.isoformat(),
            "success": self.success,
            "error_message": self.error_message
        }

@dataclass
class TradeInfo:
    ticket: int
    symbol: str
    direction: str  # "buy" or "sell"
    entry_price: float
    current_sl: Optional[float]
    current_tp: Optional[float]
    volume: float
    open_time: datetime
    last_adjustment: Optional[datetime] = None

class TPSLAdjustor:
    def __init__(self, config_path: str = "config.json", log_path: str = "logs/tp_sl_adjustments.log"):
        self.config_path = config_path
        self.log_path = log_path
        self.config = self._load_config()
        self.logger = self._setup_logger()
        
        # Adjustment rules
        self.adjustment_rules: Dict[str, List[AdjustmentRule]] = {}
        self.adjustment_history: List[AdjustmentEvent] = []
        
        # Module dependencies
        self.mt5_bridge = None
        self.spread_checker = None
        self.tp_manager = None
        self.sl_manager = None
        
        # Market data cache
        self.market_data_cache: Dict[str, Dict[str, Any]] = {}
        self.cache_duration = 2  # seconds
        
        # Background monitoring
        self.monitoring_task = None
        self.is_monitoring = False
        
        # Load adjustment rules
        self._load_adjustment_rules()
        
    def _load_config(self) -> Dict[str, Any]:
        """Load TP/SL adjustor configuration"""
        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)
                
            if "tp_sl_adjustor" not in config:
                config["tp_sl_adjustor"] = {
                    "enabled": True,
                    "monitoring_interval": 30.0,  # Check every 30 seconds
                    "min_adjustment_interval": 300,  # Min 5 minutes between adjustments
                    "default_spread_threshold": 3.0,  # Pips
                    "default_sl_buffer_pips": 2.0,
                    "default_tp_buffer_pips": 2.0,
                    "max_adjustment_per_session": 5.0,  # Max 5 pips adjustment per session
                    "enable_volatility_adjustments": True,
                    "enable_spread_adjustments": True,
                    "symbol_specific_rules": {
                        "EURUSD": {
                            "spread_threshold": 2.0,
                            "sl_buffer_pips": 1.5,
                            "tp_buffer_pips": 1.5,
                            "min_distance_pips": 10.0,
                            "max_adjustment_pips": 3.0
                        },
                        "GBPUSD": {
                            "spread_threshold": 2.5,
                            "sl_buffer_pips": 2.0,
                            "tp_buffer_pips": 2.0,
                            "min_distance_pips": 12.0,
                            "max_adjustment_pips": 4.0
                        },
                        "XAUUSD": {
                            "spread_threshold": 8.0,
                            "sl_buffer_pips": 5.0,
                            "tp_buffer_pips": 5.0,
                            "min_distance_pips": 50.0,
                            "max_adjustment_pips": 20.0
                        }
                    }
                }
                self._save_config(config)
                
            return config.get("tp_sl_adjustor", {})
            
        except FileNotFoundError:
            self.logger.warning(f"Config file not found: {self.config_path}, using defaults")
            return self._get_default_config()
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in config file: {e}")
            return self._get_default_config()
            
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration"""
        return {
            "enabled": True,
            "monitoring_interval": 30.0,
            "min_adjustment_interval": 300,
            "default_spread_threshold": 3.0,
            "default_sl_buffer_pips": 2.0,
            "default_tp_buffer_pips": 2.0,
            "max_adjustment_per_session": 5.0,
            "enable_volatility_adjustments": True,
            "enable_spread_adjustments": True,
            "symbol_specific_rules": {}
        }
        
    def _save_config(self, full_config: Dict[str, Any]):
        """Save updated configuration"""
        try:
            with open(self.config_path, 'w') as f:
                json.dump(full_config, f, indent=4)
        except Exception as e:
            self.logger.error(f"Failed to save config: {e}")
            
    def _setup_logger(self) -> logging.Logger:
        """Setup dedicated logger for TP/SL adjustments"""
        logger = logging.getLogger("tp_sl_adjustor")
        logger.setLevel(logging.INFO)
        
        # Create logs directory if it doesn't exist
        os.makedirs(os.path.dirname(self.log_path), exist_ok=True)
        
        # File handler
        file_handler = logging.FileHandler(self.log_path)
        file_handler.setLevel(logging.INFO)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.WARNING)
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        if not logger.handlers:
            logger.addHandler(file_handler)
            logger.addHandler(console_handler)
            
        return logger
        
    def _load_adjustment_rules(self):
        """Load adjustment rules from configuration"""
        symbol_rules = self.config.get("symbol_specific_rules", {})
        
        for symbol, rules in symbol_rules.items():
            self.adjustment_rules[symbol] = []
            
            # Create spread-based adjustment rule
            if self.config.get("enable_spread_adjustments", True):
                spread_rule = AdjustmentRule(
                    symbol=symbol,
                    adjustment_type=AdjustmentType.SPREAD_BASED,
                    trigger_condition=rules.get("spread_threshold", self.config.get("default_spread_threshold", 3.0)),
                    sl_adjustment_pips=rules.get("sl_buffer_pips", self.config.get("default_sl_buffer_pips", 2.0)),
                    tp_adjustment_pips=rules.get("tp_buffer_pips", self.config.get("default_tp_buffer_pips", 2.0)),
                    min_distance_pips=rules.get("min_distance_pips", 10.0),
                    max_adjustment_pips=rules.get("max_adjustment_pips", self.config.get("max_adjustment_per_session", 5.0))
                )
                self.adjustment_rules[symbol].append(spread_rule)
                
    def set_dependencies(self, mt5_bridge=None, spread_checker=None, tp_manager=None, sl_manager=None):
        """Set module dependencies"""
        self.mt5_bridge = mt5_bridge
        self.spread_checker = spread_checker
        self.tp_manager = tp_manager
        self.sl_manager = sl_manager
        
    def _get_pip_value(self, symbol: str) -> float:
        """Get pip value for symbol"""
        pip_values = {
            "EURUSD": 0.00001, "GBPUSD": 0.00001, "AUDUSD": 0.00001,
            "NZDUSD": 0.00001, "USDCAD": 0.00001, "USDCHF": 0.00001,
            "USDJPY": 0.001, "EURJPY": 0.001, "GBPJPY": 0.001,
            "EURGBP": 0.00001, "EURAUD": 0.00001, "EURCHF": 0.00001,
            "XAUUSD": 0.01, "XAGUSD": 0.001,
            "BTCUSD": 1.0, "ETHUSD": 0.1
        }
        return pip_values.get(symbol, 0.00001)
        
    def _get_market_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get current market data for symbol"""
        try:
            # Check cache first
            if symbol in self.market_data_cache:
                cached_data, cache_time = self.market_data_cache[symbol]
                if time.time() - cache_time < self.cache_duration:
                    return cached_data
                    
            if not self.mt5_bridge:
                self.logger.warning("MT5 bridge not available")
                return None
                
            # Get tick data and spread info
            tick_data = self.mt5_bridge.get_symbol_tick(symbol)
            if not tick_data:
                return None
                
            # Get spread from spread checker if available
            spread_pips = 0
            if self.spread_checker:
                spread_result, spread_info = self.spread_checker.check_spread_before_trade(symbol)
                if spread_info:
                    spread_pips = spread_info.get('spread_pips', 0)
            else:
                # Calculate spread manually
                bid = tick_data.get('bid', 0)
                ask = tick_data.get('ask', 0)
                pip_value = self._get_pip_value(symbol)
                spread_pips = (ask - bid) / pip_value if pip_value > 0 else 0
                
            market_data = {
                'symbol': symbol,
                'bid': tick_data.get('bid', 0),
                'ask': tick_data.get('ask', 0),
                'last': tick_data.get('last', 0),
                'spread_pips': spread_pips,
                'time': tick_data.get('time', datetime.now())
            }
            
            # Cache the result
            self.market_data_cache[symbol] = (market_data, time.time())
            return market_data
            
        except Exception as e:
            self.logger.error(f"Error getting market data for {symbol}: {e}")
            return None
            
    def _get_open_trades(self) -> List[TradeInfo]:
        """Get list of open trades from MT5"""
        try:
            if not self.mt5_bridge:
                return []
                
            positions = self.mt5_bridge.get_open_positions()
            if not positions:
                return []
                
            trades = []
            for position in positions:
                trade_info = TradeInfo(
                    ticket=position.get('ticket', 0),
                    symbol=position.get('symbol', ''),
                    direction='buy' if position.get('type', 0) == 0 else 'sell',
                    entry_price=position.get('price_open', 0),
                    current_sl=position.get('sl', None) if position.get('sl', 0) != 0 else None,
                    current_tp=position.get('tp', None) if position.get('tp', 0) != 0 else None,
                    volume=position.get('volume', 0),
                    open_time=position.get('time', datetime.now())
                )
                trades.append(trade_info)
                
            return trades
            
        except Exception as e:
            self.logger.error(f"Error getting open trades: {e}")
            return []
            
    def _should_adjust_levels(self, trade: TradeInfo, market_data: Dict[str, Any]) -> Tuple[bool, AdjustmentReason]:
        """Determine if SL/TP levels should be adjusted"""
        symbol = trade.symbol
        
        # Check if we have adjustment rules for this symbol
        if symbol not in self.adjustment_rules:
            return False, AdjustmentReason.MANUAL_OVERRIDE
            
        # Check minimum time between adjustments
        min_interval = self.config.get("min_adjustment_interval", 300)
        if trade.last_adjustment:
            time_since_last = (datetime.now() - trade.last_adjustment).total_seconds()
            if time_since_last < min_interval:
                return False, AdjustmentReason.MANUAL_OVERRIDE
                
        current_spread = market_data.get('spread_pips', 0)
        
        # Check spread-based adjustments
        if self.config.get("enable_spread_adjustments", True):
            for rule in self.adjustment_rules[symbol]:
                if rule.adjustment_type == AdjustmentType.SPREAD_BASED and rule.enabled:
                    if current_spread > rule.trigger_condition:
                        return True, AdjustmentReason.HIGH_SPREAD
                    elif current_spread < (rule.trigger_condition * 0.6):  # Much lower spread
                        return True, AdjustmentReason.LOW_SPREAD
                        
        return False, AdjustmentReason.MANUAL_OVERRIDE
        
    def _calculate_adjusted_levels(self, trade: TradeInfo, market_data: Dict[str, Any], 
                                 reason: AdjustmentReason) -> Tuple[Optional[float], Optional[float]]:
        """Calculate new SL and TP levels"""
        symbol = trade.symbol
        pip_value = self._get_pip_value(symbol)
        current_price = market_data.get('bid' if trade.direction == 'sell' else 'ask', 0)
        
        if symbol not in self.adjustment_rules:
            return trade.current_sl, trade.current_tp
            
        # Get appropriate adjustment rule
        rule = None
        for r in self.adjustment_rules[symbol]:
            if r.adjustment_type == AdjustmentType.SPREAD_BASED:
                rule = r
                break
                
        if not rule:
            return trade.current_sl, trade.current_tp
            
        new_sl = trade.current_sl
        new_tp = trade.current_tp
        
        # Calculate SL adjustment
        if trade.current_sl is not None:
            if reason == AdjustmentReason.HIGH_SPREAD:
                # Move SL further from price to avoid premature hits
                sl_adjustment = rule.sl_adjustment_pips * pip_value
                if trade.direction == 'buy':
                    new_sl = trade.current_sl - sl_adjustment
                    # Ensure minimum distance from current price
                    min_sl = current_price - (rule.min_distance_pips * pip_value)
                    new_sl = min(new_sl, min_sl)
                else:  # sell
                    new_sl = trade.current_sl + sl_adjustment
                    # Ensure minimum distance from current price  
                    max_sl = current_price + (rule.min_distance_pips * pip_value)
                    new_sl = max(new_sl, max_sl)
                    
            elif reason == AdjustmentReason.LOW_SPREAD:
                # Move SL closer to price for better protection
                sl_adjustment = rule.sl_adjustment_pips * 0.5 * pip_value
                if trade.direction == 'buy':
                    new_sl = trade.current_sl + sl_adjustment
                    # Ensure minimum distance from current price
                    min_sl = current_price - (rule.min_distance_pips * pip_value)
                    new_sl = max(new_sl, min_sl)
                else:  # sell
                    new_sl = trade.current_sl - sl_adjustment
                    # Ensure minimum distance from current price
                    max_sl = current_price + (rule.min_distance_pips * pip_value)
                    new_sl = min(new_sl, max_sl)
                    
        # Calculate TP adjustment
        if trade.current_tp is not None:
            if reason == AdjustmentReason.HIGH_SPREAD:
                # Move TP closer to make it easier to hit
                tp_adjustment = rule.tp_adjustment_pips * pip_value
                if trade.direction == 'buy':
                    new_tp = max(trade.current_tp - tp_adjustment, current_price + (rule.min_distance_pips * pip_value))
                else:  # sell
                    new_tp = min(trade.current_tp + tp_adjustment, current_price - (rule.min_distance_pips * pip_value))
                    
            elif reason == AdjustmentReason.LOW_SPREAD:
                # Keep TP at good levels since spread is low
                tp_adjustment = rule.tp_adjustment_pips * 0.3 * pip_value
                if trade.direction == 'buy':
                    new_tp = min(trade.current_tp + tp_adjustment, trade.current_tp + (rule.max_adjustment_pips * pip_value))
                else:  # sell
                    new_tp = max(trade.current_tp - tp_adjustment, trade.current_tp - (rule.max_adjustment_pips * pip_value))
                    
        return new_sl, new_tp
        
    async def _apply_adjustments(self, trade: TradeInfo, new_sl: Optional[float], new_tp: Optional[float],
                               reason: AdjustmentReason) -> bool:
        """Apply SL/TP adjustments to the trade"""
        try:
            success = True
            error_message = None
            
            # Apply SL adjustment if needed
            if new_sl is not None and new_sl != trade.current_sl:
                if self.sl_manager:
                    sl_success = await self.sl_manager.modify_stop_loss(trade.ticket, new_sl)
                    if not sl_success:
                        success = False
                        error_message = "Failed to modify stop loss"
                elif self.mt5_bridge:
                    sl_result = await self.mt5_bridge.modify_position(trade.ticket, sl=new_sl)
                    if not sl_result.get('success', False):
                        success = False
                        error_message = sl_result.get('error', 'Unknown SL modification error')
                        
            # Apply TP adjustment if needed
            if new_tp is not None and new_tp != trade.current_tp:
                if self.tp_manager:
                    tp_success = await self.tp_manager.modify_take_profit(trade.ticket, new_tp)
                    if not tp_success:
                        success = False
                        error_message = "Failed to modify take profit" if not error_message else error_message + "; Failed to modify take profit"
                elif self.mt5_bridge:
                    tp_result = await self.mt5_bridge.modify_position(trade.ticket, tp=new_tp)
                    if not tp_result.get('success', False):
                        success = False
                        tp_error = tp_result.get('error', 'Unknown TP modification error')
                        error_message = tp_error if not error_message else error_message + f"; {tp_error}"
                        
            # Log adjustment event
            pip_value = self._get_pip_value(trade.symbol)
            sl_adjustment_pips = abs(new_sl - trade.current_sl) / pip_value if (new_sl and trade.current_sl) else 0
            tp_adjustment_pips = abs(new_tp - trade.current_tp) / pip_value if (new_tp and trade.current_tp) else 0
            
            adjustment_event = AdjustmentEvent(
                ticket=trade.ticket,
                symbol=trade.symbol,
                adjustment_type=AdjustmentType.SPREAD_BASED,
                reason=reason,
                old_sl=trade.current_sl,
                new_sl=new_sl,
                old_tp=trade.current_tp,
                new_tp=new_tp,
                adjustment_pips_sl=sl_adjustment_pips,
                adjustment_pips_tp=tp_adjustment_pips,
                timestamp=datetime.now(),
                success=success,
                error_message=error_message
            )
            
            self.adjustment_history.append(adjustment_event)
            
            if success:
                self.logger.info(f"Adjusted levels for ticket {trade.ticket}: SL {trade.current_sl} -> {new_sl}, TP {trade.current_tp} -> {new_tp} ({reason.value})")
            else:
                self.logger.error(f"Failed to adjust levels for ticket {trade.ticket}: {error_message}")
                
            return success
            
        except Exception as e:
            self.logger.error(f"Error applying adjustments to ticket {trade.ticket}: {e}")
            return False
            
    async def _monitor_adjustments(self):
        """Background task to monitor and adjust TP/SL levels"""
        while self.is_monitoring:
            try:
                # Get open trades
                open_trades = self._get_open_trades()
                
                if not open_trades:
                    await asyncio.sleep(self.config.get("monitoring_interval", 30.0))
                    continue
                    
                # Check each trade for adjustment needs
                for trade in open_trades:
                    try:
                        # Get market data
                        market_data = self._get_market_data(trade.symbol)
                        if not market_data:
                            continue
                            
                        # Check if adjustment is needed
                        should_adjust, reason = self._should_adjust_levels(trade, market_data)
                        
                        if should_adjust:
                            # Calculate new levels
                            new_sl, new_tp = self._calculate_adjusted_levels(trade, market_data, reason)
                            
                            # Apply adjustments if levels changed
                            if new_sl != trade.current_sl or new_tp != trade.current_tp:
                                await self._apply_adjustments(trade, new_sl, new_tp, reason)
                                trade.last_adjustment = datetime.now()
                                
                    except Exception as e:
                        self.logger.error(f"Error processing trade {trade.ticket}: {e}")
                        
                await asyncio.sleep(self.config.get("monitoring_interval", 30.0))
                
            except Exception as e:
                self.logger.error(f"Error in adjustment monitoring loop: {e}")
                await asyncio.sleep(5)  # Prevent tight error loop
                
    def start_monitoring(self):
        """Start background monitoring of adjustments"""
        if not self.config.get('enabled', True):
            self.logger.info("TP/SL adjustor is disabled")
            return
            
        if not self.is_monitoring:
            self.is_monitoring = True
            try:
                self.monitoring_task = asyncio.create_task(self._monitor_adjustments())
                self.logger.info("TP/SL adjustment monitoring started")
            except RuntimeError:
                # No event loop running
                self.is_monitoring = False
                self.logger.warning("No event loop running, cannot start monitoring")
                
    def stop_monitoring(self):
        """Stop background monitoring"""
        if self.is_monitoring:
            self.is_monitoring = False
            if self.monitoring_task:
                self.monitoring_task.cancel()
            self.logger.info("TP/SL adjustment monitoring stopped")
            
    async def manual_adjust_trade(self, ticket: int, new_sl: Optional[float] = None, 
                                new_tp: Optional[float] = None, reason: str = "Manual adjustment") -> bool:
        """Manually adjust SL/TP for a specific trade"""
        try:
            # Get trade info
            open_trades = self._get_open_trades()
            trade = None
            for t in open_trades:
                if t.ticket == ticket:
                    trade = t
                    break
                    
            if not trade:
                self.logger.error(f"Trade {ticket} not found")
                return False
                
            # Apply adjustments
            success = await self._apply_adjustments(trade, new_sl, new_tp, AdjustmentReason.MANUAL_OVERRIDE)
            
            if success:
                self.logger.info(f"Manual adjustment applied to ticket {ticket}: SL={new_sl}, TP={new_tp}")
                
            return success
            
        except Exception as e:
            self.logger.error(f"Error manually adjusting trade {ticket}: {e}")
            return False
            
    def add_adjustment_rule(self, symbol: str, rule: AdjustmentRule) -> bool:
        """Add a new adjustment rule for a symbol"""
        try:
            if symbol not in self.adjustment_rules:
                self.adjustment_rules[symbol] = []
                
            self.adjustment_rules[symbol].append(rule)
            self.logger.info(f"Added adjustment rule for {symbol}: {rule.adjustment_type.value}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error adding adjustment rule for {symbol}: {e}")
            return False
            
    def remove_adjustment_rule(self, symbol: str, adjustment_type: AdjustmentType) -> bool:
        """Remove an adjustment rule for a symbol"""
        try:
            if symbol not in self.adjustment_rules:
                return False
                
            self.adjustment_rules[symbol] = [
                rule for rule in self.adjustment_rules[symbol] 
                if rule.adjustment_type != adjustment_type
            ]
            
            self.logger.info(f"Removed {adjustment_type.value} rule for {symbol}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error removing adjustment rule for {symbol}: {e}")
            return False
            
    def get_adjustment_statistics(self) -> Dict[str, Any]:
        """Get adjustment statistics"""
        total_adjustments = len(self.adjustment_history)
        if total_adjustments == 0:
            return {
                "total_adjustments": 0,
                "successful_adjustments": 0,
                "success_rate": 0.0,
                "adjustments_by_reason": {},
                "adjustments_by_symbol": {},
                "monitoring_active": self.is_monitoring
            }
            
        successful = len([e for e in self.adjustment_history if e.success])
        
        # Group by reason
        by_reason = {}
        for event in self.adjustment_history:
            reason = event.reason.value
            if reason not in by_reason:
                by_reason[reason] = 0
            by_reason[reason] += 1
            
        # Group by symbol
        by_symbol = {}
        for event in self.adjustment_history:
            symbol = event.symbol
            if symbol not in by_symbol:
                by_symbol[symbol] = 0
            by_symbol[symbol] += 1
            
        return {
            "total_adjustments": total_adjustments,
            "successful_adjustments": successful,
            "success_rate": (successful / total_adjustments * 100) if total_adjustments > 0 else 0.0,
            "adjustments_by_reason": by_reason,
            "adjustments_by_symbol": by_symbol,
            "monitoring_active": self.is_monitoring
        }
        
    def get_recent_adjustments(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent adjustment events"""
        recent = sorted(self.adjustment_history, key=lambda x: x.timestamp, reverse=True)[:limit]
        return [event.to_dict() for event in recent]
        
    def get_symbol_rules(self, symbol: str) -> List[AdjustmentRule]:
        """Get adjustment rules for a specific symbol"""
        return self.adjustment_rules.get(symbol, [])

# Global instance for easy access
tp_sl_adjustor = TPSLAdjustor()