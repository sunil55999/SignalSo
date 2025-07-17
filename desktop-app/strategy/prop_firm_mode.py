#!/usr/bin/env python3
"""
Prop Firm Mode for SignalOS Desktop Application

Implements prop firm trading rules and risk management to enforce
daily loss limits, drawdown restrictions, and position sizing rules.
"""

import json
import logging
import asyncio
from datetime import datetime, timedelta, time
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
import sqlite3

class PropFirmRule(Enum):
    """Prop firm rule types"""
    DAILY_LOSS_LIMIT = "daily_loss_limit"
    MAX_DRAWDOWN = "max_drawdown"
    PROFIT_TARGET = "profit_target"
    POSITION_SIZE_LIMIT = "position_size_limit"
    TRADING_HOURS = "trading_hours"
    MAX_POSITIONS = "max_positions"
    NEWS_BLACKOUT = "news_blackout"
    WEEKEND_HOLD = "weekend_hold"

class RuleStatus(Enum):
    """Rule enforcement status"""
    ACTIVE = "active"
    VIOLATED = "violated"
    WARNING = "warning"
    DISABLED = "disabled"

@dataclass
class PropFirmConfig:
    """Prop firm configuration"""
    firm_name: str
    account_size: float
    daily_loss_limit: float  # Percentage of account
    max_drawdown: float     # Percentage of account
    profit_target: Optional[float]  # Percentage of account
    max_position_size: float  # Percentage of account per position
    max_total_risk: float    # Percentage of account total risk
    trading_start_time: str  # "09:00"
    trading_end_time: str    # "17:00"
    max_positions: int
    allow_weekend_holds: bool
    enable_news_filter: bool
    challenge_mode: bool = False

@dataclass
class TradingStats:
    """Daily trading statistics"""
    date: str
    starting_balance: float
    current_balance: float
    realized_pnl: float
    unrealized_pnl: float
    total_pnl: float
    drawdown: float
    max_drawdown: float
    trades_count: int
    winning_trades: int
    losing_trades: int
    largest_win: float
    largest_loss: float

@dataclass
class RuleViolation:
    """Rule violation record"""
    timestamp: datetime
    rule_type: PropFirmRule
    description: str
    current_value: float
    limit_value: float
    severity: str  # "warning", "violation", "critical"
    action_taken: str

