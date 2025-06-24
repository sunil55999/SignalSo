"""
End of Week SL Remover for SignalOS
Implements prop firm stealth feature to remove or adjust stop losses before Friday market close
to prevent SL spikes and broker flagging
"""

import json
import logging
import asyncio
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path

class SLRemovalMode(Enum):
    REMOVE = "remove"
    WIDEN = "widen"
    IGNORE = "ignore"

class MarketType(Enum):
    FOREX = "forex"
    CRYPTO = "crypto"
    INDICES = "indices"
    COMMODITIES = "commodities"

@dataclass
class EndOfWeekConfig:
    enabled: bool = True
    mode: SLRemovalMode = SLRemovalMode.WIDEN
    activation_window_start: str = "15:30"  # UTC time Friday
    activation_window_end: str = "16:59"    # UTC time Friday
    widen_distance_pips: int = 300
    excluded_pairs: Optional[List[str]] = None
    excluded_market_types: Optional[List[MarketType]] = None
    prop_firm_mode: bool = True
    log_actions: bool = True
    notify_copilot: bool = True
    timezone_override: Optional[str] = None  # Optional timezone override

    def __post_init__(self):
        if self.excluded_pairs is None:
            self.excluded_pairs = []
        if self.excluded_market_types is None:
            self.excluded_market_types = [MarketType.CRYPTO]

@dataclass
class SLRemovalAction:
    ticket: int
    symbol: str
    original_sl: Optional[float]
    new_sl: Optional[float]
    action_type: str
    reason: str
    timestamp: datetime
    trade_direction: str
    entry_price: float
    pip_value: float

@dataclass
class TradeInfo:
    ticket: int
    symbol: str
    action: str  # BUY/SELL
    entry_price: float
    current_sl: Optional[float]
    current_tp: Optional[float]
    lot_size: float
    open_time: datetime

