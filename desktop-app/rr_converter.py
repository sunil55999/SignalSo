"""
Risk-Reward Ratio Converter Engine for SignalOS
Implements risk-reward ratio converter and calculator for optimal trade management
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
import json
import math


class RRStrategy(Enum):
    FIXED_RATIO = "fixed_ratio"
    ADAPTIVE_RATIO = "adaptive_ratio"
    PROGRESSIVE_RATIO = "progressive_ratio"
    VOLATILITY_ADJUSTED = "volatility_adjusted"
    TIME_BASED = "time_based"


class RRTrigger(Enum):
    ENTRY_SIGNAL = "entry_signal"
    MANUAL_SET = "manual_set"
    MARKET_CONDITIONS = "market_conditions"
    ATR_BASED = "atr_based"
    SUPPORT_RESISTANCE = "support_resistance"


class TradeDirection(Enum):
    BUY = "buy"
    SELL = "sell"


@dataclass
class RRConfiguration:
    default_ratio: float = 1.0  # Default R:R ratio (e.g., 1:2 = 2.0)
    min_ratio: float = 0.5
    max_ratio: float = 10.0
    auto_calculate_sl: bool = True
    auto_calculate_tp: bool = True
    use_atr_multiplier: bool = False
    atr_period: int = 14
    atr_multiplier: float = 1.5
    risk_percentage: float = 2.0  # % of account to risk per trade


@dataclass
class RRLevel:
    ratio: float  # R:R ratio (e.g., 1.0, 2.0, 3.0)
    risk_amount: float  # Risk amount in account currency
    reward_amount: float  # Expected reward amount
    sl_distance_pips: float  # Distance to SL in pips
    tp_distance_pips: float  # Distance to TP in pips
    sl_price: Optional[float] = None
    tp_price: Optional[float] = None
    lot_size: Optional[float] = None
    entry_price: Optional[float] = None


@dataclass
class RRPosition:
    ticket: int
    symbol: str
    direction: TradeDirection
    entry_price: float
    current_price: float
    original_sl: Optional[float]
    original_tp: Optional[float]
    lot_size: float
    rr_config: RRConfiguration
    target_ratios: List[float] = field(default_factory=lambda: [1.0, 2.0, 3.0])
    calculated_levels: List[RRLevel] = field(default_factory=list)
    last_update: datetime = field(default_factory=datetime.now)
    is_active: bool = True


@dataclass
class RRUpdate:
    ticket: int
    old_ratio: float
    new_ratio: float
    old_sl: Optional[float]
    new_sl: Optional[float]
    old_tp: Optional[float]
    new_tp: Optional[float]
    reason: str
    timestamp: datetime = field(default_factory=datetime.now)


class RRConverter:
    def __init__(self, config_file: str = "config.json", log_file: str = "logs/rr_converter_log.json"):
        self.config_file = config_file
        self.log_file = log_file
        self.config = self._load_config()
        self.positions: Dict[int, RRPosition] = {}
        self.rr_history: List[RRUpdate] = []
        self.mt5_bridge = None
        self.market_data = None
        self.sl_manager = None
        self.tp_manager = None
        self.is_running = False
        
        # Setup logging
        self._setup_logging()
        
        # Load existing history
        self._load_rr_history()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from JSON file"""
        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)
                return config.get('rr_converter', self._create_default_config())
        except FileNotFoundError:
            return self._create_default_config()
    
    def _create_default_config(self) -> Dict[str, Any]:
        """Create default configuration"""
        default_config = {
            "rr_converter": {
                "default_ratio": 2.0,
                "min_ratio": 0.5,
                "max_ratio": 10.0,
                "auto_calculate_sl": True,
                "auto_calculate_tp": True,
                "use_atr_multiplier": False,
                "atr_period": 14,
                "atr_multiplier": 1.5,
                "risk_percentage": 2.0,
                "update_interval": 5,
                "enable_progressive_rr": True,
                "progressive_ratios": [1.0, 1.5, 2.0, 3.0],
                "volatility_adjustment": True,
                "min_tp_distance_pips": 10,
                "min_sl_distance_pips": 5
            }
        }
        
        # Save default config
        try:
            with open(self.config_file, 'w') as f:
                json.dump(default_config, f, indent=4)
        except Exception as e:
            logging.error(f"Failed to save default config: {e}")
        
        return default_config['rr_converter']
    
    def _setup_logging(self):
        """Setup logging for R:R converter operations"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('logs/rr_converter.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def _load_rr_history(self):
        """Load existing R:R history from log file"""
        try:
            with open(self.log_file, 'r') as f:
                history_data = json.load(f)
                self.rr_history = [
                    RRUpdate(**update) for update in history_data.get('rr_updates', [])
                ]
        except FileNotFoundError:
            self.rr_history = []
        except Exception as e:
            self.logger.error(f"Failed to load R:R history: {e}")
            self.rr_history = []
    
    def _save_rr_history(self):
        """Save R:R history to log file"""
        try:
            history_data = {
                'rr_updates': [
                    {
                        'ticket': update.ticket,
                        'old_ratio': update.old_ratio,
                        'new_ratio': update.new_ratio,
                        'old_sl': update.old_sl,
                        'new_sl': update.new_sl,
                        'old_tp': update.old_tp,
                        'new_tp': update.new_tp,
                        'reason': update.reason,
                        'timestamp': update.timestamp.isoformat()
                    } for update in self.rr_history[-1000:]  # Keep last 1000 updates
                ]
            }
            
            with open(self.log_file, 'w') as f:
                json.dump(history_data, f, indent=2)
                
        except Exception as e:
            self.logger.error(f"Failed to save R:R history: {e}")
    
    def inject_modules(self, mt5_bridge=None, market_data=None, sl_manager=None, tp_manager=None):
        """Inject module references for R:R operations"""
        self.mt5_bridge = mt5_bridge
        self.market_data = market_data
        self.sl_manager = sl_manager
        self.tp_manager = tp_manager
    
    def get_pip_value(self, symbol: str) -> float:
        """Get pip value for symbol"""
        # Standard pip values for major pairs
        pip_values = {
            'EURUSD': 0.0001, 'GBPUSD': 0.0001, 'AUDUSD': 0.0001, 'NZDUSD': 0.0001,
            'USDCAD': 0.0001, 'USDCHF': 0.0001, 'USDJPY': 0.01, 'EURJPY': 0.01,
            'GBPJPY': 0.01, 'AUDJPY': 0.01, 'CADJPY': 0.01, 'CHFJPY': 0.01
        }
        
        # Check for JPY pairs
        if 'JPY' in symbol:
            return 0.01
        else:
            return pip_values.get(symbol, 0.0001)
    
    def calculate_pips(self, symbol: str, price_diff: float) -> float:
        """Calculate pips from price difference"""
        pip_value = self.get_pip_value(symbol)
        return abs(price_diff) / pip_value
    
    def pips_to_price(self, symbol: str, pips: float) -> float:
        """Convert pips to price difference"""
        pip_value = self.get_pip_value(symbol)
        return pips * pip_value
    
    def calculate_lot_size_for_risk(self, symbol: str, entry_price: float, sl_price: float, 
                                   risk_amount: float) -> float:
        """Calculate lot size based on risk amount and SL distance"""
        try:
            sl_distance_pips = self.calculate_pips(symbol, abs(entry_price - sl_price))
            
            if sl_distance_pips == 0:
                return 0.01  # Minimum lot size
            
            # Standard lot value calculation (simplified)
            pip_value_usd = 10.0  # $10 per pip for 1 standard lot (major pairs)
            if 'JPY' in symbol:
                pip_value_usd = 1000 / entry_price  # Adjust for JPY pairs
            
            lot_size = risk_amount / (sl_distance_pips * pip_value_usd)
            
            # Round to 2 decimal places and ensure minimum
            lot_size = max(0.01, round(lot_size, 2))
            
            return lot_size
            
        except Exception as e:
            self.logger.error(f"Error calculating lot size: {e}")
            return 0.01
    
    def calculate_rr_levels(self, symbol: str, direction: TradeDirection, entry_price: float,
                           target_ratios: List[float], risk_amount: Optional[float] = None,
                           sl_distance_pips: Optional[float] = None) -> List[RRLevel]:
        """Calculate R:R levels for given parameters"""
        try:
            levels = []
            
            # Use default risk amount if not provided
            if risk_amount is None:
                account_balance = 10000  # Default balance for calculation
                risk_amount = account_balance * (self.config.get('risk_percentage', 2.0) / 100)
            
            # Calculate SL distance if not provided
            if sl_distance_pips is None:
                if self.config.get('use_atr_multiplier', False):
                    # Use ATR-based SL distance (simplified)
                    sl_distance_pips = 20 * self.config.get('atr_multiplier', 1.5)
                else:
                    sl_distance_pips = self.config.get('min_sl_distance_pips', 15)
            
            # Ensure we have valid values
            sl_distance_pips_final = float(sl_distance_pips or 15)
            risk_amount_final = float(risk_amount or 200)
            
            # Calculate SL price
            pip_distance = self.pips_to_price(symbol, sl_distance_pips_final)
            if direction == TradeDirection.BUY:
                sl_price = entry_price - pip_distance
            else:
                sl_price = entry_price + pip_distance
            
            # Calculate lot size
            lot_size = self.calculate_lot_size_for_risk(symbol, entry_price, sl_price, risk_amount_final)
            
            # Calculate levels for each target ratio
            for ratio in target_ratios:
                tp_distance_pips = sl_distance_pips_final * ratio
                reward_amount = risk_amount_final * ratio
                
                # Calculate TP price
                tp_pip_distance = self.pips_to_price(symbol, tp_distance_pips)
                if direction == TradeDirection.BUY:
                    tp_price = entry_price + tp_pip_distance
                else:
                    tp_price = entry_price - tp_pip_distance
                
                level = RRLevel(
                    ratio=ratio,
                    risk_amount=risk_amount_final,
                    reward_amount=reward_amount,
                    sl_distance_pips=sl_distance_pips_final,
                    tp_distance_pips=tp_distance_pips,
                    sl_price=sl_price,
                    tp_price=tp_price,
                    lot_size=lot_size,
                    entry_price=entry_price
                )
                
                levels.append(level)
            
            return levels
            
        except Exception as e:
            self.logger.error(f"Error calculating R:R levels: {e}")
            return []
    
    def add_rr_position(self, ticket: int, symbol: str, direction: TradeDirection,
                       entry_price: float, current_price: float, original_sl: Optional[float],
                       original_tp: Optional[float], lot_size: float,
                       target_ratios: Optional[List[float]] = None) -> bool:
        """Add position to R:R monitoring"""
        try:
            if target_ratios is None:
                target_ratios = self.config.get('progressive_ratios', [1.0, 2.0, 3.0])
            
            # Ensure target_ratios is a list
            target_ratios_final = target_ratios or [1.0, 2.0, 3.0]
            
            # Create R:R configuration
            rr_config = RRConfiguration(
                default_ratio=self.config.get('default_ratio', 2.0),
                min_ratio=self.config.get('min_ratio', 0.5),
                max_ratio=self.config.get('max_ratio', 10.0),
                auto_calculate_sl=self.config.get('auto_calculate_sl', True),
                auto_calculate_tp=self.config.get('auto_calculate_tp', True),
                use_atr_multiplier=self.config.get('use_atr_multiplier', False),
                atr_period=self.config.get('atr_period', 14),
                atr_multiplier=self.config.get('atr_multiplier', 1.5),
                risk_percentage=self.config.get('risk_percentage', 2.0)
            )
            
            # Calculate R:R levels
            calculated_levels = self.calculate_rr_levels(
                symbol, direction, entry_price, target_ratios_final
            )
            
            # Create position
            position = RRPosition(
                ticket=ticket,
                symbol=symbol,
                direction=direction,
                entry_price=entry_price,
                current_price=current_price,
                original_sl=original_sl,
                original_tp=original_tp,
                lot_size=lot_size,
                rr_config=rr_config,
                target_ratios=target_ratios_final,
                calculated_levels=calculated_levels
            )
            
            self.positions[ticket] = position
            
            self.logger.info(f"Added R:R position {ticket} for {symbol} with ratios: {target_ratios}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to add R:R position {ticket}: {e}")
            return False
    
    def remove_rr_position(self, ticket: int) -> bool:
        """Remove position from R:R monitoring"""
        try:
            if ticket in self.positions:
                del self.positions[ticket]
                self.logger.info(f"Removed R:R position {ticket}")
                return True
            return False
        except Exception as e:
            self.logger.error(f"Failed to remove R:R position {ticket}: {e}")
            return False
    
    async def get_current_price(self, symbol: str) -> Optional[float]:
        """Get current market price for symbol"""
        try:
            if self.market_data:
                return await self.market_data.get_current_price(symbol)
            elif self.mt5_bridge:
                return await self.mt5_bridge.get_current_price(symbol)
            else:
                # Mock price for testing
                return 1.1000
        except Exception as e:
            self.logger.error(f"Failed to get current price for {symbol}: {e}")
            return None
    
    async def update_sl_tp_from_rr(self, ticket: int, rr_level: RRLevel, reason: str = "R:R update") -> bool:
        """Update SL and TP based on R:R level calculations"""
        try:
            position = self.positions.get(ticket)
            if not position:
                return False
            
            old_sl = position.original_sl
            old_tp = position.original_tp
            new_sl = rr_level.sl_price
            new_tp = rr_level.tp_price
            
            # Update via SL manager if available
            sl_updated = True
            tp_updated = True
            
            if self.sl_manager and new_sl is not None:
                sl_updated = await self.sl_manager.update_stop_loss(ticket, new_sl)
            
            if self.tp_manager and new_tp is not None:
                tp_updated = await self.tp_manager.update_take_profit(ticket, new_tp)
            
            if sl_updated and tp_updated:
                # Log the update
                update = RRUpdate(
                    ticket=ticket,
                    old_ratio=position.rr_config.default_ratio,
                    new_ratio=rr_level.ratio,
                    old_sl=old_sl,
                    new_sl=new_sl,
                    old_tp=old_tp,
                    new_tp=new_tp,
                    reason=reason
                )
                
                self.rr_history.append(update)
                self._save_rr_history()
                
                # Update position
                position.original_sl = new_sl
                position.original_tp = new_tp
                position.last_update = datetime.now()
                
                self.logger.info(f"Updated R:R for {ticket}: SL={new_sl}, TP={new_tp}, Ratio={rr_level.ratio}")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to update SL/TP from R:R for {ticket}: {e}")
            return False
    
    async def optimize_rr_for_position(self, ticket: int) -> bool:
        """Optimize R:R ratio based on market conditions"""
        try:
            position = self.positions.get(ticket)
            if not position:
                return False
            
            current_price = await self.get_current_price(position.symbol)
            if not current_price:
                return False
            
            position.current_price = current_price
            
            # Calculate current P&L in pips
            if position.direction == TradeDirection.BUY:
                current_pips = self.calculate_pips(position.symbol, current_price - position.entry_price)
            else:
                current_pips = self.calculate_pips(position.symbol, position.entry_price - current_price)
            
            # Find optimal R:R level based on current market position
            best_level = None
            for level in position.calculated_levels:
                if current_pips >= level.sl_distance_pips * 0.3:  # At least 30% towards TP
                    best_level = level
                    break
            
            if best_level and self.config.get('volatility_adjustment', True):
                # Apply R:R optimization
                await self.update_sl_tp_from_rr(ticket, best_level, "R:R optimization")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to optimize R:R for position {ticket}: {e}")
            return False
    
    async def process_rr_updates(self):
        """Process all R:R positions and apply updates"""
        try:
            for ticket, position in list(self.positions.items()):
                if not position.is_active:
                    continue
                
                await self.optimize_rr_for_position(ticket)
                
        except Exception as e:
            self.logger.error(f"Error processing R:R updates: {e}")
    
    async def start_rr_monitor(self):
        """Start the R:R monitoring loop"""
        self.is_running = True
        self.logger.info("Starting R:R converter monitor")
        
        while self.is_running:
            try:
                await self.process_rr_updates()
                await asyncio.sleep(self.config.get('update_interval', 5))
                
            except Exception as e:
                self.logger.error(f"Error in R:R monitor loop: {e}")
                await asyncio.sleep(10)
    
    def stop_rr_monitor(self):
        """Stop the R:R monitoring loop"""
        self.is_running = False
        self.logger.info("Stopped R:R converter monitor")
    
    def get_rr_statistics(self) -> Dict[str, Any]:
        """Get statistics about R:R operations"""
        try:
            total_positions = len(self.positions)
            active_positions = len([p for p in self.positions.values() if p.is_active])
            total_updates = len(self.rr_history)
            
            # Calculate average R:R ratio
            if self.rr_history:
                avg_ratio = sum(update.new_ratio for update in self.rr_history) / len(self.rr_history)
            else:
                avg_ratio = 0.0
            
            # Recent performance
            recent_updates = [u for u in self.rr_history if u.timestamp > datetime.now() - timedelta(hours=24)]
            
            return {
                'total_positions': total_positions,
                'active_positions': active_positions,
                'total_updates': total_updates,
                'recent_updates_24h': len(recent_updates),
                'average_rr_ratio': round(avg_ratio, 2),
                'config': self.config,
                'last_update': max([p.last_update for p in self.positions.values()], default=datetime.now()).isoformat() if self.positions else None
            }
            
        except Exception as e:
            self.logger.error(f"Error getting R:R statistics: {e}")
            return {}
    
    def get_position_rr_info(self, ticket: int) -> Optional[Dict[str, Any]]:
        """Get R:R information for specific position"""
        try:
            position = self.positions.get(ticket)
            if not position:
                return None
            
            return {
                'ticket': position.ticket,
                'symbol': position.symbol,
                'direction': position.direction.value,
                'entry_price': position.entry_price,
                'current_price': position.current_price,
                'original_sl': position.original_sl,
                'original_tp': position.original_tp,
                'lot_size': position.lot_size,
                'target_ratios': position.target_ratios,
                'calculated_levels': [
                    {
                        'ratio': level.ratio,
                        'sl_price': level.sl_price,
                        'tp_price': level.tp_price,
                        'risk_amount': level.risk_amount,
                        'reward_amount': level.reward_amount,
                        'sl_distance_pips': level.sl_distance_pips,
                        'tp_distance_pips': level.tp_distance_pips
                    } for level in position.calculated_levels
                ],
                'is_active': position.is_active,
                'last_update': position.last_update.isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error getting R:R info for position {ticket}: {e}")
            return None
    
    def get_recent_rr_updates(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent R:R updates"""
        try:
            recent_updates = sorted(self.rr_history, key=lambda x: x.timestamp, reverse=True)[:limit]
            
            return [
                {
                    'ticket': update.ticket,
                    'old_ratio': update.old_ratio,
                    'new_ratio': update.new_ratio,
                    'old_sl': update.old_sl,
                    'new_sl': update.new_sl,
                    'old_tp': update.old_tp,
                    'new_tp': update.new_tp,
                    'reason': update.reason,
                    'timestamp': update.timestamp.isoformat()
                } for update in recent_updates
            ]
            
        except Exception as e:
            self.logger.error(f"Error getting recent R:R updates: {e}")
            return []


