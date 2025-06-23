"""
Margin Level Checker Engine for SignalOS
Monitors account margin levels and prevents new trades when margin falls below safe thresholds
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

class MarginStatus(Enum):
    SAFE = "safe"
    WARNING = "warning"
    CRITICAL = "critical"
    MARGIN_CALL = "margin_call"

class TradeBlockReason(Enum):
    ALLOWED = "allowed"
    INSUFFICIENT_MARGIN = "insufficient_margin"
    CRITICAL_LEVEL = "critical_level"
    MARGIN_CALL_RISK = "margin_call_risk"
    SYMBOL_BLOCKED = "symbol_blocked"
    EMERGENCY_BLOCK = "emergency_block"

@dataclass
class MarginThresholds:
    safe_level: float = 300.0  # % - Safe trading level
    warning_level: float = 200.0  # % - Warning threshold
    critical_level: float = 150.0  # % - Critical, block new trades
    margin_call_level: float = 100.0  # % - Margin call level
    emergency_close_level: float = 110.0  # % - Emergency close trades

@dataclass
class SymbolMarginRequirement:
    symbol: str
    margin_required: float  # Required margin per lot
    risk_multiplier: float = 1.0  # Risk multiplier for this symbol
    max_exposure: float = 50.0  # Max % of account for this symbol

@dataclass
class AccountInfo:
    balance: float
    equity: float
    margin: float
    free_margin: float
    margin_level: float
    credit: float
    profit: float
    timestamp: datetime

    def to_dict(self) -> Dict[str, Any]:
        return {
            "balance": self.balance,
            "equity": self.equity,
            "margin": self.margin,
            "free_margin": self.free_margin,
            "margin_level": self.margin_level,
            "credit": self.credit,
            "profit": self.profit,
            "timestamp": self.timestamp.isoformat()
        }

@dataclass
class MarginCheckResult:
    allowed: bool
    reason: TradeBlockReason
    current_margin_level: float
    required_margin: float
    available_margin: float
    risk_assessment: str
    margin_status: MarginStatus
    next_check_time: Optional[datetime] = None

@dataclass
class MarginAlert:
    alert_id: str
    alert_type: MarginStatus
    margin_level: float
    threshold: float
    message: str
    timestamp: datetime
    acknowledged: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "alert_id": self.alert_id,
            "alert_type": self.alert_type.value,
            "margin_level": self.margin_level,
            "threshold": self.threshold,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
            "acknowledged": self.acknowledged
        }

class MarginLevelChecker:
    def __init__(self, config_path: str = "config.json", log_path: str = "logs/margin_level_checker.log"):
        self.config_path = config_path
        self.log_path = log_path
        self.config = self._load_config()
        self.logger = self._setup_logger()
        
        # Margin settings
        self.thresholds = self._load_margin_thresholds()
        self.symbol_requirements: Dict[str, SymbolMarginRequirement] = {}
        
        # Account monitoring
        self.current_account_info: Optional[AccountInfo] = None
        self.account_history: List[AccountInfo] = []
        self.margin_alerts: List[MarginAlert] = []
        
        # Emergency controls
        self.emergency_block_active = False
        self.emergency_block_reason = ""
        self.emergency_block_expires: Optional[datetime] = None
        
        # Module dependencies
        self.mt5_bridge = None
        
        # Background monitoring
        self.monitoring_task = None
        self.is_monitoring = False
        
        # Load existing data
        self._load_margin_data()
        self._load_symbol_requirements()
        
    def _load_config(self) -> Dict[str, Any]:
        """Load margin checker configuration"""
        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)
                
            if "margin_level_checker" not in config:
                config["margin_level_checker"] = {
                    "enabled": True,
                    "monitoring_interval": 30.0,  # Check every 30 seconds
                    "account_update_interval": 5.0,  # Update account info every 5 seconds
                    "alert_cooldown_minutes": 15,  # Cooldown between similar alerts
                    "emergency_close_enabled": True,
                    "margin_thresholds": {
                        "safe_level": 300.0,
                        "warning_level": 200.0,
                        "critical_level": 150.0,
                        "margin_call_level": 100.0,
                        "emergency_close_level": 110.0
                    },
                    "symbol_groups": {
                        "major_pairs": {
                            "symbols": ["EURUSD", "GBPUSD", "AUDUSD", "NZDUSD", "USDCAD", "USDCHF"],
                            "risk_multiplier": 1.0,
                            "max_exposure": 50.0
                        },
                        "minor_pairs": {
                            "symbols": ["EURGBP", "EURAUD", "EURCHF", "GBPAUD", "GBPCHF"],
                            "risk_multiplier": 1.2,
                            "max_exposure": 30.0
                        },
                        "exotic_pairs": {
                            "symbols": ["USDZAR", "USDTRY", "USDRUB"],
                            "risk_multiplier": 2.0,
                            "max_exposure": 20.0
                        },
                        "commodities": {
                            "symbols": ["XAUUSD", "XAGUSD", "USOIL", "UKOIL"],
                            "risk_multiplier": 1.5,
                            "max_exposure": 25.0
                        },
                        "crypto": {
                            "symbols": ["BTCUSD", "ETHUSD"],
                            "risk_multiplier": 3.0,
                            "max_exposure": 15.0
                        }
                    }
                }
                self._save_config(config)
                
            return config.get("margin_level_checker", {})
            
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
            "account_update_interval": 5.0,
            "alert_cooldown_minutes": 15,
            "emergency_close_enabled": True,
            "margin_thresholds": {
                "safe_level": 300.0,
                "warning_level": 200.0,
                "critical_level": 150.0,
                "margin_call_level": 100.0,
                "emergency_close_level": 110.0
            },
            "symbol_groups": {}
        }
        
    def _save_config(self, full_config: Dict[str, Any]):
        """Save updated configuration"""
        try:
            with open(self.config_path, 'w') as f:
                json.dump(full_config, f, indent=4)
        except Exception as e:
            self.logger.error(f"Failed to save config: {e}")
            
    def _setup_logger(self) -> logging.Logger:
        """Setup dedicated logger for margin checker"""
        logger = logging.getLogger("margin_level_checker")
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
        
    def _load_margin_thresholds(self) -> MarginThresholds:
        """Load margin thresholds from configuration"""
        thresholds_config = self.config.get("margin_thresholds", {})
        
        return MarginThresholds(
            safe_level=thresholds_config.get("safe_level", 300.0),
            warning_level=thresholds_config.get("warning_level", 200.0),
            critical_level=thresholds_config.get("critical_level", 150.0),
            margin_call_level=thresholds_config.get("margin_call_level", 100.0),
            emergency_close_level=thresholds_config.get("emergency_close_level", 110.0)
        )
        
    def _load_symbol_requirements(self):
        """Load symbol margin requirements from configuration"""
        symbol_groups = self.config.get("symbol_groups", {})
        
        for group_name, group_config in symbol_groups.items():
            symbols = group_config.get("symbols", [])
            risk_multiplier = group_config.get("risk_multiplier", 1.0)
            max_exposure = group_config.get("max_exposure", 50.0)
            
            for symbol in symbols:
                # Base margin requirement (will be updated from MT5)
                base_margin = 1000.0  # Default, will be updated
                
                requirement = SymbolMarginRequirement(
                    symbol=symbol,
                    margin_required=base_margin,
                    risk_multiplier=risk_multiplier,
                    max_exposure=max_exposure
                )
                
                self.symbol_requirements[symbol] = requirement
                
    def _load_margin_data(self):
        """Load existing margin data from storage"""
        margin_file = self.log_path.replace('.log', '_data.json')
        try:
            if os.path.exists(margin_file):
                with open(margin_file, 'r') as f:
                    margin_data = json.load(f)
                    
                # Load account history
                for account_data in margin_data.get('account_history', []):
                    account_info = AccountInfo(
                        balance=account_data['balance'],
                        equity=account_data['equity'],
                        margin=account_data['margin'],
                        free_margin=account_data['free_margin'],
                        margin_level=account_data['margin_level'],
                        credit=account_data['credit'],
                        profit=account_data['profit'],
                        timestamp=datetime.fromisoformat(account_data['timestamp'])
                    )
                    self.account_history.append(account_info)
                    
                # Load alerts
                for alert_data in margin_data.get('margin_alerts', []):
                    alert = MarginAlert(
                        alert_id=alert_data['alert_id'],
                        alert_type=MarginStatus(alert_data['alert_type']),
                        margin_level=alert_data['margin_level'],
                        threshold=alert_data['threshold'],
                        message=alert_data['message'],
                        timestamp=datetime.fromisoformat(alert_data['timestamp']),
                        acknowledged=alert_data.get('acknowledged', False)
                    )
                    self.margin_alerts.append(alert)
                    
                self.logger.info(f"Loaded margin data: {len(self.account_history)} history records, {len(self.margin_alerts)} alerts")
                
        except Exception as e:
            self.logger.error(f"Error loading margin data: {e}")
            
    def _save_margin_data(self):
        """Save margin data to storage"""
        margin_file = self.log_path.replace('.log', '_data.json')
        try:
            # Keep only recent history (last 24 hours)
            cutoff_time = datetime.now() - timedelta(hours=24)
            recent_history = [info for info in self.account_history if info.timestamp > cutoff_time]
            
            # Keep only recent alerts (last 7 days)
            alert_cutoff = datetime.now() - timedelta(days=7)
            recent_alerts = [alert for alert in self.margin_alerts if alert.timestamp > alert_cutoff]
            
            margin_data = {
                'account_history': [info.to_dict() for info in recent_history],
                'margin_alerts': [alert.to_dict() for alert in recent_alerts],
                'last_updated': datetime.now().isoformat()
            }
            
            with open(margin_file, 'w') as f:
                json.dump(margin_data, f, indent=4)
                
            # Update in-memory data
            self.account_history = recent_history
            self.margin_alerts = recent_alerts
            
        except Exception as e:
            self.logger.error(f"Error saving margin data: {e}")
            
    def set_dependencies(self, mt5_bridge=None):
        """Set module dependencies"""
        self.mt5_bridge = mt5_bridge
        
    async def _update_account_info(self) -> bool:
        """Update account information from MT5"""
        try:
            if not self.mt5_bridge:
                self.logger.warning("MT5 bridge not available")
                return False
                
            account_data = await self.mt5_bridge.get_account_info()
            if not account_data:
                return False
                
            # Create account info object
            account_info = AccountInfo(
                balance=account_data.get('balance', 0.0),
                equity=account_data.get('equity', 0.0),
                margin=account_data.get('margin', 0.0),
                free_margin=account_data.get('free_margin', 0.0),
                margin_level=account_data.get('margin_level', 0.0),
                credit=account_data.get('credit', 0.0),
                profit=account_data.get('profit', 0.0),
                timestamp=datetime.now()
            )
            
            # Update current info
            self.current_account_info = account_info
            self.account_history.append(account_info)
            
            # Update symbol margin requirements if available
            await self._update_symbol_margins()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error updating account info: {e}")
            return False
            
    async def _update_symbol_margins(self):
        """Update symbol margin requirements from MT5"""
        try:
            if not self.mt5_bridge:
                return
                
            for symbol in self.symbol_requirements.keys():
                try:
                    symbol_info = await self.mt5_bridge.get_symbol_info(symbol)
                    if symbol_info and 'margin_initial' in symbol_info:
                        margin_initial = symbol_info.get('margin_initial', 1000.0)
                        self.symbol_requirements[symbol].margin_required = margin_initial
                except Exception as e:
                    self.logger.warning(f"Could not update margin for {symbol}: {e}")
                    
        except Exception as e:
            self.logger.error(f"Error updating symbol margins: {e}")
            
    def _determine_margin_status(self, margin_level: float) -> MarginStatus:
        """Determine margin status based on current level"""
        if margin_level >= self.thresholds.safe_level:
            return MarginStatus.SAFE
        elif margin_level >= self.thresholds.warning_level:
            return MarginStatus.WARNING
        elif margin_level >= self.thresholds.critical_level:
            return MarginStatus.CRITICAL
        else:
            return MarginStatus.MARGIN_CALL
            
    def _calculate_required_margin(self, symbol: str, volume: float) -> float:
        """Calculate required margin for a trade"""
        if symbol not in self.symbol_requirements:
            # Default margin calculation
            return volume * 1000.0  # Base margin per lot
            
        requirement = self.symbol_requirements[symbol]
        base_margin = requirement.margin_required * volume
        adjusted_margin = base_margin * requirement.risk_multiplier
        
        return adjusted_margin
        
    def _create_margin_alert(self, alert_type: MarginStatus, margin_level: float, message: str):
        """Create a new margin alert"""
        alert_id = f"{alert_type.value}_{int(datetime.now().timestamp())}"
        
        # Check if similar alert was recently created
        cooldown_minutes = self.config.get("alert_cooldown_minutes", 15)
        cutoff_time = datetime.now() - timedelta(minutes=cooldown_minutes)
        
        recent_similar = [
            alert for alert in self.margin_alerts
            if alert.alert_type == alert_type and alert.timestamp > cutoff_time
        ]
        
        if recent_similar:
            return  # Skip duplicate alert
            
        alert = MarginAlert(
            alert_id=alert_id,
            alert_type=alert_type,
            margin_level=margin_level,
            threshold=getattr(self.thresholds, f"{alert_type.value}_level", 0.0),
            message=message,
            timestamp=datetime.now()
        )
        
        self.margin_alerts.append(alert)
        self.logger.warning(f"Margin alert created: {message}")
        
    async def _handle_emergency_situation(self, margin_level: float) -> bool:
        """Handle emergency margin situation"""
        try:
            if not self.config.get("emergency_close_enabled", True):
                return False
                
            if margin_level <= self.thresholds.emergency_close_level:
                # Emergency close trades
                self.logger.critical(f"Emergency margin situation: {margin_level}% - Closing trades")
                
                if self.mt5_bridge:
                    # Get open positions
                    positions = await self.mt5_bridge.get_open_positions()
                    
                    # Close most risky positions first
                    for position in sorted(positions, key=lambda x: x.get('profit', 0)):
                        try:
                            close_result = await self.mt5_bridge.close_position(position['ticket'])
                            if close_result.get('success'):
                                self.logger.info(f"Emergency closed position {position['ticket']}")
                                
                                # Check if margin improved enough
                                await self._update_account_info()
                                if self.current_account_info and self.current_account_info.margin_level > self.thresholds.critical_level:
                                    break
                        except Exception as e:
                            self.logger.error(f"Failed to close position {position['ticket']}: {e}")
                            
                return True
                
        except Exception as e:
            self.logger.error(f"Error handling emergency situation: {e}")
            
        return False
        
    async def check_margin_for_trade(self, symbol: str, volume: float, trade_type: str = "buy") -> MarginCheckResult:
        """Check if margin is sufficient for a new trade"""
        try:
            # Update account info if needed
            if not self.current_account_info or (datetime.now() - self.current_account_info.timestamp).total_seconds() > 30:
                await self._update_account_info()
                
            if not self.current_account_info:
                return MarginCheckResult(
                    allowed=False,
                    reason=TradeBlockReason.INSUFFICIENT_MARGIN,
                    current_margin_level=0.0,
                    required_margin=0.0,
                    available_margin=0.0,
                    risk_assessment="Unable to retrieve account information",
                    margin_status=MarginStatus.CRITICAL
                )
                
            current_margin_level = self.current_account_info.margin_level
            margin_status = self._determine_margin_status(current_margin_level)
            
            # Check emergency block
            if self.emergency_block_active:
                if self.emergency_block_expires and datetime.now() < self.emergency_block_expires:
                    return MarginCheckResult(
                        allowed=False,
                        reason=TradeBlockReason.EMERGENCY_BLOCK,
                        current_margin_level=current_margin_level,
                        required_margin=0.0,
                        available_margin=self.current_account_info.free_margin,
                        risk_assessment=f"Emergency block active: {self.emergency_block_reason}",
                        margin_status=margin_status
                    )
                else:
                    self.emergency_block_active = False
                    
            # Check critical margin level
            if margin_status in [MarginStatus.CRITICAL, MarginStatus.MARGIN_CALL]:
                return MarginCheckResult(
                    allowed=False,
                    reason=TradeBlockReason.CRITICAL_LEVEL,
                    current_margin_level=current_margin_level,
                    required_margin=0.0,
                    available_margin=self.current_account_info.free_margin,
                    risk_assessment=f"Margin level critical: {current_margin_level}%",
                    margin_status=margin_status
                )
                
            # Calculate required margin
            required_margin = self._calculate_required_margin(symbol, volume)
            available_margin = self.current_account_info.free_margin
            
            # Check if sufficient margin available
            if required_margin > available_margin:
                return MarginCheckResult(
                    allowed=False,
                    reason=TradeBlockReason.INSUFFICIENT_MARGIN,
                    current_margin_level=current_margin_level,
                    required_margin=required_margin,
                    available_margin=available_margin,
                    risk_assessment=f"Required: {required_margin:.2f}, Available: {available_margin:.2f}",
                    margin_status=margin_status
                )
                
            # Check symbol exposure limits
            if symbol in self.symbol_requirements:
                requirement = self.symbol_requirements[symbol]
                max_exposure_amount = self.current_account_info.equity * (requirement.max_exposure / 100.0)
                
                # Calculate current exposure for this symbol
                current_exposure = 0.0
                if self.mt5_bridge:
                    try:
                        positions = await self.mt5_bridge.get_open_positions()
                        for pos in positions:
                            if pos.get('symbol') == symbol:
                                current_exposure += abs(pos.get('profit', 0)) + pos.get('margin', 0)
                    except Exception:
                        pass
                        
                if current_exposure + required_margin > max_exposure_amount:
                    return MarginCheckResult(
                        allowed=False,
                        reason=TradeBlockReason.SYMBOL_BLOCKED,
                        current_margin_level=current_margin_level,
                        required_margin=required_margin,
                        available_margin=available_margin,
                        risk_assessment=f"Symbol exposure limit exceeded: {symbol}",
                        margin_status=margin_status
                    )
                    
            # All checks passed
            risk_assessment = "Safe"
            if margin_status == MarginStatus.WARNING:
                risk_assessment = "Warning - monitor closely"
                
            return MarginCheckResult(
                allowed=True,
                reason=TradeBlockReason.ALLOWED,
                current_margin_level=current_margin_level,
                required_margin=required_margin,
                available_margin=available_margin,
                risk_assessment=risk_assessment,
                margin_status=margin_status
            )
            
        except Exception as e:
            self.logger.error(f"Error checking margin for trade: {e}")
            return MarginCheckResult(
                allowed=False,
                reason=TradeBlockReason.INSUFFICIENT_MARGIN,
                current_margin_level=0.0,
                required_margin=0.0,
                available_margin=0.0,
                risk_assessment=f"Error: {str(e)}",
                margin_status=MarginStatus.CRITICAL
            )
            
    async def _monitor_margin_levels(self):
        """Background task to monitor margin levels"""
        while self.is_monitoring:
            try:
                # Update account information
                success = await self._update_account_info()
                
                if success and self.current_account_info:
                    margin_level = self.current_account_info.margin_level
                    margin_status = self._determine_margin_status(margin_level)
                    
                    # Create alerts based on status
                    if margin_status == MarginStatus.MARGIN_CALL:
                        self._create_margin_alert(
                            MarginStatus.MARGIN_CALL,
                            margin_level,
                            f"MARGIN CALL - Level: {margin_level}%"
                        )
                        await self._handle_emergency_situation(margin_level)
                        
                    elif margin_status == MarginStatus.CRITICAL:
                        self._create_margin_alert(
                            MarginStatus.CRITICAL,
                            margin_level,
                            f"Critical margin level: {margin_level}%"
                        )
                        
                    elif margin_status == MarginStatus.WARNING:
                        self._create_margin_alert(
                            MarginStatus.WARNING,
                            margin_level,
                            f"Margin warning: {margin_level}%"
                        )
                        
                # Save data periodically
                self._save_margin_data()
                
                await asyncio.sleep(self.config.get("monitoring_interval", 30.0))
                
            except Exception as e:
                self.logger.error(f"Error in margin monitoring loop: {e}")
                await asyncio.sleep(5)  # Prevent tight error loop
                
    def start_monitoring(self):
        """Start background margin monitoring"""
        if not self.config.get('enabled', True):
            self.logger.info("Margin level checker is disabled")
            return
            
        if not self.is_monitoring:
            self.is_monitoring = True
            try:
                self.monitoring_task = asyncio.create_task(self._monitor_margin_levels())
                self.logger.info("Margin monitoring started")
            except RuntimeError:
                self.is_monitoring = False
                self.logger.warning("No event loop running, cannot start monitoring")
                
    def stop_monitoring(self):
        """Stop background monitoring"""
        if self.is_monitoring:
            self.is_monitoring = False
            if self.monitoring_task:
                self.monitoring_task.cancel()
            self.logger.info("Margin monitoring stopped")
            
    def enable_emergency_block(self, reason: str, duration_minutes: int = 60):
        """Enable emergency trade block"""
        self.emergency_block_active = True
        self.emergency_block_reason = reason
        self.emergency_block_expires = datetime.now() + timedelta(minutes=duration_minutes)
        
        self.logger.warning(f"Emergency block enabled: {reason}")
        
    def disable_emergency_block(self):
        """Disable emergency trade block"""
        self.emergency_block_active = False
        self.emergency_block_reason = ""
        self.emergency_block_expires = None
        
        self.logger.info("Emergency block disabled")
        
    def acknowledge_alert(self, alert_id: str) -> bool:
        """Acknowledge a margin alert"""
        for alert in self.margin_alerts:
            if alert.alert_id == alert_id:
                alert.acknowledged = True
                self.logger.info(f"Alert acknowledged: {alert_id}")
                return True
        return False
        
    def get_current_status(self) -> Dict[str, Any]:
        """Get current margin status"""
        if not self.current_account_info:
            return {
                "status": "no_data",
                "message": "No account information available"
            }
            
        margin_level = self.current_account_info.margin_level
        margin_status = self._determine_margin_status(margin_level)
        
        # Count unacknowledged alerts
        unack_alerts = len([a for a in self.margin_alerts if not a.acknowledged])
        
        return {
            "margin_level": margin_level,
            "margin_status": margin_status.value,
            "account_balance": self.current_account_info.balance,
            "account_equity": self.current_account_info.equity,
            "free_margin": self.current_account_info.free_margin,
            "used_margin": self.current_account_info.margin,
            "unrealized_profit": self.current_account_info.profit,
            "thresholds": asdict(self.thresholds),
            "emergency_block_active": self.emergency_block_active,
            "emergency_block_reason": self.emergency_block_reason,
            "unacknowledged_alerts": unack_alerts,
            "last_update": self.current_account_info.timestamp.isoformat(),
            "monitoring_active": self.is_monitoring
        }
        
    def get_recent_alerts(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent margin alerts"""
        recent = sorted(self.margin_alerts, key=lambda x: x.timestamp, reverse=True)[:limit]
        return [alert.to_dict() for alert in recent]
        
    def get_account_history(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get account history for specified time period"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        recent_history = [info for info in self.account_history if info.timestamp > cutoff_time]
        
        return [info.to_dict() for info in recent_history]

# Global instance for easy access
margin_level_checker = MarginLevelChecker()