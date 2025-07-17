#!/usr/bin/env python3
"""
Telegram Channel Monitoring for SignalOS Phase 1
Multi-account support with channel filtering and real-time signal processing
"""

import asyncio
import json
import logging
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, asdict

try:
    from telethon import TelegramClient, events
    from telethon.tl.types import Channel, User, Message
    TELETHON_AVAILABLE = True
except ImportError:
    TELETHON_AVAILABLE = False
    logging.warning("Telethon not available - Telegram monitoring disabled")

from ai_parser.parser_engine import parse_signal_safe
from parser.ocr_engine import OCREngine
from parser.multilingual_parser import MultilingualParser

@dataclass
class ChannelConfig:
    """Configuration for a monitored channel"""
    channel_id: str
    channel_title: str
    enabled: bool = True
    pair_filter: List[str] = None
    time_filter: Dict[str, Any] = None
    parse_images: bool = True
    language: str = "auto"
    confidence_threshold: float = 0.7

@dataclass
class SignalMessage:
    """Processed signal message"""
    message_id: int
    channel_id: str
    channel_title: str
    raw_text: str
    processed_text: Optional[str]
    parsed_signal: Optional[Dict[str, Any]]
    timestamp: datetime
    has_image: bool = False
    language_detected: Optional[str] = None
    confidence: float = 0.0
    processing_method: str = "text"