async def main():
    """Example usage of R:R Converter Engine"""
    
    # Create R:R converter
    rr_converter = RRConverter()
    
    # Mock MT5 bridge and market data
    class MockMT5Bridge:
        async def get_current_price(self, symbol):
            return 1.1050 if symbol == "EURUSD" else 1.2500
    
    class MockSLManager:
        async def update_stop_loss(self, ticket, new_sl):
            print(f"Mock: Updated SL for {ticket} to {new_sl}")
            return True
    
    class MockTPManager:
        async def update_take_profit(self, ticket, new_tp):
            print(f"Mock: Updated TP for {ticket} to {new_tp}")
            return True
    
    # Inject mock modules
    rr_converter.inject_modules(
        mt5_bridge=MockMT5Bridge(),
        sl_manager=MockSLManager(),
        tp_manager=MockTPManager()
    )
    
    # Test R:R calculations
    print("=== R:R Converter Engine Test ===")
    
    # Add test position
    success = rr_converter.add_rr_position(
        ticket=12345,
        symbol="EURUSD",
        direction=TradeDirection.BUY,
        entry_price=1.1000,
        current_price=1.1020,
        original_sl=1.0980,
        original_tp=1.1040,
        lot_size=0.1,
        target_ratios=[1.0, 1.5, 2.0, 3.0]
    )
    
    print(f"Added R:R position: {success}")
    
    # Get position info
    position_info = rr_converter.get_position_rr_info(12345)
    print(f"Position R:R info: {json.dumps(position_info, indent=2)}")
    
    # Test R:R optimization
    optimization_result = await rr_converter.optimize_rr_for_position(12345)
    print(f"R:R optimization result: {optimization_result}")
    
    # Get statistics
    stats = rr_converter.get_rr_statistics()
    print(f"R:R Statistics: {json.dumps(stats, indent=2)}")
    
    print("=== R:R Converter Engine Test Complete ===")


if __name__ == "__main__":
    asyncio.run(main())