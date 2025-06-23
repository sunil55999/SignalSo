"""
SL Manager Engine for SignalOS
Implements advanced stop loss management with dynamic adjustments, multiple strategies, and automated SL modifications
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from enum import Enum
import json
import math


class SLStrategy(Enum):
    FIXED = "fixed"
    TRAILING = "trailing"
    ATR_BASED = "atr_based"
    PERCENTAGE_BASED = "percentage_based"
    VOLATILITY_BASED = "volatility_based"
    TIME_BASED = "time_based"
    RR_BASED = "rr_based"


class SLTrigger(Enum):
    IMMEDIATE = "immediate"
    ON_PROFIT = "on_profit"
    ON_TP_HIT = "on_tp_hit"
    ON_BREAKEVEN = "on_breakeven"
    TIME_DELAYED = "time_delayed"
    MANUAL = "manual"


class SLAction(Enum):
    MOVE_TO_BREAKEVEN = "move_to_breakeven"
    MOVE_TO_TP_LEVEL = "move_to_tp_level"
    TRAIL_BY_PIPS = "trail_by_pips"
    TRAIL_BY_PERCENTAGE = "trail_by_percentage"
    ADJUST_BY_ATR = "adjust_by_atr"
    CUSTOM_PRICE = "custom_price"


class TradeDirection(Enum):
    BUY = "buy"
    SELL = "sell"


@dataclass
class SLRule:
    strategy: SLStrategy
    trigger: SLTrigger
    action: SLAction
    value: float  # Pips, percentage, ATR multiplier, or specific price
    condition: Optional[str] = None  # Additional condition (e.g., "profit > 20 pips")
    priority: int = 1  # Higher priority rules execute first
    enabled: bool = True
    max_adjustments: int = 99  # Maximum number of SL adjustments
    min_distance_pips: float = 5.0  # Minimum distance from current price


@dataclass
class SLConfiguration:
    rules: List[SLRule] = field(default_factory=list)
    auto_adjust: bool = True
    max_sl_moves_per_day: int = 10
    preserve_original_sl: bool = True
    emergency_sl_distance: float = 100.0  # Emergency SL distance in pips
    trailing_step_pips: float = 5.0  # Minimum step for trailing SL
    atr_period: int = 14  # ATR calculation period
    volatility_factor: float = 2.0  # Volatility multiplier
    time_decay_hours: int = 24  # Time-based SL decay


@dataclass
class SLManagedPosition:
    ticket: int
    symbol: str
    direction: TradeDirection
    entry_price: float
    entry_time: datetime
    lot_size: float
    original_sl: Optional[float]
    current_sl: Optional[float]
    config: SLConfiguration = field(default_factory=SLConfiguration)
    last_sl_update: datetime = field(default_factory=datetime.now)
    sl_adjustments_count: int = 0
    sl_moves_today: int = 0
    best_price_achieved: Optional[float] = None
    last_atr_value: Optional[float] = None
    created_at: datetime = field(default_factory=datetime.now)
    tp_levels_hit: List[int] = field(default_factory=list)
    breakeven_triggered: bool = False


@dataclass
class SLAdjustment:
    ticket: int
    old_sl: Optional[float]
    new_sl: float
    adjustment_reason: str
    strategy_used: SLStrategy
    action_taken: SLAction
    market_price: float
    profit_pips: float
    timestamp: datetime
    rule_applied: Optional[SLRule] = None


class SLManager:
    def __init__(self, config_file: str = "config.json", log_file: str = "logs/sl_manager_log.json"):
        self.config_file = config_file
        self.log_file = log_file
        self.config = self._load_config()
        self._setup_logging()
        
        # Module references
        self.mt5_bridge: Optional[Any] = None
        self.market_data: Optional[Any] = None
        self.trailing_stop_engine: Optional[Any] = None
        self.break_even_engine: Optional[Any] = None
        self.tp_manager: Optional[Any] = None
        
        # Active SL managed positions
        self.sl_positions: Dict[int, SLManagedPosition] = {}
        self.adjustment_history: List[SLAdjustment] = []
        
        # Monitoring settings
        self.update_interval = self.config.get('update_interval_seconds', 5)
        self.is_running = False
        self._load_sl_history()

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from JSON file"""
        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)
                return config.get('sl_manager', {
                    'update_interval_seconds': 5,
                    'default_trailing_distance': 20.0,
                    'max_sl_moves_per_day': 10,
                    'min_sl_distance_pips': 5.0,
                    'atr_period': 14,
                    'volatility_multiplier': 2.0,
                    'pip_values': {
                        'EURUSD': 0.0001,
                        'GBPUSD': 0.0001,
                        'USDJPY': 0.01,
                        'USDCHF': 0.0001,
                        'default': 0.0001
                    },
                    'default_sl_rules': [
                        {
                            'strategy': 'trailing',
                            'trigger': 'on_profit',
                            'action': 'trail_by_pips',
                            'value': 20.0,
                            'condition': 'profit > 15 pips',
                            'priority': 1
                        },
                        {
                            'strategy': 'fixed',
                            'trigger': 'on_tp_hit',
                            'action': 'move_to_breakeven',
                            'value': 0.0,
                            'condition': 'tp_level >= 1',
                            'priority': 2
                        }
                    ],
                    'max_positions_to_monitor': 100
                })
        except FileNotFoundError:
            return self._create_default_config()

    def _create_default_config(self) -> Dict[str, Any]:
        """Create default configuration"""
        default_config = {
            'sl_manager': {
                'update_interval_seconds': 5,
                'default_trailing_distance': 20.0,
                'max_sl_moves_per_day': 10,
                'min_sl_distance_pips': 5.0,
                'atr_period': 14,
                'volatility_multiplier': 2.0,
                'pip_values': {
                    'EURUSD': 0.0001,
                    'GBPUSD': 0.0001,
                    'USDJPY': 0.01,
                    'USDCHF': 0.0001,
                    'default': 0.0001
                },
                'default_sl_rules': [
                    {
                        'strategy': 'trailing',
                        'trigger': 'on_profit',
                        'action': 'trail_by_pips',
                        'value': 20.0,
                        'condition': 'profit > 15 pips',
                        'priority': 1
                    },
                    {
                        'strategy': 'fixed',
                        'trigger': 'on_tp_hit',
                        'action': 'move_to_breakeven',
                        'value': 0.0,
                        'condition': 'tp_level >= 1',
                        'priority': 2
                    }
                ],
                'max_positions_to_monitor': 100
            }
        }
        
        try:
            with open(self.config_file, 'w') as f:
                json.dump(default_config, f, indent=2)
        except Exception as e:
            logging.warning(f"Could not create config file: {e}")
            
        return default_config['sl_manager']

    def _setup_logging(self):
        """Setup logging for SL management operations"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger('SLManager')

    def _load_sl_history(self):
        """Load existing SL adjustment history from log file"""
        try:
            with open(self.log_file, 'r') as f:
                data = json.load(f)
                self.adjustment_history = []
                for entry in data:
                    adjustment = SLAdjustment(
                        ticket=entry['ticket'],
                        old_sl=entry.get('old_sl'),
                        new_sl=entry['new_sl'],
                        adjustment_reason=entry['adjustment_reason'],
                        strategy_used=SLStrategy(entry['strategy_used']),
                        action_taken=SLAction(entry['action_taken']),
                        market_price=entry['market_price'],
                        profit_pips=entry['profit_pips'],
                        timestamp=datetime.fromisoformat(entry['timestamp'])
                    )
                    self.adjustment_history.append(adjustment)
        except FileNotFoundError:
            self.adjustment_history = []
            self._save_sl_history()

    def _save_sl_history(self):
        """Save SL adjustment history to log file"""
        try:
            data = []
            for adjustment in self.adjustment_history:
                data.append({
                    'ticket': adjustment.ticket,
                    'old_sl': adjustment.old_sl,
                    'new_sl': adjustment.new_sl,
                    'adjustment_reason': adjustment.adjustment_reason,
                    'strategy_used': adjustment.strategy_used.value,
                    'action_taken': adjustment.action_taken.value,
                    'market_price': adjustment.market_price,
                    'profit_pips': adjustment.profit_pips,
                    'timestamp': adjustment.timestamp.isoformat()
                })
            
            with open(self.log_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to save SL history: {e}")

    def inject_modules(self, mt5_bridge=None, market_data=None, trailing_stop_engine=None, 
                      break_even_engine=None, tp_manager=None):
        """Inject module references for trading operations"""
        self.mt5_bridge = mt5_bridge
        self.market_data = market_data
        self.trailing_stop_engine = trailing_stop_engine
        self.break_even_engine = break_even_engine
        self.tp_manager = tp_manager

    def get_pip_value(self, symbol: str) -> float:
        """Get pip value for symbol"""
        return self.config['pip_values'].get(symbol, self.config['pip_values']['default'])

    def calculate_pips(self, symbol: str, price_diff: float, direction: TradeDirection) -> float:
        """Calculate pips from price difference considering direction"""
        pip_value = self.get_pip_value(symbol)
        pips = abs(price_diff) / pip_value
        
        # Apply direction sign
        if direction == TradeDirection.BUY:
            return pips if price_diff > 0 else -pips
        else:  # SELL
            return pips if price_diff < 0 else -pips

    def pips_to_price(self, symbol: str, pips: float) -> float:
        """Convert pips to price difference"""
        pip_value = self.get_pip_value(symbol)
        return pips * pip_value

    def parse_sl_commands_from_signal(self, signal_text: str, symbol: str, direction: TradeDirection,
                                     entry_price: float) -> List[SLRule]:
        """
        Parse SL management commands from signal text
        Examples:
        - "SL to breakeven after TP1"
        - "Trail SL by 20 pips when 15 pips profit"
        - "Move SL to TP1 after TP2 hit"
        - "ATR SL with 2x multiplier"
        """
        sl_rules = []
        
        if not signal_text:
            return sl_rules
        
        import re
        signal_text = signal_text.upper()
        
        # Pattern 1: "SL to breakeven after TP1"
        breakeven_pattern = r'SL\s+TO\s+BREAKEVEN\s+AFTER\s+TP(\d+)'
        breakeven_match = re.search(breakeven_pattern, signal_text)
        if breakeven_match:
            tp_level = int(breakeven_match.group(1))
            rule = SLRule(
                strategy=SLStrategy.FIXED,
                trigger=SLTrigger.ON_TP_HIT,
                action=SLAction.MOVE_TO_BREAKEVEN,
                value=0.0,
                condition=f'tp_level >= {tp_level}',
                priority=1
            )
            sl_rules.append(rule)
        
        # Pattern 2: "Trail SL by X pips when Y pips profit"
        trail_pattern = r'TRAIL\s+SL\s+BY\s+(\d+)\s+PIPS\s+WHEN\s+(\d+)\s+PIPS\s+PROFIT'
        trail_match = re.search(trail_pattern, signal_text)
        if trail_match:
            trail_pips = float(trail_match.group(1))
            profit_threshold = float(trail_match.group(2))
            rule = SLRule(
                strategy=SLStrategy.TRAILING,
                trigger=SLTrigger.ON_PROFIT,
                action=SLAction.TRAIL_BY_PIPS,
                value=trail_pips,
                condition=f'profit > {profit_threshold} pips',
                priority=2
            )
            sl_rules.append(rule)
        
        # Pattern 3: "Move SL to TP1 after TP2 hit"
        move_to_tp_pattern = r'MOVE\s+SL\s+TO\s+TP(\d+)\s+AFTER\s+TP(\d+)\s+HIT'
        move_to_tp_match = re.search(move_to_tp_pattern, signal_text)
        if move_to_tp_match:
            target_tp = int(move_to_tp_match.group(1))
            trigger_tp = int(move_to_tp_match.group(2))
            rule = SLRule(
                strategy=SLStrategy.FIXED,
                trigger=SLTrigger.ON_TP_HIT,
                action=SLAction.MOVE_TO_TP_LEVEL,
                value=float(target_tp),
                condition=f'tp_level >= {trigger_tp}',
                priority=3
            )
            sl_rules.append(rule)
        
        # Pattern 4: "ATR SL with Xx multiplier"
        atr_pattern = r'ATR\s+SL\s+WITH\s+(\d+(?:\.\d+)?)[Xx]\s+MULTIPLIER'
        atr_match = re.search(atr_pattern, signal_text)
        if atr_match:
            multiplier = float(atr_match.group(1))
            rule = SLRule(
                strategy=SLStrategy.ATR_BASED,
                trigger=SLTrigger.ON_PROFIT,
                action=SLAction.ADJUST_BY_ATR,
                value=multiplier,
                condition='profit > 10 pips',
                priority=4
            )
            sl_rules.append(rule)
        
        # Pattern 5: "SL X% below high" (percentage trailing)
        percentage_pattern = r'SL\s+(\d+)%\s+BELOW\s+HIGH'
        percentage_match = re.search(percentage_pattern, signal_text)
        if percentage_match:
            percentage = float(percentage_match.group(1))
            rule = SLRule(
                strategy=SLStrategy.PERCENTAGE_BASED,
                trigger=SLTrigger.ON_PROFIT,
                action=SLAction.TRAIL_BY_PERCENTAGE,
                value=percentage,
                condition='profit > 5 pips',
                priority=5
            )
            sl_rules.append(rule)
        
        return sl_rules

    def create_default_sl_rules(self) -> List[SLRule]:
        """Create default SL rules from configuration"""
        default_rules = []
        
        for rule_config in self.config.get('default_sl_rules', []):
            rule = SLRule(
                strategy=SLStrategy(rule_config['strategy']),
                trigger=SLTrigger(rule_config['trigger']),
                action=SLAction(rule_config['action']),
                value=rule_config['value'],
                condition=rule_config.get('condition'),
                priority=rule_config.get('priority', 1)
            )
            default_rules.append(rule)
        
        return default_rules

    def add_sl_managed_position(self, ticket: int, symbol: str, direction: TradeDirection,
                               entry_price: float, lot_size: float, current_sl: Optional[float] = None,
                               config: Optional[SLConfiguration] = None,
                               custom_rules: Optional[List[SLRule]] = None) -> bool:
        """Add position to SL management"""
        try:
            if config is None:
                config = SLConfiguration()
            
            # Add custom rules or default rules
            if custom_rules:
                config.rules.extend(custom_rules)
            else:
                config.rules.extend(self.create_default_sl_rules())
            
            position = SLManagedPosition(
                ticket=ticket,
                symbol=symbol,
                direction=direction,
                entry_price=entry_price,
                entry_time=datetime.now(),
                lot_size=lot_size,
                original_sl=current_sl,
                current_sl=current_sl,
                config=config,
                best_price_achieved=entry_price
            )
            
            self.sl_positions[ticket] = position
            
            self.logger.info(f"Added SL managed position {ticket} ({symbol}) with {len(config.rules)} rules")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to add SL managed position {ticket}: {e}")
            return False

    def remove_sl_managed_position(self, ticket: int) -> bool:
        """Remove position from SL management"""
        if ticket in self.sl_positions:
            del self.sl_positions[ticket]
            self.logger.info(f"Removed SL managed position {ticket}")
            return True
        return False

    async def get_current_price(self, symbol: str) -> Optional[float]:
        """Get current market price for symbol"""
        try:
            if self.market_data and hasattr(self.market_data, 'get_current_price'):
                return await self.market_data.get_current_price(symbol)
            elif self.mt5_bridge and hasattr(self.mt5_bridge, 'get_current_price'):
                return await self.mt5_bridge.get_current_price(symbol)
            else:
                self.logger.warning(f"No market data source available for {symbol}")
                return None
        except Exception as e:
            self.logger.error(f"Failed to get current price for {symbol}: {e}")
            return None

    async def get_atr_value(self, symbol: str, period: int = 14) -> Optional[float]:
        """Get ATR (Average True Range) value for symbol"""
        try:
            if self.market_data and hasattr(self.market_data, 'get_atr'):
                return await self.market_data.get_atr(symbol, period)
            else:
                # Fallback: estimate ATR based on recent price movements
                return self.pips_to_price(symbol, 20.0)  # Default 20 pips
        except Exception as e:
            self.logger.error(f"Failed to get ATR for {symbol}: {e}")
            return self.pips_to_price(symbol, 20.0)

    def evaluate_sl_rule_condition(self, position: SLManagedPosition, rule: SLRule, 
                                  current_price: float) -> bool:
        """Evaluate if SL rule condition is met"""
        if not rule.condition:
            return True
        
        try:
            # Calculate current profit in pips
            profit_pips = self.calculate_pips(
                position.symbol, 
                current_price - position.entry_price, 
                position.direction
            )
            
            # Create evaluation context
            context = {
                'profit': profit_pips,
                'tp_level': max(position.tp_levels_hit) if position.tp_levels_hit else 0,
                'breakeven_triggered': position.breakeven_triggered,
                'sl_adjustments': position.sl_adjustments_count,
                'current_price': current_price,
                'entry_price': position.entry_price
            }
            
            # Simple condition evaluation
            condition = rule.condition.lower()
            
            if 'profit >' in condition:
                threshold = float(condition.split('profit >')[1].split('pips')[0].strip())
                return profit_pips > threshold
            elif 'tp_level >=' in condition:
                threshold = int(condition.split('tp_level >=')[1].strip())
                return context['tp_level'] >= threshold
            elif 'breakeven_triggered' in condition:
                return position.breakeven_triggered
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to evaluate SL rule condition: {e}")
            return False

    async def calculate_new_sl(self, position: SLManagedPosition, rule: SLRule, 
                              current_price: float) -> Optional[float]:
        """Calculate new SL based on rule and current market conditions"""
        try:
            if rule.action == SLAction.MOVE_TO_BREAKEVEN:
                return position.entry_price
            
            elif rule.action == SLAction.MOVE_TO_TP_LEVEL:
                # Get TP level price from TP manager
                if self.tp_manager:
                    tp_level = int(rule.value)
                    tp_status = self.tp_manager.get_position_status(position.ticket)
                    if tp_status and tp_status.get('tp_levels'):
                        for tp in tp_status['tp_levels']:
                            if tp['level'] == tp_level:
                                return tp['price']
                return None
            
            elif rule.action == SLAction.TRAIL_BY_PIPS:
                trail_distance = self.pips_to_price(position.symbol, rule.value)
                if position.direction == TradeDirection.BUY:
                    new_sl = current_price - trail_distance
                    # Only move SL up for BUY positions
                    if position.current_sl is None or new_sl > position.current_sl:
                        return new_sl
                else:  # SELL
                    new_sl = current_price + trail_distance
                    # Only move SL down for SELL positions
                    if position.current_sl is None or new_sl < position.current_sl:
                        return new_sl
                return None
            
            elif rule.action == SLAction.TRAIL_BY_PERCENTAGE:
                if position.best_price_achieved is None:
                    return None
                
                percentage = rule.value / 100.0
                if position.direction == TradeDirection.BUY:
                    new_sl = position.best_price_achieved * (1 - percentage)
                    if position.current_sl is None or new_sl > position.current_sl:
                        return new_sl
                else:  # SELL
                    new_sl = position.best_price_achieved * (1 + percentage)
                    if position.current_sl is None or new_sl < position.current_sl:
                        return new_sl
                return None
            
            elif rule.action == SLAction.ADJUST_BY_ATR:
                atr_value = await self.get_atr_value(position.symbol)
                if atr_value is None:
                    return None
                
                atr_distance = atr_value * rule.value
                if position.direction == TradeDirection.BUY:
                    new_sl = current_price - atr_distance
                    if position.current_sl is None or new_sl > position.current_sl:
                        return new_sl
                else:  # SELL
                    new_sl = current_price + atr_distance
                    if position.current_sl is None or new_sl < position.current_sl:
                        return new_sl
                return None
            
            elif rule.action == SLAction.CUSTOM_PRICE:
                return rule.value
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to calculate new SL: {e}")
            return None

    def validate_new_sl(self, position: SLManagedPosition, new_sl: float, current_price: float) -> bool:
        """Validate that new SL is appropriate"""
        try:
            # Check minimum distance from current price
            min_distance = self.pips_to_price(position.symbol, position.config.min_distance_pips)
            
            if position.direction == TradeDirection.BUY:
                if new_sl >= current_price - min_distance:
                    return False
            else:  # SELL
                if new_sl <= current_price + min_distance:
                    return False
            
            # Check daily SL move limit
            if position.sl_moves_today >= position.config.max_sl_moves_per_day:
                return False
            
            # Check maximum adjustments
            if position.sl_adjustments_count >= max(rule.max_adjustments for rule in position.config.rules):
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to validate new SL: {e}")
            return False

    async def execute_sl_adjustment(self, position: SLManagedPosition, new_sl: float, 
                                   rule: SLRule, current_price: float, reason: str) -> bool:
        """Execute SL adjustment via MT5 bridge"""
        try:
            if not self.validate_new_sl(position, new_sl, current_price):
                return False
            
            # Execute SL modification
            success = False
            if self.mt5_bridge and hasattr(self.mt5_bridge, 'modify_position'):
                result = await self.mt5_bridge.modify_position(
                    ticket=position.ticket,
                    new_sl=new_sl
                )
                success = result.get('success', False)
            
            if success:
                # Update position
                old_sl = position.current_sl
                position.current_sl = new_sl
                position.last_sl_update = datetime.now()
                position.sl_adjustments_count += 1
                position.sl_moves_today += 1
                
                # Calculate profit
                profit_pips = self.calculate_pips(
                    position.symbol, 
                    current_price - position.entry_price, 
                    position.direction
                )
                
                # Record adjustment
                adjustment = SLAdjustment(
                    ticket=position.ticket,
                    old_sl=old_sl,
                    new_sl=new_sl,
                    adjustment_reason=reason,
                    strategy_used=rule.strategy,
                    action_taken=rule.action,
                    market_price=current_price,
                    profit_pips=profit_pips,
                    timestamp=datetime.now(),
                    rule_applied=rule
                )
                self.adjustment_history.append(adjustment)
                
                self.logger.info(f"SL adjusted for position {position.ticket}: {old_sl} -> {new_sl} ({reason})")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to execute SL adjustment for {position.ticket}: {e}")
            return False

    async def process_sl_rules(self, position: SLManagedPosition, current_price: float):
        """Process all SL rules for a position"""
        # Update best price achieved
        if position.best_price_achieved is None:
            position.best_price_achieved = current_price
        else:
            if position.direction == TradeDirection.BUY:
                position.best_price_achieved = max(position.best_price_achieved, current_price)
            else:  # SELL
                position.best_price_achieved = min(position.best_price_achieved, current_price)
        
        # Sort rules by priority (higher priority first)
        sorted_rules = sorted(position.config.rules, key=lambda r: r.priority, reverse=True)
        
        for rule in sorted_rules:
            if not rule.enabled:
                continue
            
            try:
                # Check if rule condition is met
                if not self.evaluate_sl_rule_condition(position, rule, current_price):
                    continue
                
                # Calculate new SL based on rule
                new_sl = await self.calculate_new_sl(position, rule, current_price)
                if new_sl is None:
                    continue
                
                # Check if SL actually needs to be moved
                if position.current_sl is not None and abs(new_sl - position.current_sl) < self.pips_to_price(position.symbol, 0.5):
                    continue
                
                # Execute SL adjustment
                reason = f"{rule.strategy.value} strategy - {rule.action.value}"
                success = await self.execute_sl_adjustment(position, new_sl, rule, current_price, reason)
                
                if success:
                    # Only execute one rule per cycle to avoid conflicts
                    break
                    
            except Exception as e:
                self.logger.error(f"Error processing SL rule for position {position.ticket}: {e}")

    async def handle_tp_hit_notification(self, ticket: int, tp_level: int):
        """Handle notification when TP level is hit"""
        if ticket in self.sl_positions:
            position = self.sl_positions[ticket]
            if tp_level not in position.tp_levels_hit:
                position.tp_levels_hit.append(tp_level)
                self.logger.info(f"TP{tp_level} hit notification received for position {ticket}")

    async def handle_breakeven_notification(self, ticket: int):
        """Handle notification when breakeven is triggered"""
        if ticket in self.sl_positions:
            position = self.sl_positions[ticket]
            position.breakeven_triggered = True
            self.logger.info(f"Breakeven notification received for position {ticket}")

    async def monitor_sl_positions(self):
        """Monitor all SL managed positions for adjustments"""
        for ticket, position in list(self.sl_positions.items()):
            try:
                current_price = await self.get_current_price(position.symbol)
                if current_price is None:
                    continue
                
                # Process SL rules
                await self.process_sl_rules(position, current_price)
                
                # Reset daily counters if new day
                if position.last_sl_update.date() < datetime.now().date():
                    position.sl_moves_today = 0
                
            except Exception as e:
                self.logger.error(f"Error monitoring SL position {ticket}: {e}")

    async def start_sl_monitor(self):
        """Start the SL monitoring loop"""
        if self.is_running:
            self.logger.warning("SL monitor already running")
            return
        
        self.is_running = True
        self.logger.info("Starting SL monitor")
        
        try:
            while self.is_running:
                await self.monitor_sl_positions()
                await asyncio.sleep(self.update_interval)
                
        except Exception as e:
            self.logger.error(f"SL monitor error: {e}")
        finally:
            self.is_running = False
            self.logger.info("SL monitor stopped")

    def stop_sl_monitor(self):
        """Stop the SL monitoring loop"""
        self.is_running = False
        self.logger.info("Stopping SL monitor")

    def get_sl_statistics(self) -> Dict[str, Any]:
        """Get statistics about SL management operations"""
        total_positions = len(self.sl_positions)
        total_adjustments = len(self.adjustment_history)
        
        if total_adjustments > 0:
            successful_adjustments = len([adj for adj in self.adjustment_history])
            strategies_used = {}
            actions_taken = {}
            
            for adjustment in self.adjustment_history:
                strategy = adjustment.strategy_used.value
                action = adjustment.action_taken.value
                
                strategies_used[strategy] = strategies_used.get(strategy, 0) + 1
                actions_taken[action] = actions_taken.get(action, 0) + 1
            
            avg_profit_at_adjustment = sum(adj.profit_pips for adj in self.adjustment_history) / total_adjustments
        else:
            successful_adjustments = 0
            strategies_used = {}
            actions_taken = {}
            avg_profit_at_adjustment = 0.0
        
        return {
            'total_positions': total_positions,
            'active_positions': len([p for p in self.sl_positions.values()]),
            'total_adjustments': total_adjustments,
            'successful_adjustments': successful_adjustments,
            'strategies_used': strategies_used,
            'actions_taken': actions_taken,
            'average_profit_at_adjustment': avg_profit_at_adjustment
        }

    def get_position_status(self, ticket: int) -> Optional[Dict[str, Any]]:
        """Get status of specific SL managed position"""
        if ticket not in self.sl_positions:
            return None
        
        position = self.sl_positions[ticket]
        
        rules_status = []
        for rule in position.config.rules:
            rules_status.append({
                'strategy': rule.strategy.value,
                'trigger': rule.trigger.value,
                'action': rule.action.value,
                'value': rule.value,
                'condition': rule.condition,
                'priority': rule.priority,
                'enabled': rule.enabled
            })
        
        return {
            'ticket': ticket,
            'symbol': position.symbol,
            'direction': position.direction.value,
            'entry_price': position.entry_price,
            'lot_size': position.lot_size,
            'original_sl': position.original_sl,
            'current_sl': position.current_sl,
            'best_price_achieved': position.best_price_achieved,
            'sl_adjustments_count': position.sl_adjustments_count,
            'sl_moves_today': position.sl_moves_today,
            'tp_levels_hit': position.tp_levels_hit,
            'breakeven_triggered': position.breakeven_triggered,
            'rules': rules_status,
            'created_at': position.created_at.isoformat(),
            'last_sl_update': position.last_sl_update.isoformat()
        }

    def get_recent_adjustments(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent SL adjustments"""
        recent_adjustments = self.adjustment_history[-limit:] if self.adjustment_history else []
        
        return [{
            'ticket': adjustment.ticket,
            'old_sl': adjustment.old_sl,
            'new_sl': adjustment.new_sl,
            'adjustment_reason': adjustment.adjustment_reason,
            'strategy_used': adjustment.strategy_used.value,
            'action_taken': adjustment.action_taken.value,
            'market_price': adjustment.market_price,
            'profit_pips': adjustment.profit_pips,
            'timestamp': adjustment.timestamp.isoformat()
        } for adjustment in recent_adjustments]


# Example usage and testing
async def main():
    """Example usage of SL Manager"""
    manager = SLManager()
    
    # Test SL command parsing
    test_signals = [
        "SL to breakeven after TP1",
        "Trail SL by 20 pips when 15 pips profit",
        "Move SL to TP1 after TP2 hit",
        "ATR SL with 2.5x multiplier",
        "SL 5% below high"
    ]
    
    print("Testing SL command parsing:")
    for signal in test_signals:
        sl_rules = manager.parse_sl_commands_from_signal(signal, "EURUSD", TradeDirection.BUY, 1.2000)
        print(f"Signal: '{signal}'")
        for rule in sl_rules:
            print(f"  {rule.strategy.value} - {rule.action.value} (value: {rule.value}, condition: {rule.condition})")
        print()
    
    # Get statistics
    stats = manager.get_sl_statistics()
    print(f"Current statistics: {stats}")


if __name__ == "__main__":
    asyncio.run(main())