class TelegramMonitor:
    """Advanced Telegram channel monitoring with signal processing"""
    
    def __init__(self, config_file: str = "config/telegram_monitor.json"):
        self.config_file = config_file
        self.config = self._load_config()
        self._setup_logging()
        
        # Telegram clients
        self.clients: Dict[str, TelegramClient] = {}
        self.active_sessions: Set[str] = set()
        
        # Channel monitoring
        self.monitored_channels: Dict[str, ChannelConfig] = {}
        self.channel_handlers: Dict[str, Any] = {}
        
        # Signal processing
        self.ocr_engine = OCREngine() if self.config.get('ocr_enabled', True) else None
        self.multilingual_parser = MultilingualParser() if self.config.get('multilingual_enabled', True) else None
        
        # Statistics
        self.stats = {
            "total_messages": 0,
            "signals_detected": 0,
            "signals_parsed": 0,
            "images_processed": 0,
            "errors": 0,
            "start_time": datetime.now()
        }
        
        # Message processing queue
        self.message_queue = asyncio.Queue()
        self.processing_task: Optional[asyncio.Task] = None
        
        self.logger.info("Telegram Monitor initialized")
    
    def _load_config(self) -> Dict[str, Any]:
        """Load monitoring configuration"""
        try:
            if Path(self.config_file).exists():
                with open(self.config_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logging.warning(f"Failed to load Telegram config: {e}")
        
        return {
            "enabled": True,
            "api_id": None,
            "api_hash": None,
            "ocr_enabled": True,
            "multilingual_enabled": True,
            "auto_reconnect": True,
            "reconnect_delay": 30,
            "max_message_age": 3600,  # 1 hour
            "channels": [],
            "global_filters": {
                "pairs": ["EURUSD", "GBPUSD", "XAUUSD", "USDJPY"],
                "time_windows": {
                    "london_session": {"start": "08:00", "end": "17:00"},
                    "ny_session": {"start": "13:00", "end": "22:00"}
                },
                "keywords": ["buy", "sell", "entry", "tp", "sl", "target", "stop"]
            }
        }
    
    def _setup_logging(self):
        """Setup logging for Telegram monitoring"""
        self.logger = logging.getLogger(__name__)
        
        # Create telegram-specific log file
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        handler = logging.FileHandler(log_dir / "telegram_monitor.log")
        handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        self.logger.addHandler(handler)
    
    async def start(self):
        """Start Telegram monitoring"""
        if not TELETHON_AVAILABLE:
            self.logger.error("Telethon not available - cannot start monitoring")
            return False
        
        if not self.config.get('enabled', True):
            self.logger.info("Telegram monitoring disabled in config")
            return False
        
        self.logger.info("Starting Telegram monitoring...")
        
        try:
            # Initialize Telegram clients
            await self._initialize_clients()
            
            # Setup channel monitoring
            await self._setup_channel_monitoring()
            
            # Start message processing
            self.processing_task = asyncio.create_task(self._process_message_queue())
            
            self.logger.info("Telegram monitoring started successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start Telegram monitoring: {e}")
            return False
    
    async def stop(self):
        """Stop Telegram monitoring"""
        self.logger.info("Stopping Telegram monitoring...")
        
        try:
            # Stop message processing
            if self.processing_task:
                self.processing_task.cancel()
                try:
                    await self.processing_task
                except asyncio.CancelledError:
                    pass
            
            # Disconnect clients
            for client in self.clients.values():
                if client.is_connected():
                    await client.disconnect()
            
            self.clients.clear()
            self.active_sessions.clear()
            
            self.logger.info("Telegram monitoring stopped")
            
        except Exception as e:
            self.logger.error(f"Error stopping Telegram monitoring: {e}")
    
    async def _initialize_clients(self):
        """Initialize Telegram clients"""
        api_id = self.config.get('api_id')
        api_hash = self.config.get('api_hash')
        
        if not api_id or not api_hash:
            raise ValueError("Telegram API credentials not configured")
        
        # For now, create a single client
        # In production, this would support multiple accounts
        session_name = "signalos_session"
        
        client = TelegramClient(
            f"sessions/{session_name}",
            api_id,
            api_hash
        )
        
        await client.start()
        
        if client.is_connected():
            self.clients[session_name] = client
            self.active_sessions.add(session_name)
            self.logger.info(f"Telegram client '{session_name}' connected")
        else:
            raise RuntimeError(f"Failed to connect Telegram client '{session_name}'")
    
    async def _setup_channel_monitoring(self):
        """Setup monitoring for configured channels"""
        for channel_config in self.config.get('channels', []):
            await self._add_channel_monitor(channel_config)
    
    async def _add_channel_monitor(self, channel_config: Dict[str, Any]):
        """Add monitoring for a specific channel"""
        try:
            config = ChannelConfig(**channel_config)
            self.monitored_channels[config.channel_id] = config
            
            # Setup event handler for each client
            for session_name, client in self.clients.items():
                @client.on(events.NewMessage(chats=config.channel_id))
                async def handler(event, config=config):
                    await self._handle_new_message(event, config)
                
                self.channel_handlers[f"{session_name}_{config.channel_id}"] = handler
            
            self.logger.info(f"Added monitoring for channel: {config.channel_title}")
            
        except Exception as e:
            self.logger.error(f"Failed to add channel monitor: {e}")
    
    async def _handle_new_message(self, event, channel_config: ChannelConfig):
        """Handle new message from monitored channel"""
        try:
            if not channel_config.enabled:
                return
            
            message = event.message
            
            # Basic message filtering
            if not self._should_process_message(message, channel_config):
                return
            
            # Create signal message object
            signal_msg = SignalMessage(
                message_id=message.id,
                channel_id=str(message.peer_id.channel_id),
                channel_title=channel_config.channel_title,
                raw_text=message.text or "",
                processed_text=None,
                parsed_signal=None,
                timestamp=message.date,
                has_image=bool(message.photo or message.document)
            )
            
            # Add to processing queue
            await self.message_queue.put((signal_msg, channel_config))
            
            self.stats["total_messages"] += 1
            
        except Exception as e:
            self.logger.error(f"Error handling message: {e}")
            self.stats["errors"] += 1
    
    def _should_process_message(self, message: Message, config: ChannelConfig) -> bool:
        """Check if message should be processed"""
        # Skip old messages
        if message.date < datetime.now() - timedelta(seconds=self.config.get('max_message_age', 3600)):
            return False
        
        # Check for trading-related keywords
        text = (message.text or "").lower()
        keywords = self.config.get('global_filters', {}).get('keywords', [])
        
        if keywords and not any(keyword in text for keyword in keywords):
            return False
        
        # Check pair filter
        if config.pair_filter:
            pairs_mentioned = any(pair.lower() in text for pair in config.pair_filter)
            if not pairs_mentioned:
                return False
        
        # Time filter check (simplified)
        # In production, this would check actual trading session times
        
        return True
    
    async def _process_message_queue(self):
        """Process messages from the queue"""
        self.logger.info("Started message processing queue")
        
        try:
            while True:
                # Get message from queue
                signal_msg, channel_config = await self.message_queue.get()
                
                try:
                    # Process the signal message
                    await self._process_signal_message(signal_msg, channel_config)
                    
                except Exception as e:
                    self.logger.error(f"Error processing signal message: {e}")
                    self.stats["errors"] += 1
                finally:
                    self.message_queue.task_done()
                    
        except asyncio.CancelledError:
            self.logger.info("Message processing queue cancelled")
        except Exception as e:
            self.logger.error(f"Message processing queue error: {e}")
    
    async def _process_signal_message(self, signal_msg: SignalMessage, config: ChannelConfig):
        """Process a signal message completely"""
        try:
            # Step 1: Text processing
            if signal_msg.raw_text:
                processed_text = await self._process_text(signal_msg.raw_text, config)
                signal_msg.processed_text = processed_text
                signal_msg.processing_method = "text"
            
            # Step 2: Image processing (if available and enabled)
            if signal_msg.has_image and config.parse_images and self.ocr_engine:
                # This would download and process the image
                # For now, it's a placeholder
                ocr_text = await self._process_image_ocr(signal_msg)
                if ocr_text:
                    signal_msg.processed_text = f"{signal_msg.processed_text or ''}\n{ocr_text}".strip()
                    signal_msg.processing_method = "text+ocr"
                    self.stats["images_processed"] += 1
            
            # Step 3: Language detection and processing
            if self.multilingual_parser and signal_msg.processed_text:
                lang_result = await self.multilingual_parser.detect_and_process(
                    signal_msg.processed_text
                )
                signal_msg.language_detected = lang_result.get('language')
                if lang_result.get('processed_text'):
                    signal_msg.processed_text = lang_result['processed_text']
            
            # Step 4: Signal parsing
            if signal_msg.processed_text:
                parsed_signal = parse_signal_safe(signal_msg.processed_text)
                if parsed_signal:
                    signal_msg.parsed_signal = parsed_signal
                    signal_msg.confidence = parsed_signal.get('confidence', 0.0)
                    
                    # Check confidence threshold
                    if signal_msg.confidence >= config.confidence_threshold:
                        self.stats["signals_detected"] += 1
                        self.stats["signals_parsed"] += 1
                        
                        # Log successful signal
                        await self._log_processed_signal(signal_msg)
                        
                        # Notify signal processors (Phase 1 integration point)
                        await self._notify_signal_processors(signal_msg)
                    else:
                        self.logger.debug(f"Signal confidence too low: {signal_msg.confidence}")
                else:
                    self.logger.debug("No signal detected in message")
            
        except Exception as e:
            self.logger.error(f"Error processing signal message: {e}")
            self.stats["errors"] += 1
    
    async def _process_text(self, text: str, config: ChannelConfig) -> str:
        """Process text message"""
        # Basic text cleaning and normalization
        processed = text.strip()
        
        # Remove excessive whitespace
        processed = re.sub(r'\s+', ' ', processed)
        
        # Remove excessive punctuation
        processed = re.sub(r'[!]{2,}', '!', processed)
        processed = re.sub(r'[?]{2,}', '?', processed)
        
        return processed
    
    async def _process_image_ocr(self, signal_msg: SignalMessage) -> Optional[str]:
        """Process image using OCR"""
        if not self.ocr_engine:
            return None
        
        try:
            # This would download the image and process it
            # For now, return placeholder
            self.logger.info(f"Processing image from message {signal_msg.message_id}")
            return None  # Placeholder for actual OCR processing
            
        except Exception as e:
            self.logger.error(f"OCR processing failed: {e}")
            return None
    
    async def _log_processed_signal(self, signal_msg: SignalMessage):
        """Log successfully processed signal"""
        try:
            log_file = Path("logs/processed_signals.jsonl")
            
            with open(log_file, 'a', encoding='utf-8') as f:
                log_entry = {
                    "timestamp": datetime.now().isoformat(),
                    "message_id": signal_msg.message_id,
                    "channel": signal_msg.channel_title,
                    "raw_text": signal_msg.raw_text,
                    "processed_text": signal_msg.processed_text,
                    "parsed_signal": signal_msg.parsed_signal,
                    "confidence": signal_msg.confidence,
                    "processing_method": signal_msg.processing_method,
                    "language": signal_msg.language_detected
                }
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
                
        except Exception as e:
            self.logger.error(f"Failed to log processed signal: {e}")
    
    async def _notify_signal_processors(self, signal_msg: SignalMessage):
        """Notify other components about new signal"""
        # This is the integration point with the rest of Phase 1
        # In a complete implementation, this would trigger:
        # - Trade execution
        # - Strategy evaluation
        # - Risk management checks
        
        self.logger.info(f"New signal processed: {signal_msg.parsed_signal.get('pair')} {signal_msg.parsed_signal.get('direction')}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get monitoring status"""
        return {
            "enabled": self.config.get('enabled', False),
            "connected_clients": len(self.active_sessions),
            "monitored_channels": len(self.monitored_channels),
            "statistics": self.stats,
            "uptime": (datetime.now() - self.stats["start_time"]).total_seconds()
        }
    
    def get_channel_list(self) -> List[Dict[str, Any]]:
        """Get list of monitored channels"""
        return [
            {
                "channel_id": config.channel_id,
                "title": config.channel_title,
                "enabled": config.enabled,
                "pairs": config.pair_filter or [],
                "confidence_threshold": config.confidence_threshold
            }
            for config in self.monitored_channels.values()
        ]