class EndOfWeekSLRemover:
    def __init__(self, config_file: str = "config.json", log_file: str = "logs/eow_sl_remover_log.json"):
        self.config_file = config_file
        self.log_file = log_file
        self.removal_history: List[SLRemovalAction] = []
        
        self._setup_logging()
        self.config = self._load_config()
        self._load_history()
        
        # Injected modules
        self.mt5_bridge = None
        self.copilot_bot = None
        self.market_data = None
        
        # Symbol categorization
        self.symbol_categories = self._init_symbol_categories()
    
    def _load_config(self) -> EndOfWeekConfig:
        """Load configuration from JSON file"""
        try:
            if Path(self.config_file).exists():
                with open(self.config_file, 'r') as f:
                    config_data = json.load(f)
                    eow_config = config_data.get('end_of_week_sl_remover', {})
                    return EndOfWeekConfig(**eow_config)
            else:
                return self._create_default_config()
        except Exception as e:
            self.logger.warning(f"Failed to load config, using defaults: {e}")
            return EndOfWeekConfig()
    
    def _create_default_config(self) -> EndOfWeekConfig:
        """Create default configuration and save to file"""
        default_config = EndOfWeekConfig()
        
        try:
            config_data = {}
            if Path(self.config_file).exists():
                with open(self.config_file, 'r') as f:
                    config_data = json.load(f)
            
            # Convert enum values to strings for JSON serialization
            config_dict = asdict(default_config)
            config_dict['mode'] = default_config.mode.value
            config_dict['excluded_market_types'] = [mt.value for mt in default_config.excluded_market_types] if default_config.excluded_market_types else []
            
            config_data['end_of_week_sl_remover'] = config_dict
            
            with open(self.config_file, 'w') as f:
                json.dump(config_data, f, indent=4)
                
        except Exception as e:
            self.logger.error(f"Failed to save default config: {e}")
        
        return default_config
    
    def _setup_logging(self):
        """Setup logging for EOW SL remover operations"""
        self.logger = logging.getLogger('EndOfWeekSLRemover')
        self.logger.setLevel(logging.INFO)
        
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
    
    def _load_history(self):
        """Load removal history from log file"""
        try:
            if Path(self.log_file).exists():
                with open(self.log_file, 'r') as f:
                    history_data = json.load(f)
                    
                for entry in history_data.get('removals', []):
                    action = SLRemovalAction(
                        ticket=entry['ticket'],
                        symbol=entry['symbol'],
                        original_sl=entry.get('original_sl'),
                        new_sl=entry.get('new_sl'),
                        action_type=entry['action_type'],
                        reason=entry['reason'],
                        timestamp=datetime.fromisoformat(entry['timestamp']),
                        trade_direction=entry['trade_direction'],
                        entry_price=entry['entry_price'],
                        pip_value=entry['pip_value']
                    )
                    self.removal_history.append(action)
        except Exception as e:
            self.logger.warning(f"Failed to load removal history: {e}")
    
    def _save_history(self):
        """Save removal history to log file"""
        try:
            Path(self.log_file).parent.mkdir(parents=True, exist_ok=True)
            
            # Keep only recent history to prevent file bloat
            recent_history = self.removal_history[-500:] if len(self.removal_history) > 500 else self.removal_history
            
            history_data = {
                'removals': [
                    {
                        'ticket': action.ticket,
                        'symbol': action.symbol,
                        'original_sl': action.original_sl,
                        'new_sl': action.new_sl,
                        'action_type': action.action_type,
                        'reason': action.reason,
                        'timestamp': action.timestamp.isoformat(),
                        'trade_direction': action.trade_direction,
                        'entry_price': action.entry_price,
                        'pip_value': action.pip_value
                    }
                    for action in recent_history
                ],
                'last_updated': datetime.now().isoformat()
            }
            
            with open(self.log_file, 'w') as f:
                json.dump(history_data, f, indent=2)
                
        except Exception as e:
            self.logger.error(f"Failed to save removal history: {e}")
    
    def _init_symbol_categories(self) -> Dict[str, MarketType]:
        """Initialize symbol categorization"""
        return {
            # Forex majors
            'EURUSD': MarketType.FOREX, 'GBPUSD': MarketType.FOREX, 'USDJPY': MarketType.FOREX,
            'USDCHF': MarketType.FOREX, 'AUDUSD': MarketType.FOREX, 'USDCAD': MarketType.FOREX,
            'NZDUSD': MarketType.FOREX,
            
            # Forex minors
            'EURGBP': MarketType.FOREX, 'EURJPY': MarketType.FOREX, 'GBPJPY': MarketType.FOREX,
            'EURCHF': MarketType.FOREX, 'EURAUD': MarketType.FOREX, 'EURCAD': MarketType.FOREX,
            'GBPAUD': MarketType.FOREX, 'GBPCAD': MarketType.FOREX, 'GBPCHF': MarketType.FOREX,
            'AUDJPY': MarketType.FOREX, 'AUDCAD': MarketType.FOREX, 'AUDCHF': MarketType.FOREX,
            'CADJPY': MarketType.FOREX, 'CHFJPY': MarketType.FOREX, 'NZDJPY': MarketType.FOREX,
            
            # Crypto
            'BTCUSD': MarketType.CRYPTO, 'ETHUSD': MarketType.CRYPTO, 'LTCUSD': MarketType.CRYPTO,
            'XRPUSD': MarketType.CRYPTO, 'ADAUSD': MarketType.CRYPTO, 'DOTUSD': MarketType.CRYPTO,
            
            # Indices
            'US30': MarketType.INDICES, 'SPX500': MarketType.INDICES, 'NAS100': MarketType.INDICES,
            'UK100': MarketType.INDICES, 'GER30': MarketType.INDICES, 'FRA40': MarketType.INDICES,
            'JPN225': MarketType.INDICES, 'AUS200': MarketType.INDICES,
            
            # Commodities
            'XAUUSD': MarketType.COMMODITIES, 'XAGUSD': MarketType.COMMODITIES,
            'USOIL': MarketType.COMMODITIES, 'UKOIL': MarketType.COMMODITIES,
        }
    
    def inject_modules(self, mt5_bridge=None, copilot_bot=None, market_data=None):
        """Inject module references for operations"""
        self.mt5_bridge = mt5_bridge
        self.copilot_bot = copilot_bot
        self.market_data = market_data
        self.logger.info("Modules injected successfully")
    
    def _get_market_type(self, symbol: str) -> MarketType:
        """Determine market type for symbol"""
        symbol_upper = symbol.upper()
        
        # Check exact match first
        if symbol_upper in self.symbol_categories:
            return self.symbol_categories[symbol_upper]
        
        # Pattern matching for unknown symbols
        if any(crypto in symbol_upper for crypto in ['BTC', 'ETH', 'LTC', 'XRP', 'ADA', 'DOT']):
            return MarketType.CRYPTO
        elif any(index in symbol_upper for index in ['US30', 'SPX', 'NAS', 'UK100', 'GER', 'FRA', 'JPN', 'AUS']):
            return MarketType.INDICES
        elif any(commodity in symbol_upper for commodity in ['XAU', 'XAG', 'OIL', 'GOLD', 'SILVER']):
            return MarketType.COMMODITIES
        else:
            # Default to forex for unknown symbols
            return MarketType.FOREX
    
    def _get_pip_value(self, symbol: str) -> float:
        """Get pip value for symbol"""
        symbol_upper = symbol.upper()
        
        # JPY pairs
        if 'JPY' in symbol_upper:
            return 0.01
        
        # Standard forex pairs
        if self._get_market_type(symbol) == MarketType.FOREX:
            return 0.0001
        
        # Commodities
        if symbol_upper in ['XAUUSD', 'GOLD']:
            return 0.1
        elif symbol_upper in ['XAGUSD', 'SILVER']:
            return 0.001
        elif 'OIL' in symbol_upper:
            return 0.01
        
        # Indices (varies by broker, using common values)
        if symbol_upper in ['US30', 'GER30']:
            return 1.0
        elif symbol_upper in ['SPX500', 'NAS100']:
            return 0.1
        
        # Default
        return 0.0001
    
    def _is_friday_close_window(self, current_time: Optional[datetime] = None) -> bool:
        """Check if current time is within Friday close window"""
        if current_time is None:
            current_time = datetime.now(timezone.utc)
        
        # Use configured timezone if specified (simplified for now - using UTC)
        if self.config.timezone_override:
            self.logger.info(f"Timezone override {self.config.timezone_override} configured but using UTC for calculations")
        
        # Check if it's Friday
        if current_time.weekday() != 4:  # 4 = Friday
            return False
        
        # Parse time window
        try:
            start_time = datetime.strptime(self.config.activation_window_start, "%H:%M").time()
            end_time = datetime.strptime(self.config.activation_window_end, "%H:%M").time()
            current_time_only = current_time.time()
            
            return start_time <= current_time_only <= end_time
        except Exception as e:
            self.logger.error(f"Failed to parse time window: {e}")
            return False
    
    def _should_process_symbol(self, symbol: str) -> Tuple[bool, str]:
        """Check if symbol should be processed based on configuration"""
        # Check excluded pairs
        excluded_pairs = self.config.excluded_pairs or []
        if symbol.upper() in [pair.upper() for pair in excluded_pairs]:
            return False, f"Symbol {symbol} is in excluded pairs list"
        
        # Check excluded market types
        market_type = self._get_market_type(symbol)
        excluded_market_types = self.config.excluded_market_types or []
        if market_type in excluded_market_types:
            return False, f"Market type {market_type.value} is excluded"
        
        return True, "Symbol approved for processing"
    
    async def _get_open_trades(self) -> List[TradeInfo]:
        """Get list of open trades from MT5 bridge"""
        if not self.mt5_bridge:
            self.logger.warning("MT5 bridge not available")
            return []
        
        try:
            # This would be the actual MT5 bridge call
            # positions = await self.mt5_bridge.get_open_positions()
            
            # Mock data for testing - replace with actual bridge call
            mock_positions = [
                {
                    'ticket': 12345,
                    'symbol': 'EURUSD',
                    'type': 0,  # 0=BUY, 1=SELL
                    'volume': 0.1,
                    'price_open': 1.0850,
                    'sl': 1.0800,
                    'tp': 1.0900,
                    'time': datetime.now()
                },
                {
                    'ticket': 12346,
                    'symbol': 'GBPUSD',
                    'type': 1,  # SELL
                    'volume': 0.05,
                    'price_open': 1.2750,
                    'sl': 1.2800,
                    'tp': 1.2700,
                    'time': datetime.now()
                }
            ]
            
            trades = []
            for pos in mock_positions:
                trade = TradeInfo(
                    ticket=pos['ticket'],
                    symbol=pos['symbol'],
                    action='BUY' if pos['type'] == 0 else 'SELL',
                    entry_price=pos['price_open'],
                    current_sl=pos.get('sl'),
                    current_tp=pos.get('tp'),
                    lot_size=pos['volume'],
                    open_time=pos['time']
                )
                trades.append(trade)
            
            return trades
            
        except Exception as e:
            self.logger.error(f"Failed to get open trades: {e}")
            return []
    
    def _calculate_widened_sl(self, trade: TradeInfo) -> Optional[float]:
        """Calculate widened stop loss position"""
        if not trade.current_sl:
            return None
        
        pip_value = self._get_pip_value(trade.symbol)
        widen_amount = self.config.widen_distance_pips * pip_value
        
        if trade.action == 'BUY':
            # For BUY trades, move SL further down (away from current price)
            new_sl = trade.current_sl - widen_amount
        else:
            # For SELL trades, move SL further up (away from current price)
            new_sl = trade.current_sl + widen_amount
        
        return new_sl
    
    async def _update_trade_sl(self, ticket: int, new_sl: Optional[float]) -> bool:
        """Update trade stop loss via MT5 bridge"""
        if not self.mt5_bridge:
            self.logger.warning("MT5 bridge not available")
            return False
        
        try:
            # This would be the actual MT5 bridge call
            # success = await self.mt5_bridge.modify_position(ticket, sl=new_sl)
            
            # Mock success for testing
            self.logger.info(f"Mock SL update: Ticket {ticket} SL -> {new_sl}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to update SL for ticket {ticket}: {e}")
            return False

    async def run_end_of_week_check(self, current_time: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Main scheduled check function for end of week SL removal
        Should be called by auto_sync.py or scheduled job
        """
        if current_time is None:
            current_time = datetime.now(timezone.utc)
        
        # Check if we're in the activation window
        if not self._is_friday_close_window(current_time):
            return {
                'executed': False,
                'reason': 'Outside Friday close window',
                'current_time': current_time.isoformat(),
                'next_check': 'Next Friday 15:30 UTC'
            }
        
        if not self.config.enabled:
            return {
                'executed': False,
                'reason': 'End of week SL remover disabled',
                'current_time': current_time.isoformat()
            }
        
        # Get open trades
        open_trades = await self._get_open_trades()
        
        if not open_trades:
            return {
                'executed': True,
                'reason': 'No open trades to process',
                'trades_processed': 0,
                'current_time': current_time.isoformat()
            }
        
        # Process each trade
        processed_trades = []
        successful_modifications = 0
        
        for trade in open_trades:
            # Check if symbol should be processed
            should_process, process_reason = self._should_process_symbol(trade.symbol)
            
            if not should_process:
                self.logger.info(f"Skipping {trade.symbol} (ticket {trade.ticket}): {process_reason}")
                continue
            
            # Only process trades with stop losses
            if not trade.current_sl:
                self.logger.info(f"Skipping ticket {trade.ticket} - no stop loss set")
                continue
            
            # Process based on configured mode
            success = False
            action_type = self.config.mode.value
            new_sl = None
            
            if self.config.mode == SLRemovalMode.REMOVE:
                # Remove stop loss completely
                success = await self._update_trade_sl(trade.ticket, None)
                new_sl = None
                
            elif self.config.mode == SLRemovalMode.WIDEN:
                # Widen stop loss
                new_sl = self._calculate_widened_sl(trade)
                if new_sl:
                    success = await self._update_trade_sl(trade.ticket, new_sl)
                else:
                    self.logger.warning(f"Could not calculate widened SL for ticket {trade.ticket}")
                    continue
            
            elif self.config.mode == SLRemovalMode.IGNORE:
                # Do nothing
                self.logger.info(f"Ignoring trade {trade.ticket} due to IGNORE mode")
                continue
            
            # Record the action
            pip_value = self._get_pip_value(trade.symbol)
            
            action = SLRemovalAction(
                ticket=trade.ticket,
                symbol=trade.symbol,
                original_sl=trade.current_sl,
                new_sl=new_sl,
                action_type=action_type,
                reason=f"End of week {action_type} - Friday close protection",
                timestamp=current_time,
                trade_direction=trade.action,
                entry_price=trade.entry_price,
                pip_value=pip_value
            )
            
            self.removal_history.append(action)
            processed_trades.append({
                'ticket': trade.ticket,
                'symbol': trade.symbol,
                'action': action_type,
                'success': success,
                'original_sl': trade.current_sl,
                'new_sl': new_sl
            })
            
            if success:
                successful_modifications += 1
                self.logger.info(f"Successfully {action_type} SL for {trade.symbol} ticket {trade.ticket}")
                
                # Send copilot notification if enabled
                if self.config.notify_copilot and self.copilot_bot:
                    await self._send_copilot_notification(action)
            else:
                self.logger.error(f"Failed to {action_type} SL for {trade.symbol} ticket {trade.ticket}")
        
        # Save history
        self._save_history()
        
        return {
            'executed': True,
            'trades_processed': len(processed_trades),
            'successful_modifications': successful_modifications,
            'failed_modifications': len(processed_trades) - successful_modifications,
            'mode': self.config.mode.value,
            'processed_trades': processed_trades,
            'current_time': current_time.isoformat()
        }

    async def _send_copilot_notification(self, action: SLRemovalAction):
        """Send notification to copilot bot about SL modification"""
        try:
            if action.action_type == "remove":
                message = f"🕐 EOW SL Removed: {action.symbol} (#{action.ticket})\nOriginal SL: {action.original_sl}"
            else:
                pips_moved = abs((action.new_sl - action.original_sl) / action.pip_value) if action.new_sl and action.original_sl else 0
                message = f"🕐 EOW SL Widened: {action.symbol} (#{action.ticket})\nOriginal: {action.original_sl} → New: {action.new_sl}\nWidened by: {pips_moved:.1f} pips"
            
            # This would be the actual copilot notification
            # await self.copilot_bot.send_alert(message)
            self.logger.info(f"EOW notification: {message}")
            
        except Exception as e:
            self.logger.error(f"Failed to send EOW copilot notification: {e}")

    def schedule_with_auto_sync(self, auto_sync_module):
        """Integration hook for auto_sync.py to schedule EOW checks"""
        try:
            # Register EOW check with auto_sync scheduler
            # This would integrate with the actual auto_sync scheduling system
            self.logger.info("End of week SL remover scheduled with auto_sync")
            return True
        except Exception as e:
            self.logger.error(f"Failed to schedule with auto_sync: {e}")
            return False: {e}")
            return False
    
    async def _send_copilot_notification(self, action: SLRemovalAction):
        """Send notification to Copilot Bot"""
        if not self.config.notify_copilot or not self.copilot_bot:
            return
        
        try:
            if action.action_type == "remove":
                message = f"🔄 EOW SL Removed: {action.symbol} (#{action.ticket})\nOriginal SL: {action.original_sl}"
            elif action.action_type == "widen":
                message = f"🔄 EOW SL Widened: {action.symbol} (#{action.ticket})\n{action.original_sl} → {action.new_sl}"
            else:
                message = f"🔄 EOW SL Action: {action.symbol} (#{action.ticket})\n{action.reason}"
            
            # This would be the actual copilot bot call
            # await self.copilot_bot.send_alert(message)
            self.logger.info(f"Copilot notification: {message}")
            
        except Exception as e:
            self.logger.error(f"Failed to send copilot notification: {e}")
    
    async def process_end_of_week_sl_removal(self, force_run: bool = False) -> Dict[str, Any]:
        """
        Main function to process end-of-week SL removal
        
        Args:
            force_run: If True, bypass time window check (for testing)
            
        Returns:
            Dictionary with processing results
        """
        if not self.config.enabled and not force_run:
            return {
                "processed": False,
                "reason": "End-of-week SL removal is disabled",
                "actions": []
            }
        
        current_time = datetime.now(timezone.utc)
        
        # Check if we're in the activation window
        if not force_run and not self._is_friday_close_window(current_time):
            return {
                "processed": False,
                "reason": f"Not in activation window. Current time: {current_time.strftime('%A %H:%M UTC')}",
                "actions": []
            }
        
        self.logger.info(f"Starting end-of-week SL processing at {current_time}")
        
        # Get open trades
        open_trades = await self._get_open_trades()
        
        if not open_trades:
            return {
                "processed": True,
                "reason": "No open trades found",
                "actions": []
            }
        
        actions_taken = []
        
        for trade in open_trades:
            # Check if symbol should be processed
            should_process, reason = self._should_process_symbol(trade.symbol)
            
            if not should_process:
                self.logger.info(f"Skipping {trade.symbol} (#{trade.ticket}): {reason}")
                continue
            
            # Skip trades without stop loss if mode is not 'ignore'
            if not trade.current_sl and self.config.mode != SLRemovalMode.IGNORE:
                self.logger.info(f"Skipping {trade.symbol} (#{trade.ticket}): No stop loss set")
                continue
            
            pip_value = self._get_pip_value(trade.symbol)
            action_taken = None
            
            if self.config.mode == SLRemovalMode.REMOVE:
                # Remove stop loss completely
                success = await self._update_trade_sl(trade.ticket, None)
                
                if success:
                    action_taken = SLRemovalAction(
                        ticket=trade.ticket,
                        symbol=trade.symbol,
                        original_sl=trade.current_sl,
                        new_sl=None,
                        action_type="remove",
                        reason="End-of-week SL removal",
                        timestamp=current_time,
                        trade_direction=trade.action,
                        entry_price=trade.entry_price,
                        pip_value=pip_value
                    )
                    
                    self.logger.info(f"Removed SL for {trade.symbol} (#{trade.ticket})")
            
            elif self.config.mode == SLRemovalMode.WIDEN:
                # Widen stop loss
                new_sl = self._calculate_widened_sl(trade)
                
                if new_sl and new_sl != trade.current_sl:
                    success = await self._update_trade_sl(trade.ticket, new_sl)
                    
                    if success:
                        action_taken = SLRemovalAction(
                            ticket=trade.ticket,
                            symbol=trade.symbol,
                            original_sl=trade.current_sl,
                            new_sl=new_sl,
                            action_type="widen",
                            reason=f"Widened SL by {self.config.widen_distance_pips} pips",
                            timestamp=current_time,
                            trade_direction=trade.action,
                            entry_price=trade.entry_price,
                            pip_value=pip_value
                        )
                        
                        self.logger.info(f"Widened SL for {trade.symbol} (#{trade.ticket}): {trade.current_sl} → {new_sl}")
            
            elif self.config.mode == SLRemovalMode.IGNORE:
                # Log but don't modify
                action_taken = SLRemovalAction(
                    ticket=trade.ticket,
                    symbol=trade.symbol,
                    original_sl=trade.current_sl,
                    new_sl=trade.current_sl,
                    action_type="ignore",
                    reason="EOW processing - mode set to ignore",
                    timestamp=current_time,
                    trade_direction=trade.action,
                    entry_price=trade.entry_price,
                    pip_value=pip_value
                )
                
                self.logger.info(f"Ignored {trade.symbol} (#{trade.ticket}) as per configuration")
            
            if action_taken:
                self.removal_history.append(action_taken)
                actions_taken.append(action_taken)
                
                # Send notification if enabled
                if self.config.notify_copilot:
                    await self._send_copilot_notification(action_taken)
        
        # Save history
        if actions_taken:
            self._save_history()
        
        result = {
            "processed": True,
            "reason": f"Processed {len(open_trades)} trades, took {len(actions_taken)} actions",
            "actions": [
                {
                    "ticket": action.ticket,
                    "symbol": action.symbol,
                    "action_type": action.action_type,
                    "original_sl": action.original_sl,
                    "new_sl": action.new_sl,
                    "reason": action.reason
                }
                for action in actions_taken
            ],
            "timestamp": current_time.isoformat()
        }
        
        self.logger.info(f"End-of-week SL processing completed: {result['reason']}")
        return result
    
    def get_removal_statistics(self) -> Dict[str, Any]:
        """Get statistics about SL removal operations"""
        if not self.removal_history:
            return {
                "total_actions": 0,
                "by_action_type": {},
                "symbols_processed": 0,
                "last_action": None
            }
        
        total_actions = len(self.removal_history)
        
        # Count by action type
        action_counts = {}
        for action in self.removal_history:
            action_counts[action.action_type] = action_counts.get(action.action_type, 0) + 1
        
        symbols_processed = len(set(action.symbol for action in self.removal_history))
        last_action = self.removal_history[-1].timestamp.isoformat()
        
        return {
            "total_actions": total_actions,
            "by_action_type": action_counts,
            "symbols_processed": symbols_processed,
            "last_action": last_action,
            "current_mode": self.config.mode.value,
            "enabled": self.config.enabled
        }
    
    def get_recent_actions(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent SL removal actions"""
        recent = self.removal_history[-limit:] if self.removal_history else []
        return [
            {
                "ticket": action.ticket,
                "symbol": action.symbol,
                "action_type": action.action_type,
                "original_sl": action.original_sl,
                "new_sl": action.new_sl,
                "reason": action.reason,
                "timestamp": action.timestamp.isoformat(),
                "trade_direction": action.trade_direction
            }
            for action in recent
        ]
    
    def update_config(self, new_config: Dict[str, Any]):
        """Update configuration parameters"""
        try:
            # Update config object
            for key, value in new_config.items():
                if hasattr(self.config, key):
                    if key == 'mode' and isinstance(value, str):
                        setattr(self.config, key, SLRemovalMode(value))
                    elif key == 'excluded_market_types' and isinstance(value, list):
                        setattr(self.config, key, [MarketType(mt) if isinstance(mt, str) else mt for mt in value])
                    else:
                        setattr(self.config, key, value)
            
            # Save to file
            config_data = {}
            if Path(self.config_file).exists():
                with open(self.config_file, 'r') as f:
                    config_data = json.load(f)
            
            config_data['end_of_week_sl_remover'] = asdict(self.config)
            
            with open(self.config_file, 'w') as f:
                json.dump(config_data, f, indent=4)
            
            self.logger.info(f"Configuration updated: {new_config}")
            
        except Exception as e:
            self.logger.error(f"Failed to update configuration: {e}")

# Example usage
async def main():
    """Example usage of End of Week SL Remover"""
    remover = EndOfWeekSLRemover()
    
    # Mock MT5 bridge
    class MockMT5Bridge:
        async def get_open_positions(self):
            return []
        
        async def modify_position(self, ticket, sl=None):
            return True
    
    # Inject modules
    mt5_bridge = MockMT5Bridge()
    remover.inject_modules(mt5_bridge=mt5_bridge)
    
    # Test processing (force run to bypass time window)
    result = await remover.process_end_of_week_sl_removal(force_run=True)
    
    print(f"Processing result: {result}")
    
    # Get statistics
    stats = remover.get_removal_statistics()
    print(f"Statistics: {stats}")

if __name__ == "__main__":
    asyncio.run(main())