class PropFirmMode:
    """Prop firm trading mode with rule enforcement"""
    
    def __init__(self, config_file: str = "config.json", db_file: str = "prop_firm.db"):
        self.config_file = config_file
        self.db_file = db_file
        self.config = self._load_config()
        self._setup_logging()
        self._setup_database()
        
        # Prop firm configuration
        self.prop_config = self._load_prop_config()
        
        # Current state
        self.is_active = False
        self.trading_allowed = True
        self.current_stats = None
        self.active_violations = []
        
        # Rule monitoring
        self.rule_checks = {
            PropFirmRule.DAILY_LOSS_LIMIT: self._check_daily_loss_limit,
            PropFirmRule.MAX_DRAWDOWN: self._check_max_drawdown,
            PropFirmRule.PROFIT_TARGET: self._check_profit_target,
            PropFirmRule.POSITION_SIZE_LIMIT: self._check_position_size,
            PropFirmRule.TRADING_HOURS: self._check_trading_hours,
            PropFirmRule.MAX_POSITIONS: self._check_max_positions,
        }
        
        # External module references
        self.mt5_bridge = None
        self.account_monitor = None
        
    def _load_config(self) -> Dict[str, Any]:
        """Load prop firm configuration"""
        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)
                return config.get('prop_firm_mode', self._get_default_config())
        except FileNotFoundError:
            return self._create_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default prop firm configuration"""
        return {
            "enabled": False,
            "firm_name": "FTMO",
            "account_size": 100000.0,
            "daily_loss_limit": 5.0,  # 5%
            "max_drawdown": 10.0,     # 10%
            "profit_target": 10.0,    # 10%
            "max_position_size": 2.0, # 2%
            "max_total_risk": 5.0,    # 5%
            "trading_start_time": "09:00",
            "trading_end_time": "17:00",
            "max_positions": 10,
            "allow_weekend_holds": False,
            "enable_news_filter": True,
            "challenge_mode": False,
            "auto_close_on_violation": True,
            "warning_thresholds": {
                "daily_loss": 80,  # 80% of daily limit
                "drawdown": 80     # 80% of max drawdown
            },
            "predefined_configs": {
                "FTMO": {
                    "daily_loss_limit": 5.0,
                    "max_drawdown": 10.0,
                    "profit_target": 10.0
                },
                "MyForexFunds": {
                    "daily_loss_limit": 5.0,
                    "max_drawdown": 12.0,
                    "profit_target": 8.0
                },
                "TopstepFX": {
                    "daily_loss_limit": 3.0,
                    "max_drawdown": 6.0,
                    "profit_target": 6.0
                }
            }
        }
    
    def _create_default_config(self) -> Dict[str, Any]:
        """Create default configuration and save to file"""
        default_config = {
            "prop_firm_mode": self._get_default_config()
        }
        
        try:
            with open(self.config_file, 'w') as f:
                json.dump(default_config, f, indent=4)
        except Exception as e:
            logging.error(f"Failed to save default config: {e}")
            
        return default_config["prop_firm_mode"]
    
    def _setup_logging(self):
        """Setup logging for prop firm mode"""
        self.logger = logging.getLogger('PropFirmMode')
        self.logger.setLevel(logging.INFO)
        
        if not self.logger.handlers:
            # File handler
            log_file = Path("logs") / "prop_firm.log"
            log_file.parent.mkdir(exist_ok=True)
            
            file_handler = logging.FileHandler(log_file)
            file_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            file_handler.setFormatter(file_formatter)
            self.logger.addHandler(file_handler)
            
            # Console handler
            console_handler = logging.StreamHandler()
            console_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            console_handler.setFormatter(console_formatter)
            self.logger.addHandler(console_handler)
    
    def _setup_database(self):
        """Setup SQLite database for tracking"""
        try:
            with sqlite3.connect(self.db_file) as conn:
                cursor = conn.cursor()
                
                # Create tables
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS daily_stats (
                        date TEXT PRIMARY KEY,
                        starting_balance REAL,
                        current_balance REAL,
                        realized_pnl REAL,
                        unrealized_pnl REAL,
                        total_pnl REAL,
                        drawdown REAL,
                        max_drawdown REAL,
                        trades_count INTEGER,
                        winning_trades INTEGER,
                        losing_trades INTEGER,
                        largest_win REAL,
                        largest_loss REAL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS rule_violations (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TIMESTAMP,
                        rule_type TEXT,
                        description TEXT,
                        current_value REAL,
                        limit_value REAL,
                        severity TEXT,
                        action_taken TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS trade_log (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TIMESTAMP,
                        symbol TEXT,
                        action TEXT,
                        volume REAL,
                        price REAL,
                        pnl REAL,
                        allowed BOOLEAN,
                        reason TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                conn.commit()
                
        except Exception as e:
            self.logger.error(f"Database setup error: {e}")
    
    def _load_prop_config(self) -> PropFirmConfig:
        """Load prop firm configuration"""
        firm_name = self.config.get("firm_name", "FTMO")
        
        # Use predefined config if available
        predefined = self.config.get("predefined_configs", {}).get(firm_name, {})
        
        return PropFirmConfig(
            firm_name=firm_name,
            account_size=self.config.get("account_size", 100000.0),
            daily_loss_limit=predefined.get("daily_loss_limit", self.config.get("daily_loss_limit", 5.0)),
            max_drawdown=predefined.get("max_drawdown", self.config.get("max_drawdown", 10.0)),
            profit_target=predefined.get("profit_target", self.config.get("profit_target", 10.0)),
            max_position_size=self.config.get("max_position_size", 2.0),
            max_total_risk=self.config.get("max_total_risk", 5.0),
            trading_start_time=self.config.get("trading_start_time", "09:00"),
            trading_end_time=self.config.get("trading_end_time", "17:00"),
            max_positions=self.config.get("max_positions", 10),
            allow_weekend_holds=self.config.get("allow_weekend_holds", False),
            enable_news_filter=self.config.get("enable_news_filter", True),
            challenge_mode=self.config.get("challenge_mode", False)
        )
    
    def inject_modules(self, mt5_bridge=None, account_monitor=None):
        """Inject external module references"""
        self.mt5_bridge = mt5_bridge
        self.account_monitor = account_monitor
    
    def enable_prop_firm_mode(self) -> bool:
        """Enable prop firm mode"""
        try:
            if not self.config.get("enabled", False):
                self.logger.warning("Prop firm mode is disabled in configuration")
                return False
            
            # Initialize daily stats
            today = datetime.now().strftime("%Y-%m-%d")
            self.current_stats = self._get_or_create_daily_stats(today)
            
            self.is_active = True
            self.trading_allowed = True
            self.active_violations.clear()
            
            self.logger.info(f"Prop firm mode enabled: {self.prop_config.firm_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to enable prop firm mode: {e}")
            return False
    
    def disable_prop_firm_mode(self):
        """Disable prop firm mode"""
        self.is_active = False
        self.trading_allowed = True
        self.active_violations.clear()
        self.logger.info("Prop firm mode disabled")
    
    def _get_or_create_daily_stats(self, date: str) -> TradingStats:
        """Get or create daily trading statistics"""
        try:
            with sqlite3.connect(self.db_file) as conn:
                cursor = conn.cursor()
                
                # Try to get existing stats
                cursor.execute(
                    "SELECT * FROM daily_stats WHERE date = ?",
                    (date,)
                )
                row = cursor.fetchone()
                
                if row:
                    return TradingStats(
                        date=row[0],
                        starting_balance=row[1],
                        current_balance=row[2],
                        realized_pnl=row[3],
                        unrealized_pnl=row[4],
                        total_pnl=row[5],
                        drawdown=row[6],
                        max_drawdown=row[7],
                        trades_count=row[8],
                        winning_trades=row[9],
                        losing_trades=row[10],
                        largest_win=row[11],
                        largest_loss=row[12]
                    )
                else:
                    # Create new stats
                    starting_balance = self.prop_config.account_size
                    
                    # Get current balance from MT5 if available
                    if self.mt5_bridge and hasattr(self.mt5_bridge, 'get_account_info'):
                        account_info = self.mt5_bridge.get_account_info()
                        if account_info:
                            starting_balance = account_info.balance
                    
                    stats = TradingStats(
                        date=date,
                        starting_balance=starting_balance,
                        current_balance=starting_balance,
                        realized_pnl=0.0,
                        unrealized_pnl=0.0,
                        total_pnl=0.0,
                        drawdown=0.0,
                        max_drawdown=0.0,
                        trades_count=0,
                        winning_trades=0,
                        losing_trades=0,
                        largest_win=0.0,
                        largest_loss=0.0
                    )
                    
                    # Save to database
                    cursor.execute(
                        '''INSERT INTO daily_stats 
                           (date, starting_balance, current_balance, realized_pnl, 
                            unrealized_pnl, total_pnl, drawdown, max_drawdown, 
                            trades_count, winning_trades, losing_trades, 
                            largest_win, largest_loss) 
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                        (stats.date, stats.starting_balance, stats.current_balance,
                         stats.realized_pnl, stats.unrealized_pnl, stats.total_pnl,
                         stats.drawdown, stats.max_drawdown, stats.trades_count,
                         stats.winning_trades, stats.losing_trades,
                         stats.largest_win, stats.largest_loss)
                    )
                    conn.commit()
                    
                    return stats
                    
        except Exception as e:
            self.logger.error(f"Error getting daily stats: {e}")
            # Return default stats
            return TradingStats(
                date=date,
                starting_balance=self.prop_config.account_size,
                current_balance=self.prop_config.account_size,
                realized_pnl=0.0,
                unrealized_pnl=0.0,
                total_pnl=0.0,
                drawdown=0.0,
                max_drawdown=0.0,
                trades_count=0,
                winning_trades=0,
                losing_trades=0,
                largest_win=0.0,
                largest_loss=0.0
            )
    
    def update_daily_stats(self):
        """Update daily trading statistics"""
        if not self.is_active or not self.current_stats:
            return
        
        try:
            # Get current account info
            if self.mt5_bridge and hasattr(self.mt5_bridge, 'get_account_info'):
                account_info = self.mt5_bridge.get_account_info()
                if account_info:
                    self.current_stats.current_balance = account_info.balance
                    self.current_stats.unrealized_pnl = account_info.profit
                    self.current_stats.total_pnl = (
                        self.current_stats.current_balance - self.current_stats.starting_balance
                    )
                    
                    # Calculate drawdown
                    peak_balance = max(self.current_stats.starting_balance, 
                                     self.current_stats.current_balance)
                    self.current_stats.drawdown = (
                        (peak_balance - self.current_stats.current_balance) / peak_balance * 100
                    )
                    self.current_stats.max_drawdown = max(
                        self.current_stats.max_drawdown, 
                        self.current_stats.drawdown
                    )
            
            # Save to database
            self._save_daily_stats()
            
        except Exception as e:
            self.logger.error(f"Error updating daily stats: {e}")
    
    def _save_daily_stats(self):
        """Save daily statistics to database"""
        try:
            with sqlite3.connect(self.db_file) as conn:
                cursor = conn.cursor()
                
                cursor.execute(
                    '''UPDATE daily_stats SET 
                       current_balance = ?, realized_pnl = ?, unrealized_pnl = ?,
                       total_pnl = ?, drawdown = ?, max_drawdown = ?,
                       trades_count = ?, winning_trades = ?, losing_trades = ?,
                       largest_win = ?, largest_loss = ?
                       WHERE date = ?''',
                    (self.current_stats.current_balance, self.current_stats.realized_pnl,
                     self.current_stats.unrealized_pnl, self.current_stats.total_pnl,
                     self.current_stats.drawdown, self.current_stats.max_drawdown,
                     self.current_stats.trades_count, self.current_stats.winning_trades,
                     self.current_stats.losing_trades, self.current_stats.largest_win,
                     self.current_stats.largest_loss, self.current_stats.date)
                )
                conn.commit()
                
        except Exception as e:
            self.logger.error(f"Error saving daily stats: {e}")
    
    def _check_daily_loss_limit(self) -> Optional[RuleViolation]:
        """Check daily loss limit rule"""
        if not self.current_stats:
            return None
        
        daily_loss_amount = self.prop_config.account_size * (self.prop_config.daily_loss_limit / 100)
        current_loss = abs(min(0, self.current_stats.total_pnl))
        
        if current_loss >= daily_loss_amount:
            return RuleViolation(
                timestamp=datetime.now(),
                rule_type=PropFirmRule.DAILY_LOSS_LIMIT,
                description=f"Daily loss limit exceeded",
                current_value=current_loss,
                limit_value=daily_loss_amount,
                severity="violation",
                action_taken="trading_disabled"
            )
        elif current_loss >= daily_loss_amount * 0.8:  # Warning at 80%
            return RuleViolation(
                timestamp=datetime.now(),
                rule_type=PropFirmRule.DAILY_LOSS_LIMIT,
                description=f"Approaching daily loss limit",
                current_value=current_loss,
                limit_value=daily_loss_amount,
                severity="warning",
                action_taken="none"
            )
        
        return None
    
    def _check_max_drawdown(self) -> Optional[RuleViolation]:
        """Check maximum drawdown rule"""
        if not self.current_stats:
            return None
        
        if self.current_stats.drawdown >= self.prop_config.max_drawdown:
            return RuleViolation(
                timestamp=datetime.now(),
                rule_type=PropFirmRule.MAX_DRAWDOWN,
                description=f"Maximum drawdown exceeded",
                current_value=self.current_stats.drawdown,
                limit_value=self.prop_config.max_drawdown,
                severity="violation",
                action_taken="trading_disabled"
            )
        elif self.current_stats.drawdown >= self.prop_config.max_drawdown * 0.8:
            return RuleViolation(
                timestamp=datetime.now(),
                rule_type=PropFirmRule.MAX_DRAWDOWN,
                description=f"Approaching maximum drawdown",
                current_value=self.current_stats.drawdown,
                limit_value=self.prop_config.max_drawdown,
                severity="warning",
                action_taken="none"
            )
        
        return None
    
    def _check_profit_target(self) -> Optional[RuleViolation]:
        """Check profit target achievement"""
        if not self.current_stats or not self.prop_config.profit_target:
            return None
        
        profit_target_amount = self.prop_config.account_size * (self.prop_config.profit_target / 100)
        
        if self.current_stats.total_pnl >= profit_target_amount:
            return RuleViolation(
                timestamp=datetime.now(),
                rule_type=PropFirmRule.PROFIT_TARGET,
                description=f"Profit target achieved",
                current_value=self.current_stats.total_pnl,
                limit_value=profit_target_amount,
                severity="achievement",
                action_taken="target_reached"
            )
        
        return None
    
    def _check_position_size(self) -> Optional[RuleViolation]:
        """Check position size limits"""
        # This would need position data from MT5
        return None
    
    def _check_trading_hours(self) -> Optional[RuleViolation]:
        """Check trading hours restrictions"""
        current_time = datetime.now().time()
        start_time = time.fromisoformat(self.prop_config.trading_start_time)
        end_time = time.fromisoformat(self.prop_config.trading_end_time)
        
        if not (start_time <= current_time <= end_time):
            return RuleViolation(
                timestamp=datetime.now(),
                rule_type=PropFirmRule.TRADING_HOURS,
                description=f"Trading outside allowed hours",
                current_value=current_time.hour + current_time.minute/60,
                limit_value=0,
                severity="violation",
                action_taken="trade_blocked"
            )
        
        return None
    
    def _check_max_positions(self) -> Optional[RuleViolation]:
        """Check maximum positions limit"""
        # This would need position data from MT5
        return None
    
    def check_all_rules(self) -> List[RuleViolation]:
        """Check all prop firm rules"""
        violations = []
        
        for rule_type, check_function in self.rule_checks.items():
            violation = check_function()
            if violation:
                violations.append(violation)
        
        return violations
    
    def can_trade(self, trade_request: Dict[str, Any]) -> Tuple[bool, str]:
        """Check if a trade is allowed under prop firm rules"""
        if not self.is_active:
            return True, "Prop firm mode not active"
        
        if not self.trading_allowed:
            return False, "Trading disabled due to rule violations"
        
        # Update stats before checking
        self.update_daily_stats()
        
        # Check all rules
        violations = self.check_all_rules()
        
        critical_violations = [v for v in violations if v.severity in ["violation", "critical"]]
        
        if critical_violations:
            # Log violations
            for violation in critical_violations:
                self._log_violation(violation)
            
            # Disable trading if auto-close is enabled
            if self.config.get("auto_close_on_violation", True):
                self.trading_allowed = False
            
            return False, f"Rule violation: {critical_violations[0].description}"
        
        # Check warnings
        warnings = [v for v in violations if v.severity == "warning"]
        if warnings:
            for warning in warnings:
                self._log_violation(warning)
        
        return True, "Trade allowed"
    
    def _log_violation(self, violation: RuleViolation):
        """Log rule violation to database"""
        try:
            with sqlite3.connect(self.db_file) as conn:
                cursor = conn.cursor()
                
                cursor.execute(
                    '''INSERT INTO rule_violations 
                       (timestamp, rule_type, description, current_value, 
                        limit_value, severity, action_taken) 
                       VALUES (?, ?, ?, ?, ?, ?, ?)''',
                    (violation.timestamp.isoformat(), violation.rule_type.value,
                     violation.description, violation.current_value,
                     violation.limit_value, violation.severity, violation.action_taken)
                )
                conn.commit()
                
            self.logger.warning(f"Rule violation: {violation.description}")
            
        except Exception as e:
            self.logger.error(f"Error logging violation: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current prop firm mode status"""
        violations = self.check_all_rules() if self.is_active else []
        
        return {
            "active": self.is_active,
            "trading_allowed": self.trading_allowed,
            "firm_config": asdict(self.prop_config),
            "current_stats": asdict(self.current_stats) if self.current_stats else None,
            "active_violations": len([v for v in violations if v.severity == "violation"]),
            "warnings": len([v for v in violations if v.severity == "warning"]),
            "last_update": datetime.now().isoformat()
        }


# Example usage and testing
async def main():
    """Example usage of prop firm mode"""
    prop_firm = PropFirmMode()
    
    # Enable prop firm mode
    if prop_firm.enable_prop_firm_mode():
        print("Prop firm mode enabled")
        
        # Update stats
        prop_firm.update_daily_stats()
        
        # Check if trade is allowed
        trade_request = {
            "symbol": "EURUSD",
            "action": "buy",
            "volume": 0.1
        }
        
        allowed, reason = prop_firm.can_trade(trade_request)
        print(f"Trade allowed: {allowed}, Reason: {reason}")
        
        # Get status
        status = prop_firm.get_status()
        print(f"Status: {json.dumps(status, indent=2)}")
    else:
        print("Failed to enable prop firm mode")


if __name__ == "__main__":
    asyncio.run(main())