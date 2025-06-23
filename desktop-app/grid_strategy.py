"""
Grid Strategy Engine for SignalOS
Implements grid trading strategy with dynamic level calculation and risk management
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
import math

class GridDirection(Enum):
    BUY_GRID = "buy_grid"
    SELL_GRID = "sell_grid"
    BIDIRECTIONAL = "bidirectional"

class GridStatus(Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    STOPPED = "stopped"
    RECOVERING = "recovering"

class OrderType(Enum):
    BUY_LIMIT = "buy_limit"
    SELL_LIMIT = "sell_limit"
    BUY_STOP = "buy_stop"
    SELL_STOP = "sell_stop"

@dataclass
class GridLevel:
    level_id: str
    price: float
    order_type: OrderType
    volume: float
    is_filled: bool = False
    order_ticket: Optional[int] = None
    fill_time: Optional[datetime] = None
    fill_price: Optional[float] = None

@dataclass
class GridConfiguration:
    symbol: str
    direction: GridDirection
    center_price: float
    grid_spacing_pips: float
    levels_above: int
    levels_below: int
    base_volume: float
    volume_multiplier: float = 1.0
    max_spread_pips: float = 3.0
    profit_target_pips: float = 20.0
    stop_loss_pips: Optional[float] = None
    max_total_volume: float = 1.0
    enable_martingale: bool = False
    martingale_multiplier: float = 1.5
    adaptive_spacing: bool = True
    volatility_multiplier: float = 1.0

@dataclass
class GridInstance:
    grid_id: str
    config: GridConfiguration
    status: GridStatus
    levels: List[GridLevel]
    created_time: datetime
    total_invested: float = 0.0
    total_profit: float = 0.0
    active_orders: int = 0
    filled_orders: int = 0
    last_update: Optional[datetime] = None
    recovery_price: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "grid_id": self.grid_id,
            "symbol": self.config.symbol,
            "direction": self.config.direction.value,
            "status": self.status.value,
            "center_price": self.config.center_price,
            "total_levels": len(self.levels),
            "active_orders": self.active_orders,
            "filled_orders": self.filled_orders,
            "total_invested": self.total_invested,
            "total_profit": self.total_profit,
            "created_time": self.created_time.isoformat(),
            "last_update": self.last_update.isoformat() if self.last_update else None
        }

@dataclass
class GridEvent:
    event_id: str
    grid_id: str
    event_type: str  # "level_filled", "profit_taken", "grid_reset", "error"
    level_id: Optional[str]
    price: float
    volume: float
    profit: float
    timestamp: datetime
    details: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "grid_id": self.grid_id,
            "event_type": self.event_type,
            "level_id": self.level_id,
            "price": self.price,
            "volume": self.volume,
            "profit": self.profit,
            "timestamp": self.timestamp.isoformat(),
            "details": self.details
        }

class GridStrategy:
    def __init__(self, config_path: str = "config.json", log_path: str = "logs/grid_strategy.log"):
        self.config_path = config_path
        self.log_path = log_path
        self.config = self._load_config()
        self.logger = self._setup_logger()
        
        # Grid management
        self.active_grids: Dict[str, GridInstance] = {}
        self.grid_history: List[GridEvent] = []
        
        # Market data cache
        self.market_cache: Dict[str, Dict[str, Any]] = {}
        self.cache_duration = 5  # seconds
        
        # Module dependencies
        self.mt5_bridge = None
        self.margin_checker = None
        self.spread_checker = None
        
        # Background monitoring
        self.monitoring_task = None
        self.is_monitoring = False
        
        # Load existing grids
        self._load_grid_data()
        
    def _load_config(self) -> Dict[str, Any]:
        """Load grid strategy configuration"""
        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)
                
            if "grid_strategy" not in config:
                config["grid_strategy"] = {
                    "enabled": True,
                    "monitoring_interval": 5.0,
                    "max_active_grids": 5,
                    "default_grid_spacing_pips": 10.0,
                    "default_profit_target_pips": 20.0,
                    "max_grid_levels": 20,
                    "min_account_balance": 1000.0,
                    "max_risk_percentage": 10.0,
                    "enable_recovery_mode": True,
                    "recovery_multiplier": 1.2,
                    "symbol_configs": {
                        "EURUSD": {
                            "grid_spacing_pips": 8.0,
                            "max_levels": 15,
                            "base_volume": 0.01,
                            "profit_target_pips": 15.0,
                            "max_spread_pips": 2.0
                        },
                        "GBPUSD": {
                            "grid_spacing_pips": 10.0,
                            "max_levels": 12,
                            "base_volume": 0.01,
                            "profit_target_pips": 20.0,
                            "max_spread_pips": 3.0
                        },
                        "XAUUSD": {
                            "grid_spacing_pips": 50.0,
                            "max_levels": 10,
                            "base_volume": 0.01,
                            "profit_target_pips": 100.0,
                            "max_spread_pips": 10.0
                        }
                    }
                }
                self._save_config(config)
                
            return config.get("grid_strategy", {})
            
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
            "monitoring_interval": 5.0,
            "max_active_grids": 5,
            "default_grid_spacing_pips": 10.0,
            "default_profit_target_pips": 20.0,
            "max_grid_levels": 20,
            "min_account_balance": 1000.0,
            "max_risk_percentage": 10.0,
            "enable_recovery_mode": True,
            "recovery_multiplier": 1.2,
            "symbol_configs": {}
        }
        
    def _save_config(self, full_config: Dict[str, Any]):
        """Save updated configuration"""
        try:
            with open(self.config_path, 'w') as f:
                json.dump(full_config, f, indent=4)
        except Exception as e:
            self.logger.error(f"Failed to save config: {e}")
            
    def _setup_logger(self) -> logging.Logger:
        """Setup dedicated logger for grid strategy"""
        logger = logging.getLogger("grid_strategy")
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
        
    def _load_grid_data(self):
        """Load existing grid data from storage"""
        grid_file = self.log_path.replace('.log', '_grids.json')
        try:
            if os.path.exists(grid_file):
                with open(grid_file, 'r') as f:
                    grid_data = json.load(f)
                    
                # Load active grids (simplified reconstruction)
                for grid_data_item in grid_data.get('active_grids', []):
                    # In production, you'd want full reconstruction
                    pass
                    
                self.logger.info(f"Loaded {len(self.active_grids)} active grids from storage")
                
        except Exception as e:
            self.logger.error(f"Error loading grid data: {e}")
            
    def _save_grid_data(self):
        """Save grid data to storage"""
        grid_file = self.log_path.replace('.log', '_grids.json')
        try:
            grid_data = {
                'active_grids': [grid.to_dict() for grid in self.active_grids.values()],
                'last_updated': datetime.now().isoformat()
            }
            
            with open(grid_file, 'w') as f:
                json.dump(grid_data, f, indent=4)
                
        except Exception as e:
            self.logger.error(f"Error saving grid data: {e}")
            
    def set_dependencies(self, mt5_bridge=None, margin_checker=None, spread_checker=None):
        """Set module dependencies"""
        self.mt5_bridge = mt5_bridge
        self.margin_checker = margin_checker
        self.spread_checker = spread_checker
        
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
        
    def _get_current_price(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get current market price for symbol"""
        try:
            # Check cache first
            if symbol in self.market_cache:
                cached_data, cache_time = self.market_cache[symbol]
                if time.time() - cache_time < self.cache_duration:
                    return cached_data
                    
            if not self.mt5_bridge:
                self.logger.warning("MT5 bridge not available")
                return None
                
            tick_data = self.mt5_bridge.get_symbol_tick(symbol)
            if not tick_data:
                return None
                
            price_data = {
                'symbol': symbol,
                'bid': tick_data.get('bid', 0),
                'ask': tick_data.get('ask', 0),
                'mid': (tick_data.get('bid', 0) + tick_data.get('ask', 0)) / 2,
                'time': tick_data.get('time', datetime.now())
            }
            
            # Cache the result
            self.market_cache[symbol] = (price_data, time.time())
            return price_data
            
        except Exception as e:
            self.logger.error(f"Error getting price for {symbol}: {e}")
            return None
            
    def _calculate_volatility(self, symbol: str, periods: int = 20) -> float:
        """Calculate market volatility for adaptive grid spacing"""
        try:
            # Simplified volatility calculation
            # In production, you'd use historical price data
            if symbol == "XAUUSD":
                return 2.5  # High volatility
            elif symbol in ["EURUSD", "GBPUSD"]:
                return 1.0  # Normal volatility
            else:
                return 1.5  # Medium volatility
                
        except Exception as e:
            self.logger.error(f"Error calculating volatility for {symbol}: {e}")
            return 1.0
            
    def _get_symbol_config(self, symbol: str) -> Dict[str, Any]:
        """Get symbol-specific configuration"""
        symbol_configs = self.config.get("symbol_configs", {})
        if symbol in symbol_configs:
            return symbol_configs[symbol]
            
        # Return default config
        return {
            "grid_spacing_pips": self.config.get("default_grid_spacing_pips", 10.0),
            "max_levels": self.config.get("max_grid_levels", 20) // 2,
            "base_volume": 0.01,
            "profit_target_pips": self.config.get("default_profit_target_pips", 20.0),
            "max_spread_pips": 3.0
        }
        
    def _calculate_grid_spacing(self, symbol: str, volatility: float, adaptive: bool = True) -> float:
        """Calculate optimal grid spacing based on market conditions"""
        symbol_config = self._get_symbol_config(symbol)
        base_spacing = symbol_config.get("grid_spacing_pips", 10.0)
        
        if not adaptive:
            return base_spacing
            
        # Adjust based on volatility
        volatility_factor = max(0.5, min(2.0, volatility))
        adjusted_spacing = base_spacing * volatility_factor
        
        return adjusted_spacing
        
    def _calculate_position_size(self, symbol: str, level: int, base_volume: float, 
                               enable_martingale: bool = False, multiplier: float = 1.5) -> float:
        """Calculate position size for grid level"""
        if not enable_martingale:
            return base_volume
            
        # Martingale progression: increase size for levels further from center
        level_multiplier = multiplier ** abs(level)
        return base_volume * level_multiplier
        
    def _create_grid_levels(self, config: GridConfiguration) -> List[GridLevel]:
        """Create grid levels based on configuration"""
        levels = []
        pip_value = self._get_pip_value(config.symbol)
        spacing_price = config.grid_spacing_pips * pip_value
        
        # Create buy levels (below center price)
        for i in range(1, config.levels_below + 1):
            level_price = config.center_price - (spacing_price * i)
            volume = self._calculate_position_size(
                config.symbol, -i, config.base_volume, 
                config.enable_martingale, config.martingale_multiplier
            )
            
            level = GridLevel(
                level_id=f"buy_{i}",
                price=level_price,
                order_type=OrderType.BUY_LIMIT,
                volume=volume
            )
            levels.append(level)
            
        # Create sell levels (above center price)
        for i in range(1, config.levels_above + 1):
            level_price = config.center_price + (spacing_price * i)
            volume = self._calculate_position_size(
                config.symbol, i, config.base_volume,
                config.enable_martingale, config.martingale_multiplier
            )
            
            level = GridLevel(
                level_id=f"sell_{i}",
                price=level_price,
                order_type=OrderType.SELL_LIMIT,
                volume=volume
            )
            levels.append(level)
            
        return levels
        
    async def _check_margin_requirements(self, config: GridConfiguration, levels: List[GridLevel]) -> bool:
        """Check if account has sufficient margin for grid"""
        try:
            if not self.margin_checker:
                self.logger.warning("Margin checker not available")
                return True  # Assume OK if checker not available
                
            total_volume = sum(level.volume for level in levels)
            
            # Check margin for the total grid volume
            margin_result = await self.margin_checker.check_margin_for_trade(
                config.symbol, total_volume, "buy"
            )
            
            return margin_result.allowed
            
        except Exception as e:
            self.logger.error(f"Error checking margin requirements: {e}")
            return False
            
    async def _place_grid_order(self, level: GridLevel, symbol: str) -> bool:
        """Place a single grid order"""
        try:
            if not self.mt5_bridge:
                self.logger.error("MT5 bridge not available")
                return False
                
            # Check spread before placing order
            if self.spread_checker:
                spread_result, _ = self.spread_checker.check_spread_before_trade(symbol)
                if spread_result.value != "allowed":
                    self.logger.warning(f"Spread too high for {symbol}, skipping order")
                    return False
                    
            # Place order based on type
            if level.order_type == OrderType.BUY_LIMIT:
                order_result = await self.mt5_bridge.place_buy_limit_order(
                    symbol=symbol,
                    volume=level.volume,
                    price=level.price,
                    comment=f"Grid_Buy_{level.level_id}"
                )
            elif level.order_type == OrderType.SELL_LIMIT:
                order_result = await self.mt5_bridge.place_sell_limit_order(
                    symbol=symbol,
                    volume=level.volume,
                    price=level.price,
                    comment=f"Grid_Sell_{level.level_id}"
                )
            else:
                self.logger.error(f"Unsupported order type: {level.order_type}")
                return False
                
            if order_result.get('success', False):
                level.order_ticket = order_result.get('ticket')
                self.logger.info(f"Grid order placed: {level.level_id} at {level.price} (Ticket: {level.order_ticket})")
                return True
            else:
                error_msg = order_result.get('error', 'Unknown error')
                self.logger.error(f"Failed to place grid order {level.level_id}: {error_msg}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error placing grid order {level.level_id}: {e}")
            return False
            
    async def create_grid(self, symbol: str, direction: GridDirection, center_price: Optional[float] = None,
                         levels_above: int = 5, levels_below: int = 5, base_volume: float = 0.01,
                         custom_spacing: Optional[float] = None) -> Optional[str]:
        """Create a new grid trading instance"""
        try:
            if not self.config.get("enabled", True):
                self.logger.warning("Grid strategy is disabled")
                return None
                
            # Check maximum active grids limit
            max_grids = self.config.get("max_active_grids", 5)
            if len(self.active_grids) >= max_grids:
                self.logger.warning(f"Maximum active grids limit reached: {max_grids}")
                return None
                
            # Get current price if not provided
            if center_price is None:
                price_data = self._get_current_price(symbol)
                if not price_data:
                    self.logger.error(f"Could not get current price for {symbol}")
                    return None
                center_price = price_data['mid']
                
            # Calculate volatility and spacing
            volatility = self._calculate_volatility(symbol)
            spacing_pips = custom_spacing or self._calculate_grid_spacing(symbol, volatility, True)
            
            # Get symbol configuration
            symbol_config = self._get_symbol_config(symbol)
            
            # Create grid configuration
            config = GridConfiguration(
                symbol=symbol,
                direction=direction,
                center_price=center_price,
                grid_spacing_pips=spacing_pips,
                levels_above=min(levels_above, symbol_config.get("max_levels", 10)),
                levels_below=min(levels_below, symbol_config.get("max_levels", 10)),
                base_volume=base_volume,
                max_spread_pips=symbol_config.get("max_spread_pips", 3.0),
                profit_target_pips=symbol_config.get("profit_target_pips", 20.0),
                adaptive_spacing=True,
                volatility_multiplier=volatility
            )
            
            # Create grid levels
            levels = self._create_grid_levels(config)
            
            # Check margin requirements
            margin_ok = await self._check_margin_requirements(config, levels)
            if not margin_ok:
                self.logger.error(f"Insufficient margin for grid {symbol}")
                return None
                
            # Create grid instance
            grid_id = f"grid_{symbol}_{int(datetime.now().timestamp())}"
            grid_instance = GridInstance(
                grid_id=grid_id,
                config=config,
                status=GridStatus.ACTIVE,
                levels=levels,
                created_time=datetime.now()
            )
            
            # Place initial grid orders
            successful_orders = 0
            for level in levels:
                success = await self._place_grid_order(level, symbol)
                if success:
                    successful_orders += 1
                    grid_instance.active_orders += 1
                    
            if successful_orders == 0:
                self.logger.error(f"Failed to place any grid orders for {symbol}")
                return None
                
            # Add to active grids
            self.active_grids[grid_id] = grid_instance
            
            # Start monitoring if not already running
            if not self.is_monitoring:
                self.start_monitoring()
                
            self.logger.info(f"Grid created successfully: {grid_id} with {successful_orders}/{len(levels)} orders")
            
            # Save grid data
            self._save_grid_data()
            
            return grid_id
            
        except Exception as e:
            self.logger.error(f"Error creating grid for {symbol}: {e}")
            return None
            
    async def stop_grid(self, grid_id: str, close_positions: bool = True) -> bool:
        """Stop a grid and optionally close all positions"""
        try:
            if grid_id not in self.active_grids:
                self.logger.warning(f"Grid {grid_id} not found")
                return False
                
            grid = self.active_grids[grid_id]
            grid.status = GridStatus.STOPPED
            
            if close_positions and self.mt5_bridge:
                # Cancel pending orders
                for level in grid.levels:
                    if level.order_ticket and not level.is_filled:
                        try:
                            cancel_result = await self.mt5_bridge.cancel_order(level.order_ticket)
                            if cancel_result.get('success'):
                                self.logger.info(f"Cancelled order {level.order_ticket} for level {level.level_id}")
                        except Exception as e:
                            self.logger.error(f"Error cancelling order {level.order_ticket}: {e}")
                            
                # Close filled positions
                for level in grid.levels:
                    if level.is_filled and level.order_ticket:
                        try:
                            close_result = await self.mt5_bridge.close_position(level.order_ticket)
                            if close_result.get('success'):
                                self.logger.info(f"Closed position {level.order_ticket} for level {level.level_id}")
                        except Exception as e:
                            self.logger.error(f"Error closing position {level.order_ticket}: {e}")
                            
            # Remove from active grids
            del self.active_grids[grid_id]
            
            self.logger.info(f"Grid {grid_id} stopped successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error stopping grid {grid_id}: {e}")
            return False
            
    async def _monitor_grid_levels(self, grid: GridInstance):
        """Monitor grid levels for fills and manage positions"""
        try:
            if not self.mt5_bridge:
                return
                
            # Get open orders and positions
            orders = await self.mt5_bridge.get_open_orders()
            positions = await self.mt5_bridge.get_open_positions()
            
            # Check for filled orders
            for level in grid.levels:
                if level.order_ticket and not level.is_filled:
                    # Check if order is still pending
                    order_exists = any(order.get('ticket') == level.order_ticket for order in orders)
                    
                    if not order_exists:
                        # Order might be filled, check positions
                        position = next((pos for pos in positions if pos.get('ticket') == level.order_ticket), None)
                        if position:
                            level.is_filled = True
                            level.fill_time = datetime.now()
                            level.fill_price = position.get('price_open', level.price)
                            grid.filled_orders += 1
                            grid.active_orders -= 1
                            
                            self.logger.info(f"Grid level filled: {level.level_id} at {level.fill_price}")
                            
                            # Create new opposite order if bidirectional
                            if grid.config.direction == GridDirection.BIDIRECTIONAL:
                                await self._create_opposite_order(grid, level)
                                
            # Update grid statistics
            grid.last_update = datetime.now()
            
        except Exception as e:
            self.logger.error(f"Error monitoring grid {grid.grid_id}: {e}")
            
    async def _create_opposite_order(self, grid: GridInstance, filled_level: GridLevel):
        """Create opposite order after a level is filled"""
        try:
            pip_value = self._get_pip_value(grid.config.symbol)
            profit_distance = grid.config.profit_target_pips * pip_value
            
            if filled_level.order_type == OrderType.BUY_LIMIT:
                # Create sell order above fill price
                opposite_price = filled_level.fill_price + profit_distance
                opposite_level = GridLevel(
                    level_id=f"profit_sell_{filled_level.level_id}",
                    price=opposite_price,
                    order_type=OrderType.SELL_LIMIT,
                    volume=filled_level.volume
                )
            else:
                # Create buy order below fill price
                opposite_price = filled_level.fill_price - profit_distance
                opposite_level = GridLevel(
                    level_id=f"profit_buy_{filled_level.level_id}",
                    price=opposite_price,
                    order_type=OrderType.BUY_LIMIT,
                    volume=filled_level.volume
                )
                
            # Place the opposite order
            success = await self._place_grid_order(opposite_level, grid.config.symbol)
            if success:
                grid.levels.append(opposite_level)
                grid.active_orders += 1
                
        except Exception as e:
            self.logger.error(f"Error creating opposite order for {filled_level.level_id}: {e}")
            
    async def _monitor_grids(self):
        """Background task to monitor all active grids"""
        while self.is_monitoring:
            try:
                if not self.active_grids:
                    await asyncio.sleep(self.config.get("monitoring_interval", 5.0))
                    continue
                    
                # Monitor each active grid
                for grid_id, grid in list(self.active_grids.items()):
                    if grid.status == GridStatus.ACTIVE:
                        await self._monitor_grid_levels(grid)
                        
                # Save grid data periodically
                self._save_grid_data()
                
                await asyncio.sleep(self.config.get("monitoring_interval", 5.0))
                
            except Exception as e:
                self.logger.error(f"Error in grid monitoring loop: {e}")
                await asyncio.sleep(10)  # Prevent tight error loop
                
    def start_monitoring(self):
        """Start background grid monitoring"""
        if not self.config.get('enabled', True):
            self.logger.info("Grid strategy is disabled")
            return
            
        if not self.is_monitoring:
            self.is_monitoring = True
            try:
                self.monitoring_task = asyncio.create_task(self._monitor_grids())
                self.logger.info("Grid monitoring started")
            except RuntimeError:
                self.is_monitoring = False
                self.logger.warning("No event loop running, cannot start monitoring")
                
    def stop_monitoring(self):
        """Stop background monitoring"""
        if self.is_monitoring:
            self.is_monitoring = False
            if self.monitoring_task:
                self.monitoring_task.cancel()
            self.logger.info("Grid monitoring stopped")
            
    def get_active_grids(self) -> Dict[str, Dict[str, Any]]:
        """Get information about all active grids"""
        return {grid_id: grid.to_dict() for grid_id, grid in self.active_grids.items()}
        
    def get_grid_details(self, grid_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific grid"""
        if grid_id not in self.active_grids:
            return None
            
        grid = self.active_grids[grid_id]
        
        return {
            "grid_info": grid.to_dict(),
            "levels": [
                {
                    "level_id": level.level_id,
                    "price": level.price,
                    "order_type": level.order_type.value,
                    "volume": level.volume,
                    "is_filled": level.is_filled,
                    "order_ticket": level.order_ticket,
                    "fill_time": level.fill_time.isoformat() if level.fill_time else None,
                    "fill_price": level.fill_price
                }
                for level in grid.levels
            ],
            "config": {
                "symbol": grid.config.symbol,
                "direction": grid.config.direction.value,
                "center_price": grid.config.center_price,
                "grid_spacing_pips": grid.config.grid_spacing_pips,
                "levels_above": grid.config.levels_above,
                "levels_below": grid.config.levels_below,
                "base_volume": grid.config.base_volume,
                "profit_target_pips": grid.config.profit_target_pips
            }
        }
        
    def get_statistics(self) -> Dict[str, Any]:
        """Get grid strategy statistics"""
        total_grids = len(self.active_grids)
        total_invested = sum(grid.total_invested for grid in self.active_grids.values())
        total_profit = sum(grid.total_profit for grid in self.active_grids.values())
        total_orders = sum(grid.active_orders for grid in self.active_grids.values())
        total_filled = sum(grid.filled_orders for grid in self.active_grids.values())
        
        return {
            "active_grids": total_grids,
            "total_invested": total_invested,
            "total_profit": total_profit,
            "total_active_orders": total_orders,
            "total_filled_orders": total_filled,
            "monitoring_active": self.is_monitoring,
            "max_grids_allowed": self.config.get("max_active_grids", 5)
        }

# Global instance for easy access
grid_strategy = GridStrategy()