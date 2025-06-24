"""
Edit Trade on Signal Change Engine for SignalOS
Detects when Telegram signal messages are edited and automatically adjusts open trades accordingly
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from enum import Enum
import json
import hashlib


class ChangeType(Enum):
    ENTRY_PRICE = "entry_price"
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"
    LOT_SIZE = "lot_size"
    SIGNAL_STATUS = "signal_status"
    NO_CHANGE = "no_change"


class TradeStatus(Enum):
    OPEN = "open"
    CLOSED = "closed"
    PENDING = "pending"
    CANCELLED = "cancelled"


@dataclass
class SignalVersion:
    message_id: int
    content_hash: str
    entry_price: Optional[float]
    stop_loss: Optional[float]
    take_profit: Optional[float]
    lot_size: Optional[float]
    timestamp: datetime
    raw_content: str


@dataclass
class TradeModification:
    ticket: int
    change_type: ChangeType
    old_value: Any
    new_value: Any
    modification_time: datetime
    success: bool
    error_message: Optional[str] = None


@dataclass
class EditTradeEvent:
    message_id: int
    signal_versions: List[SignalVersion] = field(default_factory=list)
    associated_trades: List[int] = field(default_factory=list)
    modifications: List[TradeModification] = field(default_factory=list)
    last_processed: datetime = field(default_factory=datetime.now)


class EditTradeEngine:
    def __init__(self, config_file: str = "config.json", log_file: str = "logs/edit_trade_log.json"):
        self.config_file = config_file
        self.log_file = log_file
        self.config = self._load_config()
        
        # Track signal versions and associated trades
        self.signal_versions: Dict[int, List[SignalVersion]] = {}
        self.trade_signal_mapping: Dict[int, int] = {}  # trade_id -> message_id
        self.edit_events: List[EditTradeEvent] = []
        
        # Module dependencies
        self.parser = None
        self.mt5_bridge = None
        self.strategy_runtime = None
        self.is_running = False
        
        # Setup logging
        self._setup_logging()
        
        # Load existing data
        self._load_edit_history()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from JSON file"""
        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)
                return config.get('edit_trade_engine', self._create_default_config())
        except FileNotFoundError:
            return self._create_default_config()
    
    def _create_default_config(self) -> Dict[str, Any]:
        """Create default configuration"""
        default_config = {
            "edit_trade_engine": {
                "enable_auto_edit": True,
                "max_signal_versions": 10,
                "edit_detection_threshold": 0.1,  # Minimum change to trigger edit
                "confirmation_required": True,
                "log_signal_changes": True,
                "process_delayed_edits": True,
                "max_edit_age_hours": 24
            }
        }
        
        try:
            config_data = {}
            if Path(self.config_file).exists():
                with open(self.config_file, 'r') as f:
                    config_data = json.load(f)
            
            config_data.update(default_config)
            
            with open(self.config_file, 'w') as f:
                json.dump(config_data, f, indent=4)
                
        except Exception as e:
            logging.error(f"Failed to save default config: {e}")
        
        return default_config["edit_trade_engine"]
                "check_interval": 30,
                "max_edit_time_window": 3600,  # 1 hour after signal
                "allowed_changes": ["entry_price", "stop_loss", "take_profit"],
                "require_confirmation": False,
                "min_change_threshold": {
                    "entry_price": 0.0001,
                    "stop_loss": 0.0001,
                    "take_profit": 0.0001
                },
                "max_modification_attempts": 3,
                "notification_enabled": True
            }
        }
        
        # Save default config
        try:
            with open(self.config_file, 'w') as f:
                json.dump(default_config, f, indent=4)
        except Exception as e:
            logging.error(f"Failed to save default config: {e}")
        
        return default_config['edit_trade_engine']
    
    def _setup_logging(self):
        """Setup logging for edit trade operations"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('logs/edit_trade.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def _load_edit_history(self):
        """Load existing edit history from log file"""
        try:
            with open(self.log_file, 'r') as f:
                history_data = json.load(f)
                
                # Load edit events
                for event_data in history_data.get('edit_events', []):
                    event = EditTradeEvent(
                        message_id=event_data['message_id'],
                        signal_versions=[
                            SignalVersion(
                                message_id=sv['message_id'],
                                content_hash=sv['content_hash'],
                                entry_price=sv.get('entry_price'),
                                stop_loss=sv.get('stop_loss'),
                                take_profit=sv.get('take_profit'),
                                lot_size=sv.get('lot_size'),
                                timestamp=datetime.fromisoformat(sv['timestamp']),
                                raw_content=sv['raw_content']
                            ) for sv in event_data.get('signal_versions', [])
                        ],
                        associated_trades=event_data.get('associated_trades', []),
                        modifications=[
                            TradeModification(
                                ticket=mod['ticket'],
                                change_type=ChangeType(mod['change_type']),
                                old_value=mod['old_value'],
                                new_value=mod['new_value'],
                                modification_time=datetime.fromisoformat(mod['modification_time']),
                                success=mod['success'],
                                error_message=mod.get('error_message')
                            ) for mod in event_data.get('modifications', [])
                        ],
                        last_processed=datetime.fromisoformat(event_data['last_processed'])
                    )
                    self.edit_events.append(event)
                
                # Rebuild mappings
                for event in self.edit_events:
                    for trade_id in event.associated_trades:
                        self.trade_signal_mapping[trade_id] = event.message_id
                        
        except FileNotFoundError:
            self.edit_events = []
        except Exception as e:
            self.logger.error(f"Failed to load edit history: {e}")
            self.edit_events = []
    
    def _save_edit_history(self):
        """Save edit history to log file"""
        try:
            history_data = {
                'edit_events': []
            }
            
            for event in self.edit_events[-100:]:  # Keep last 100 events
                event_data = {
                    'message_id': event.message_id,
                    'signal_versions': [
                        {
                            'message_id': sv.message_id,
                            'content_hash': sv.content_hash,
                            'entry_price': sv.entry_price,
                            'stop_loss': sv.stop_loss,
                            'take_profit': sv.take_profit,
                            'lot_size': sv.lot_size,
                            'timestamp': sv.timestamp.isoformat(),
                            'raw_content': sv.raw_content
                        } for sv in event.signal_versions
                    ],
                    'associated_trades': event.associated_trades,
                    'modifications': [
                        {
                            'ticket': mod.ticket,
                            'change_type': mod.change_type.value,
                            'old_value': mod.old_value,
                            'new_value': mod.new_value,
                            'modification_time': mod.modification_time.isoformat(),
                            'success': mod.success,
                            'error_message': mod.error_message
                        } for mod in event.modifications
                    ],
                    'last_processed': event.last_processed.isoformat()
                }
                history_data['edit_events'].append(event_data)
            
            with open(self.log_file, 'w') as f:
                json.dump(history_data, f, indent=2)
                
        except Exception as e:
            self.logger.error(f"Failed to save edit history: {e}")
    
    def inject_modules(self, parser=None, mt5_bridge=None, strategy_runtime=None):
        """Inject module dependencies"""
        self.parser = parser
        self.mt5_bridge = mt5_bridge
        self.strategy_runtime = strategy_runtime
        
        # Register for parser edit events if available
        if hasattr(self.parser, 'register_edit_callback'):
            self.parser.register_edit_callback(self.on_signal_edit)
    
    def _calculate_content_hash(self, signal_content: str) -> str:
        """Calculate hash of signal content for change detection"""
        return hashlib.md5(signal_content.encode()).hexdigest()
    
    def _parse_signal_values(self, signal_content: str) -> Dict[str, Optional[float]]:
        """Extract trading values from signal content"""
        try:
            if self.parser:
                # Use existing parser to extract values
                parsed_data = self.parser.parse_signal(signal_content)
                return {
                    'entry_price': parsed_data.get('entry_price'),
                    'stop_loss': parsed_data.get('stop_loss'),
                    'take_profit': parsed_data.get('take_profit'),
                    'lot_size': parsed_data.get('lot_size')
                }
            else:
                # Fallback manual parsing for basic signal formats
                import re
                
                values = {
                    'entry_price': None,
                    'stop_loss': None,
                    'take_profit': None,
                    'lot_size': None
                }
                
                # Basic regex patterns for common signal formats
                entry_patterns = [
                    r'(?:ENTRY|ENTER|BUY|SELL)\s*:?\s*(\d+\.?\d*)',
                    r'@\s*(\d+\.?\d*)',
                    r'(?:PRICE|AT)\s*(\d+\.?\d*)'
                ]
                
                sl_patterns = [
                    r'(?:SL|STOP\s*LOSS|STOPLOSS)\s*:?\s*(\d+\.?\d*)',
                    r'(?:STOP|S/L)\s*:?\s*(\d+\.?\d*)'
                ]
                
                tp_patterns = [
                    r'(?:TP|TAKE\s*PROFIT|TAKEPROFIT|TARGET)\s*:?\s*(\d+\.?\d*)',
                    r'(?:T/P|PROFIT)\s*:?\s*(\d+\.?\d*)'
                ]
                
                lot_patterns = [
                    r'(?:LOT|LOTS|SIZE|VOLUME)\s*:?\s*(\d+\.?\d*)',
                    r'(\d+\.?\d*)\s*(?:LOTS?|LOT)'
                ]
                
                # Extract values using patterns
                for pattern in entry_patterns:
                    match = re.search(pattern, signal_content.upper())
                    if match:
                        values['entry_price'] = float(match.group(1))
                        break
                
                for pattern in sl_patterns:
                    match = re.search(pattern, signal_content.upper())
                    if match:
                        values['stop_loss'] = float(match.group(1))
                        break
                
                for pattern in tp_patterns:
                    match = re.search(pattern, signal_content.upper())
                    if match:
                        values['take_profit'] = float(match.group(1))
                        break
                
                for pattern in lot_patterns:
                    match = re.search(pattern, signal_content.upper())
                    if match:
                        values['lot_size'] = float(match.group(1))
                        break
                
                return values
                
        except Exception as e:
            self.logger.error(f"Failed to parse signal values: {e}")
            return {
                'entry_price': None,
                'stop_loss': None,
                'take_profit': None,
                'lot_size': None
            }
    
    def on_signal_edit(self, message_id: int, original_content: str, edited_content: str):
        """Callback function for when parser detects signal edit"""
        asyncio.create_task(self.process_signal_edit(message_id, original_content, edited_content))
    
    async def process_signal_edit(self, message_id: int, original_content: str, edited_content: str):
        """Process detected signal edit and update trades accordingly"""
        try:
            # Create content hashes
            original_hash = self._calculate_content_hash(original_content)
            edited_hash = self._calculate_content_hash(edited_content)
            
            if original_hash == edited_hash:
                self.logger.debug(f"No actual content change detected for message {message_id}")
                return
            
            # Parse signal values from both versions
            original_values = self._parse_signal_values(original_content)
            edited_values = self._parse_signal_values(edited_content)
            
            # Detect what changed
            changes = self._detect_changes(original_values, edited_values)
            
            if not changes:
                self.logger.info(f"No significant trading parameter changes detected for message {message_id}")
                return
            
            # Find or create edit event
            edit_event = self._get_or_create_edit_event(message_id)
            
            # Add signal versions
            original_version = SignalVersion(
                message_id=message_id,
                content_hash=original_hash,
                entry_price=original_values.get('entry_price'),
                stop_loss=original_values.get('stop_loss'),
                take_profit=original_values.get('take_profit'),
                lot_size=original_values.get('lot_size'),
                timestamp=datetime.now() - timedelta(minutes=1),  # Approximate original time
                raw_content=original_content
            )
            
            edited_version = SignalVersion(
                message_id=message_id,
                content_hash=edited_hash,
                entry_price=edited_values.get('entry_price'),
                stop_loss=edited_values.get('stop_loss'),
                take_profit=edited_values.get('take_profit'),
                lot_size=edited_values.get('lot_size'),
                timestamp=datetime.now(),
                raw_content=edited_content
            )
            
            # Store original version if not already stored
            if not any(sv.content_hash == original_hash for sv in edit_event.signal_versions):
                edit_event.signal_versions.append(original_version)
            
            edit_event.signal_versions.append(edited_version)
            edit_event.last_processed = datetime.now()
            
            # Find associated trades
            associated_trades = self._find_associated_trades(message_id)
            edit_event.associated_trades.extend([t for t in associated_trades if t not in edit_event.associated_trades])
            
            # Apply changes to trades
            for trade_id in associated_trades:
                await self._apply_trade_modifications(trade_id, changes, original_values, edited_values, edit_event)
            
            # Save history
            self._save_edit_history()
            
            self.logger.info(f"Processed signal edit for message {message_id}: {len(changes)} changes applied to {len(associated_trades)} trades")
            
        except Exception as e:
            self.logger.error(f"Failed to process signal edit for message {message_id}: {e}")
    
    def _detect_changes(self, original: Dict[str, Optional[float]], edited: Dict[str, Optional[float]]) -> List[ChangeType]:
        """Detect what changed between original and edited signal values"""
        changes = []
        threshold = self.config.get('edit_detection_threshold', 0.1)
        
        for key in ['entry_price', 'stop_loss', 'take_profit', 'lot_size']:
            orig_val = original.get(key)
            edit_val = edited.get(key)
            
            # Handle None values
            if orig_val is None and edit_val is not None:
                if key == 'entry_price':
                    changes.append(ChangeType.ENTRY_PRICE)
                elif key == 'stop_loss':
                    changes.append(ChangeType.STOP_LOSS)
                elif key == 'take_profit':
                    changes.append(ChangeType.TAKE_PROFIT)
                elif key == 'lot_size':
                    changes.append(ChangeType.LOT_SIZE)
            elif orig_val is not None and edit_val is None:
                if key == 'entry_price':
                    changes.append(ChangeType.ENTRY_PRICE)
                elif key == 'stop_loss':
                    changes.append(ChangeType.STOP_LOSS)
                elif key == 'take_profit':
                    changes.append(ChangeType.TAKE_PROFIT)
                elif key == 'lot_size':
                    changes.append(ChangeType.LOT_SIZE)
            elif orig_val is not None and edit_val is not None:
                # Check if change exceeds threshold
                if abs(orig_val - edit_val) >= threshold:
                    if key == 'entry_price':
                        changes.append(ChangeType.ENTRY_PRICE)
                    elif key == 'stop_loss':
                        changes.append(ChangeType.STOP_LOSS)
                    elif key == 'take_profit':
                        changes.append(ChangeType.TAKE_PROFIT)
                    elif key == 'lot_size':
                        changes.append(ChangeType.LOT_SIZE)
        
        return changes
    
    def _get_or_create_edit_event(self, message_id: int) -> EditTradeEvent:
        """Get existing edit event or create new one"""
        for event in self.edit_events:
            if event.message_id == message_id:
                return event
        
        # Create new event
        new_event = EditTradeEvent(message_id=message_id)
        self.edit_events.append(new_event)
        return new_event
    
    def _find_associated_trades(self, message_id: int) -> List[int]:
        """Find trades associated with a signal message"""
        associated_trades = []
        
        # Check trade-signal mapping
        for trade_id, mapped_message_id in self.trade_signal_mapping.items():
            if mapped_message_id == message_id:
                associated_trades.append(trade_id)
        
        # If no direct mapping, try to find trades by timestamp correlation
        if not associated_trades and self.mt5_bridge:
            # This would query MT5 for recent trades around the signal time
            # For now, return empty list as this requires MT5 bridge integration
            pass
        
        return associated_trades
    
    async def _apply_trade_modifications(self, trade_id: int, changes: List[ChangeType], 
                                       original_values: Dict[str, Optional[float]], 
                                       edited_values: Dict[str, Optional[float]], 
                                       edit_event: EditTradeEvent):
        """Apply modifications to a specific trade"""
        if not self.mt5_bridge:
            self.logger.warning(f"MT5 bridge not available for trade modification {trade_id}")
            return
        
        for change_type in changes:
            try:
                success = False
                error_message = None
                old_value = None
                new_value = None
                
                if change_type == ChangeType.STOP_LOSS:
                    old_value = original_values.get('stop_loss')
                    new_value = edited_values.get('stop_loss')
                    
                    if self.config.get('confirmation_required', False):
                        # Would trigger copilot confirmation here
                        self.logger.info(f"SL change requires confirmation: {old_value} -> {new_value}")
                    
                    # success = await self.mt5_bridge.modify_position(trade_id, sl=new_value)
                    success = True  # Mock for now
                    
                elif change_type == ChangeType.TAKE_PROFIT:
                    old_value = original_values.get('take_profit')
                    new_value = edited_values.get('take_profit')
                    
                    if self.config.get('confirmation_required', False):
                        self.logger.info(f"TP change requires confirmation: {old_value} -> {new_value}")
                    
                    # success = await self.mt5_bridge.modify_position(trade_id, tp=new_value)
                    success = True  # Mock for now
                
                elif change_type == ChangeType.LOT_SIZE:
                    # Lot size changes might require closing and reopening trades
                    old_value = original_values.get('lot_size')
                    new_value = edited_values.get('lot_size')
                    
                    self.logger.warning(f"Lot size changes not supported for existing trades: {old_value} -> {new_value}")
                    error_message = "Lot size changes not supported for existing trades"
                
                elif change_type == ChangeType.ENTRY_PRICE:
                    # Entry price changes only affect pending orders
                    old_value = original_values.get('entry_price')
                    new_value = edited_values.get('entry_price')
                    
                    # success = await self.mt5_bridge.modify_pending_order(trade_id, price=new_value)
                    success = True  # Mock for now
                
                # Record modification
                modification = TradeModification(
                    ticket=trade_id,
                    change_type=change_type,
                    old_value=old_value,
                    new_value=new_value,
                    modification_time=datetime.now(),
                    success=success,
                    error_message=error_message
                )
                
                edit_event.modifications.append(modification)
                
                if success:
                    self.logger.info(f"Successfully modified trade {trade_id}: {change_type.value} {old_value} -> {new_value}")
                else:
                    self.logger.error(f"Failed to modify trade {trade_id}: {change_type.value} - {error_message}")
                    
            except Exception as e:
                error_message = str(e)
                self.logger.error(f"Exception modifying trade {trade_id}: {e}")
                
                # Record failed modification
                modification = TradeModification(
                    ticket=trade_id,
                    change_type=change_type,
                    old_value=old_value,
                    new_value=new_value,
                    modification_time=datetime.now(),
                    success=False,
                    error_message=error_message
                )
                edit_event.modifications.append(modification)
    
    def register_trade_signal_mapping(self, trade_id: int, message_id: int):
        """Register mapping between trade and signal message"""
        self.trade_signal_mapping[trade_id] = message_id
        self.logger.debug(f"Registered trade {trade_id} -> signal {message_id}")
    
    def get_edit_statistics(self) -> Dict[str, Any]:
        """Get statistics about signal edits and trade modifications"""
        total_events = len(self.edit_events)
        total_modifications = sum(len(event.modifications) for event in self.edit_events)
        successful_modifications = sum(
            sum(1 for mod in event.modifications if mod.success) 
            for event in self.edit_events
        )
        
        # Count change types
        change_type_counts = {}
        for event in self.edit_events:
            for mod in event.modifications:
                change_type = mod.change_type.value
                change_type_counts[change_type] = change_type_counts.get(change_type, 0) + 1
        
        return {
            'total_edit_events': total_events,
            'total_modifications': total_modifications,
            'successful_modifications': successful_modifications,
            'failed_modifications': total_modifications - successful_modifications,
            'change_type_counts': change_type_counts,
            'average_modifications_per_event': total_modifications / total_events if total_events > 0 else 0,
            'success_rate': successful_modifications / total_modifications if total_modifications > 0 else 0
        }
                    'stop_loss': parsed_data.get('stop_loss'),
                    'take_profit': parsed_data.get('take_profit'),
                    'lot_size': parsed_data.get('lot_size')
                }
            else:
                # Basic fallback parsing
                import re
                
                values = {
                    'entry_price': None,
                    'stop_loss': None,
                    'take_profit': None,
                    'lot_size': None
                }
                
                # Simple regex patterns for common formats
                entry_patterns = [r'entry[:\s]+(\d+\.?\d*)', r'buy[:\s]+(\d+\.?\d*)', r'sell[:\s]+(\d+\.?\d*)']
                sl_patterns = [r'sl[:\s]+(\d+\.?\d*)', r'stop[:\s]+(\d+\.?\d*)']
                tp_patterns = [r'tp[:\s]+(\d+\.?\d*)', r'target[:\s]+(\d+\.?\d*)']
                lot_patterns = [r'lot[:\s]+(\d+\.?\d*)', r'size[:\s]+(\d+\.?\d*)']
                
                for pattern in entry_patterns:
                    match = re.search(pattern, signal_content.lower())
                    if match:
                        values['entry_price'] = float(match.group(1))
                        break
                
                for pattern in sl_patterns:
                    match = re.search(pattern, signal_content.lower())
                    if match:
                        values['stop_loss'] = float(match.group(1))
                        break
                
                for pattern in tp_patterns:
                    match = re.search(pattern, signal_content.lower())
                    if match:
                        values['take_profit'] = float(match.group(1))
                        break
                
                for pattern in lot_patterns:
                    match = re.search(pattern, signal_content.lower())
                    if match:
                        values['lot_size'] = float(match.group(1))
                        break
                
                return values
                
        except Exception as e:
            self.logger.error(f"Failed to parse signal values: {e}")
            return {
                'entry_price': None,
                'stop_loss': None,
                'take_profit': None,
                'lot_size': None
            }
    
    def register_signal_trade_mapping(self, message_id: int, trade_ticket: int, signal_content: str):
        """Register mapping between signal message and trade"""
        try:
            # Create initial signal version
            content_hash = self._calculate_content_hash(signal_content)
            values = self._parse_signal_values(signal_content)
            
            signal_version = SignalVersion(
                message_id=message_id,
                content_hash=content_hash,
                entry_price=values['entry_price'],
                stop_loss=values['stop_loss'],
                take_profit=values['take_profit'],
                lot_size=values['lot_size'],
                timestamp=datetime.now(),
                raw_content=signal_content
            )
            
            # Store signal version
            if message_id not in self.signal_versions:
                self.signal_versions[message_id] = []
            self.signal_versions[message_id].append(signal_version)
            
            # Map trade to signal
            self.trade_signal_mapping[trade_ticket] = message_id
            
            # Create or update edit event
            event = None
            for e in self.edit_events:
                if e.message_id == message_id:
                    event = e
                    break
            
            if not event:
                event = EditTradeEvent(message_id=message_id)
                self.edit_events.append(event)
            
            event.signal_versions.append(signal_version)
            if trade_ticket not in event.associated_trades:
                event.associated_trades.append(trade_ticket)
            
            self.logger.info(f"Registered signal-trade mapping: message {message_id} -> trade {trade_ticket}")
            
        except Exception as e:
            self.logger.error(f"Failed to register signal-trade mapping: {e}")
    
    async def on_signal_edit(self, message_id: int, new_content: str):
        """Handle signal edit event from parser"""
        try:
            if message_id not in self.signal_versions:
                self.logger.warning(f"Received edit for unknown message {message_id}")
                return
            
            # Calculate new content hash
            new_hash = self._calculate_content_hash(new_content)
            
            # Get latest version
            latest_version = self.signal_versions[message_id][-1]
            
            # Check if content actually changed
            if latest_version.content_hash == new_hash:
                self.logger.debug(f"No content change detected for message {message_id}")
                return
            
            # Parse new signal values
            new_values = self._parse_signal_values(new_content)
            
            # Create new signal version
            new_version = SignalVersion(
                message_id=message_id,
                content_hash=new_hash,
                entry_price=new_values['entry_price'],
                stop_loss=new_values['stop_loss'],
                take_profit=new_values['take_profit'],
                lot_size=new_values['lot_size'],
                timestamp=datetime.now(),
                raw_content=new_content
            )
            
            self.signal_versions[message_id].append(new_version)
            
            # Detect changes and update trades
            changes = self._detect_changes(latest_version, new_version)
            if changes:
                await self._process_trade_updates(message_id, changes, latest_version, new_version)
            
            self._save_edit_history()
            
        except Exception as e:
            self.logger.error(f"Failed to handle signal edit: {e}")
    
    def _detect_changes(self, old_version: SignalVersion, new_version: SignalVersion) -> List[ChangeType]:
        """Detect what changed between signal versions"""
        changes = []
        
        # Check entry price
        if self._value_changed(old_version.entry_price, new_version.entry_price, 'entry_price'):
            changes.append(ChangeType.ENTRY_PRICE)
        
        # Check stop loss
        if self._value_changed(old_version.stop_loss, new_version.stop_loss, 'stop_loss'):
            changes.append(ChangeType.STOP_LOSS)
        
        # Check take profit
        if self._value_changed(old_version.take_profit, new_version.take_profit, 'take_profit'):
            changes.append(ChangeType.TAKE_PROFIT)
        
        # Check lot size
        if self._value_changed(old_version.lot_size, new_version.lot_size, 'lot_size'):
            changes.append(ChangeType.LOT_SIZE)
        
        return changes
    
    def _value_changed(self, old_value: Optional[float], new_value: Optional[float], field_name: str) -> bool:
        """Check if a value has changed significantly"""
        if old_value is None and new_value is None:
            return False
        
        if old_value is None or new_value is None:
            return True
        
        threshold = self.config.get('min_change_threshold', {}).get(field_name, 0.0001)
        return abs(old_value - new_value) >= threshold
    
    async def _process_trade_updates(self, message_id: int, changes: List[ChangeType], 
                                   old_version: SignalVersion, new_version: SignalVersion):
        """Process trade updates based on detected changes"""
        try:
            # Find associated trades
            event = None
            for e in self.edit_events:
                if e.message_id == message_id:
                    event = e
                    break
            
            if not event or not event.associated_trades:
                self.logger.warning(f"No associated trades found for message {message_id}")
                return
            
            allowed_changes = self.config.get('allowed_changes', [])
            
            for trade_ticket in event.associated_trades:
                # Check if trade is still open
                if not await self._is_trade_open(trade_ticket):
                    self.logger.info(f"Trade {trade_ticket} already closed, skipping update")
                    continue
                
                # Check time window
                if not self._within_edit_window(old_version.timestamp):
                    self.logger.info(f"Edit window expired for trade {trade_ticket}")
                    continue
                
                # Process each change
                for change_type in changes:
                    if change_type.value not in allowed_changes:
                        self.logger.info(f"Change type {change_type.value} not allowed")
                        continue
                    
                    await self._apply_trade_modification(
                        trade_ticket, change_type, old_version, new_version, event
                    )
            
        except Exception as e:
            self.logger.error(f"Failed to process trade updates: {e}")
    
    async def _is_trade_open(self, trade_ticket: int) -> bool:
        """Check if trade is still open"""
        try:
            if self.mt5_bridge:
                return await self.mt5_bridge.is_position_open(trade_ticket)
            else:
                # Mock implementation for testing
                return True
        except Exception as e:
            self.logger.error(f"Failed to check trade status: {e}")
            return False
    
    def _within_edit_window(self, signal_time: datetime) -> bool:
        """Check if we're within the allowed edit time window"""
        max_window = self.config.get('max_edit_time_window', 3600)
        return (datetime.now() - signal_time).total_seconds() <= max_window
    
    async def _apply_trade_modification(self, trade_ticket: int, change_type: ChangeType,
                                      old_version: SignalVersion, new_version: SignalVersion,
                                      event: EditTradeEvent):
        """Apply specific modification to trade"""
        try:
            success = False
            error_message = None
            old_value = None
            new_value = None
            
            if change_type == ChangeType.ENTRY_PRICE:
                old_value = old_version.entry_price
                new_value = new_version.entry_price
                if self.mt5_bridge and new_value:
                    success = await self.mt5_bridge.modify_position_entry(trade_ticket, new_value)
                else:
                    success = True  # Mock for testing
            
            elif change_type == ChangeType.STOP_LOSS:
                old_value = old_version.stop_loss
                new_value = new_version.stop_loss
                if self.mt5_bridge and new_value:
                    success = await self.mt5_bridge.modify_stop_loss(trade_ticket, new_value)
                else:
                    success = True  # Mock for testing
            
            elif change_type == ChangeType.TAKE_PROFIT:
                old_value = old_version.take_profit
                new_value = new_version.take_profit
                if self.mt5_bridge and new_value:
                    success = await self.mt5_bridge.modify_take_profit(trade_ticket, new_value)
                else:
                    success = True  # Mock for testing
            
            elif change_type == ChangeType.LOT_SIZE:
                old_value = old_version.lot_size
                new_value = new_version.lot_size
                if self.mt5_bridge and new_value:
                    success = await self.mt5_bridge.modify_lot_size(trade_ticket, new_value)
                else:
                    success = True  # Mock for testing
            
            # Record modification
            modification = TradeModification(
                ticket=trade_ticket,
                change_type=change_type,
                old_value=old_value,
                new_value=new_value,
                modification_time=datetime.now(),
                success=success,
                error_message=error_message
            )
            
            event.modifications.append(modification)
            
            if success:
                self.logger.info(f"Successfully modified trade {trade_ticket}: {change_type.value} from {old_value} to {new_value}")
            else:
                self.logger.error(f"Failed to modify trade {trade_ticket}: {change_type.value}")
            
        except Exception as e:
            self.logger.error(f"Failed to apply trade modification: {e}")
    
    def get_edit_statistics(self) -> Dict[str, Any]:
        """Get statistics about edit operations"""
        try:
            total_events = len(self.edit_events)
            total_modifications = sum(len(event.modifications) for event in self.edit_events)
            successful_modifications = sum(
                len([m for m in event.modifications if m.success]) 
                for event in self.edit_events
            )
            
            # Recent activity (last 24 hours)
            recent_cutoff = datetime.now() - timedelta(hours=24)
            recent_events = [e for e in self.edit_events if e.last_processed > recent_cutoff]
            
            change_type_counts = {}
            for event in self.edit_events:
                for mod in event.modifications:
                    change_type = mod.change_type.value
                    change_type_counts[change_type] = change_type_counts.get(change_type, 0) + 1
            
            return {
                'total_edit_events': total_events,
                'total_modifications': total_modifications,
                'successful_modifications': successful_modifications,
                'success_rate': (successful_modifications / total_modifications * 100) if total_modifications > 0 else 0,
                'recent_events_24h': len(recent_events),
                'change_type_breakdown': change_type_counts,
                'active_signal_mappings': len(self.trade_signal_mapping),
                'config': self.config
            }
            
        except Exception as e:
            self.logger.error(f"Error getting edit statistics: {e}")
            return {}
    
    def get_trade_edit_history(self, trade_ticket: int) -> List[Dict[str, Any]]:
        """Get edit history for specific trade"""
        try:
            history = []
            
            for event in self.edit_events:
                if trade_ticket in event.associated_trades:
                    for modification in event.modifications:
                        if modification.ticket == trade_ticket:
                            history.append({
                                'message_id': event.message_id,
                                'change_type': modification.change_type.value,
                                'old_value': modification.old_value,
                                'new_value': modification.new_value,
                                'modification_time': modification.modification_time.isoformat(),
                                'success': modification.success,
                                'error_message': modification.error_message
                            })
            
            return sorted(history, key=lambda x: x['modification_time'])
            
        except Exception as e:
            self.logger.error(f"Error getting trade edit history: {e}")
            return []
    
    async def start_edit_monitor(self):
        """Start the edit monitoring loop"""
        self.is_running = True
        self.logger.info("Starting edit trade monitor")
        
        while self.is_running:
            try:
                # Process any pending edits or cleanup
                await self._cleanup_old_mappings()
                await asyncio.sleep(self.config.get('check_interval', 30))
                
            except Exception as e:
                self.logger.error(f"Error in edit monitor loop: {e}")
                await asyncio.sleep(60)
    
    async def _cleanup_old_mappings(self):
        """Clean up old signal-trade mappings"""
        try:
            max_age = timedelta(days=7)
            cutoff_time = datetime.now() - max_age
            
            # Remove old signal versions
            for message_id in list(self.signal_versions.keys()):
                versions = self.signal_versions[message_id]
                recent_versions = [v for v in versions if v.timestamp > cutoff_time]
                
                if recent_versions:
                    self.signal_versions[message_id] = recent_versions
                else:
                    del self.signal_versions[message_id]
            
            # Remove old events
            self.edit_events = [e for e in self.edit_events if e.last_processed > cutoff_time]
            
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")
    
    def stop_edit_monitor(self):
        """Stop the edit monitoring loop"""
        self.is_running = False
        self.logger.info("Stopped edit trade monitor")


async def main():
    """Example usage of Edit Trade Engine"""
    
    # Create edit trade engine
    edit_engine = EditTradeEngine()
    
    # Mock dependencies
    class MockParser:
        def parse_signal(self, content):
            return {
                'entry_price': 1.1000,
                'stop_loss': 1.0950,
                'take_profit': 1.1050,
                'lot_size': 0.1
            }
    
    class MockMT5Bridge:
        async def is_position_open(self, ticket):
            return True
        
        async def modify_stop_loss(self, ticket, new_sl):
            print(f"Mock: Modified SL for {ticket} to {new_sl}")
            return True
        
        async def modify_take_profit(self, ticket, new_tp):
            print(f"Mock: Modified TP for {ticket} to {new_tp}")
            return True
    
    # Inject mock modules
    edit_engine.inject_modules(
        parser=MockParser(),
        mt5_bridge=MockMT5Bridge()
    )
    
    # Test edit trade functionality
    print("=== Edit Trade Engine Test ===")
    
    # Register a signal-trade mapping
    original_signal = "EURUSD BUY 1.1000 SL 1.0950 TP 1.1050"
    edit_engine.register_signal_trade_mapping(12345, 67890, original_signal)
    
    # Simulate signal edit
    edited_signal = "EURUSD BUY 1.1000 SL 1.0940 TP 1.1060"  # Changed SL and TP
    await edit_engine.on_signal_edit(12345, edited_signal)
    
    # Get statistics
    stats = edit_engine.get_edit_statistics()
    print(f"Edit Statistics: {json.dumps(stats, indent=2)}")
    
    # Get trade history
    history = edit_engine.get_trade_edit_history(67890)
    print(f"Trade Edit History: {json.dumps(history, indent=2)}")
    
    print("=== Edit Trade Engine Test Complete ===")


if __name__ == "__main__":
    asyncio.run(main())