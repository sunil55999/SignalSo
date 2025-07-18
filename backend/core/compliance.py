"""
SignalOS Compliance & Regulatory Mode System
Handles prop firm requirements and regulatory compliance
"""

import json
import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass

from db.models import ComplianceProfile, UserCompliance
from utils.logging_config import get_logger

logger = get_logger(__name__)


class ComplianceMode(Enum):
    STANDARD = "standard"
    PROP_FIRM = "prop_firm"
    REGULATORY = "regulatory"
    CUSTOM = "custom"


class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class TradingRestriction:
    """Trading restriction configuration"""
    max_lot_size: Optional[float] = None
    max_daily_loss: Optional[float] = None
    max_daily_trades: Optional[int] = None
    max_drawdown: Optional[float] = None
    allowed_symbols: Optional[List[str]] = None
    forbidden_symbols: Optional[List[str]] = None
    trading_hours: Optional[Dict[str, str]] = None
    max_positions: Optional[int] = None
    max_position_size: Optional[float] = None
    stop_loss_required: bool = False
    take_profit_required: bool = False
    news_trading_allowed: bool = True
    scalping_allowed: bool = True
    hedging_allowed: bool = True


@dataclass
class ComplianceRule:
    """Individual compliance rule"""
    name: str
    description: str
    rule_type: str
    parameters: Dict[str, Any]
    severity: RiskLevel
    is_active: bool = True


class ComplianceEngine:
    """Core compliance and regulatory engine"""
    
    def __init__(self):
        self.active_profiles = {}
        self.compliance_rules = {}
        self.violation_history = {}
        
    async def initialize(self):
        """Initialize compliance engine"""
        try:
            await self._load_default_profiles()
            await self._load_compliance_rules()
            logger.info("Compliance engine initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize compliance engine: {e}")
            raise
    
    async def _load_default_profiles(self):
        """Load default compliance profiles"""
        self.default_profiles = {
            "ftmo": {
                "name": "FTMO Prop Firm",
                "description": "Standard FTMO trading rules",
                "restrictions": TradingRestriction(
                    max_daily_loss=0.05,  # 5% daily loss limit
                    max_drawdown=0.10,    # 10% max drawdown
                    max_lot_size=2.0,     # 2 lots maximum
                    stop_loss_required=True,
                    news_trading_allowed=False,
                    scalping_allowed=True,
                    hedging_allowed=False
                ),
                "rules": [
                    ComplianceRule(
                        name="daily_loss_limit",
                        description="Daily loss cannot exceed 5%",
                        rule_type="risk_management",
                        parameters={"max_loss_percent": 5.0},
                        severity=RiskLevel.CRITICAL
                    ),
                    ComplianceRule(
                        name="max_drawdown",
                        description="Maximum drawdown cannot exceed 10%",
                        rule_type="risk_management",
                        parameters={"max_drawdown_percent": 10.0},
                        severity=RiskLevel.CRITICAL
                    ),
                    ComplianceRule(
                        name="stop_loss_required",
                        description="All trades must have stop loss",
                        rule_type="trade_validation",
                        parameters={"require_sl": True},
                        severity=RiskLevel.HIGH
                    )
                ]
            },
            "my_funded_fx": {
                "name": "MyFundedFX",
                "description": "MyFundedFX trading rules",
                "restrictions": TradingRestriction(
                    max_daily_loss=0.05,
                    max_drawdown=0.12,
                    max_lot_size=5.0,
                    max_daily_trades=50,
                    stop_loss_required=True,
                    news_trading_allowed=True,
                    scalping_allowed=True,
                    hedging_allowed=True
                ),
                "rules": [
                    ComplianceRule(
                        name="daily_loss_limit",
                        description="Daily loss cannot exceed 5%",
                        rule_type="risk_management",
                        parameters={"max_loss_percent": 5.0},
                        severity=RiskLevel.CRITICAL
                    ),
                    ComplianceRule(
                        name="max_drawdown",
                        description="Maximum drawdown cannot exceed 12%",
                        rule_type="risk_management",
                        parameters={"max_drawdown_percent": 12.0},
                        severity=RiskLevel.CRITICAL
                    ),
                    ComplianceRule(
                        name="max_daily_trades",
                        description="Maximum 50 trades per day",
                        rule_type="trade_limit",
                        parameters={"max_trades": 50},
                        severity=RiskLevel.MEDIUM
                    )
                ]
            },
            "financed_trader": {
                "name": "The Financed Trader",
                "description": "TFT trading rules",
                "restrictions": TradingRestriction(
                    max_daily_loss=0.04,
                    max_drawdown=0.08,
                    max_lot_size=3.0,
                    max_positions=10,
                    stop_loss_required=True,
                    take_profit_required=True,
                    news_trading_allowed=False,
                    scalping_allowed=False,
                    hedging_allowed=False
                ),
                "rules": [
                    ComplianceRule(
                        name="daily_loss_limit",
                        description="Daily loss cannot exceed 4%",
                        rule_type="risk_management",
                        parameters={"max_loss_percent": 4.0},
                        severity=RiskLevel.CRITICAL
                    ),
                    ComplianceRule(
                        name="max_drawdown",
                        description="Maximum drawdown cannot exceed 8%",
                        rule_type="risk_management",
                        parameters={"max_drawdown_percent": 8.0},
                        severity=RiskLevel.CRITICAL
                    ),
                    ComplianceRule(
                        name="tp_required",
                        description="All trades must have take profit",
                        rule_type="trade_validation",
                        parameters={"require_tp": True},
                        severity=RiskLevel.HIGH
                    )
                ]
            },
            "eu_mifid_ii": {
                "name": "EU MiFID II",
                "description": "European regulatory compliance",
                "restrictions": TradingRestriction(
                    max_lot_size=1.0,
                    max_daily_trades=20,
                    stop_loss_required=True,
                    forbidden_symbols=["CRYPTO"],
                    trading_hours={"start": "08:00", "end": "22:00"}
                ),
                "rules": [
                    ComplianceRule(
                        name="max_leverage",
                        description="Maximum leverage 1:30 for major pairs",
                        rule_type="regulatory",
                        parameters={"max_leverage": 30},
                        severity=RiskLevel.CRITICAL
                    ),
                    ComplianceRule(
                        name="trading_hours",
                        description="Trading only during market hours",
                        rule_type="regulatory",
                        parameters={"start_time": "08:00", "end_time": "22:00"},
                        severity=RiskLevel.MEDIUM
                    )
                ]
            },
            "us_finra": {
                "name": "US FINRA",
                "description": "US regulatory compliance",
                "restrictions": TradingRestriction(
                    max_lot_size=0.5,
                    max_daily_trades=10,
                    stop_loss_required=True,
                    forbidden_symbols=["CRYPTO", "EXOTIC"],
                    scalping_allowed=False
                ),
                "rules": [
                    ComplianceRule(
                        name="pattern_day_trader",
                        description="PDT rule - minimum $25,000 account",
                        rule_type="regulatory",
                        parameters={"min_account_balance": 25000},
                        severity=RiskLevel.CRITICAL
                    ),
                    ComplianceRule(
                        name="no_scalping",
                        description="Scalping not allowed",
                        rule_type="regulatory",
                        parameters={"min_hold_time": 300},  # 5 minutes
                        severity=RiskLevel.HIGH
                    )
                ]
            }
        }
    
    async def _load_compliance_rules(self):
        """Load compliance rules from database"""
        # This would load from your database
        # For now, rules are loaded with profiles
        pass
    
    async def activate_compliance_mode(self, user_id: str, profile_name: str, custom_restrictions: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Activate compliance mode for user"""
        try:
            if profile_name not in self.default_profiles:
                raise ValueError(f"Unknown compliance profile: {profile_name}")
            
            profile = self.default_profiles[profile_name]
            
            # Store active profile for user
            self.active_profiles[user_id] = {
                "profile_name": profile_name,
                "profile": profile,
                "custom_restrictions": custom_restrictions or {},
                "activated_at": datetime.now(),
                "violations": []
            }
            
            # Update database
            await self._update_user_compliance_db(user_id, profile_name, custom_restrictions)
            
            logger.info(f"Compliance mode '{profile_name}' activated for user {user_id}")
            return {
                "success": True,
                "profile": profile_name,
                "message": f"Compliance mode '{profile['name']}' activated successfully"
            }
            
        except Exception as e:
            logger.error(f"Failed to activate compliance mode: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def deactivate_compliance_mode(self, user_id: str) -> Dict[str, Any]:
        """Deactivate compliance mode for user"""
        try:
            if user_id in self.active_profiles:
                del self.active_profiles[user_id]
            
            # Update database
            await self._deactivate_user_compliance_db(user_id)
            
            logger.info(f"Compliance mode deactivated for user {user_id}")
            return {
                "success": True,
                "message": "Compliance mode deactivated successfully"
            }
            
        except Exception as e:
            logger.error(f"Failed to deactivate compliance mode: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def validate_trade(self, user_id: str, trade_params: Dict[str, Any]) -> Dict[str, Any]:
        """Validate trade against compliance rules"""
        try:
            if user_id not in self.active_profiles:
                return {"valid": True, "message": "No compliance mode active"}
            
            profile = self.active_profiles[user_id]
            restrictions = profile["profile"]["restrictions"]
            rules = profile["profile"]["rules"]
            
            violations = []
            
            # Check lot size
            if restrictions.max_lot_size and trade_params.get("volume", 0) > restrictions.max_lot_size:
                violations.append({
                    "rule": "max_lot_size",
                    "message": f"Lot size {trade_params.get('volume')} exceeds maximum {restrictions.max_lot_size}",
                    "severity": "high"
                })
            
            # Check symbol restrictions
            symbol = trade_params.get("symbol", "")
            if restrictions.forbidden_symbols:
                for forbidden in restrictions.forbidden_symbols:
                    if forbidden in symbol:
                        violations.append({
                            "rule": "forbidden_symbol",
                            "message": f"Symbol {symbol} contains forbidden pattern {forbidden}",
                            "severity": "critical"
                        })
            
            if restrictions.allowed_symbols and symbol not in restrictions.allowed_symbols:
                violations.append({
                    "rule": "allowed_symbols",
                    "message": f"Symbol {symbol} not in allowed symbols list",
                    "severity": "high"
                })
            
            # Check stop loss requirement
            if restrictions.stop_loss_required and not trade_params.get("sl"):
                violations.append({
                    "rule": "stop_loss_required",
                    "message": "Stop loss is required for all trades",
                    "severity": "high"
                })
            
            # Check take profit requirement
            if restrictions.take_profit_required and not trade_params.get("tp"):
                violations.append({
                    "rule": "take_profit_required",
                    "message": "Take profit is required for all trades",
                    "severity": "high"
                })
            
            # Check trading hours
            if restrictions.trading_hours:
                current_time = datetime.now().time()
                start_time = datetime.strptime(restrictions.trading_hours["start"], "%H:%M").time()
                end_time = datetime.strptime(restrictions.trading_hours["end"], "%H:%M").time()
                
                if not (start_time <= current_time <= end_time):
                    violations.append({
                        "rule": "trading_hours",
                        "message": f"Trading outside allowed hours ({restrictions.trading_hours['start']}-{restrictions.trading_hours['end']})",
                        "severity": "medium"
                    })
            
            # Check daily limits
            daily_stats = await self._get_daily_trading_stats(user_id)
            
            if restrictions.max_daily_trades and daily_stats["trade_count"] >= restrictions.max_daily_trades:
                violations.append({
                    "rule": "max_daily_trades",
                    "message": f"Daily trade limit ({restrictions.max_daily_trades}) exceeded",
                    "severity": "high"
                })
            
            if restrictions.max_daily_loss and daily_stats["daily_loss"] >= restrictions.max_daily_loss:
                violations.append({
                    "rule": "max_daily_loss",
                    "message": f"Daily loss limit ({restrictions.max_daily_loss * 100}%) exceeded",
                    "severity": "critical"
                })
            
            # Check drawdown
            if restrictions.max_drawdown and daily_stats["drawdown"] >= restrictions.max_drawdown:
                violations.append({
                    "rule": "max_drawdown",
                    "message": f"Maximum drawdown ({restrictions.max_drawdown * 100}%) exceeded",
                    "severity": "critical"
                })
            
            # Log violations
            if violations:
                await self._log_compliance_violations(user_id, violations)
            
            return {
                "valid": len(violations) == 0,
                "violations": violations,
                "critical_violations": len([v for v in violations if v["severity"] == "critical"]),
                "profile": profile["profile_name"]
            }
            
        except Exception as e:
            logger.error(f"Trade validation failed: {e}")
            return {
                "valid": False,
                "error": str(e)
            }
    
    async def _get_daily_trading_stats(self, user_id: str) -> Dict[str, Any]:
        """Get daily trading statistics for user"""
        # This would query your database for daily stats
        # For now, return mock data
        return {
            "trade_count": 5,
            "daily_loss": 0.02,  # 2%
            "drawdown": 0.05,    # 5%
            "profit_loss": -200.0
        }
    
    async def _log_compliance_violations(self, user_id: str, violations: List[Dict[str, Any]]):
        """Log compliance violations"""
        if user_id not in self.violation_history:
            self.violation_history[user_id] = []
        
        for violation in violations:
            self.violation_history[user_id].append({
                "timestamp": datetime.now(),
                "violation": violation,
                "resolved": False
            })
        
        logger.warning(f"Compliance violations logged for user {user_id}: {len(violations)} violations")
    
    async def _update_user_compliance_db(self, user_id: str, profile_name: str, custom_restrictions: Optional[Dict[str, Any]]):
        """Update user compliance in database"""
        # This would update your database
        logger.info(f"Updated user compliance DB: {user_id} -> {profile_name}")
    
    async def _deactivate_user_compliance_db(self, user_id: str):
        """Deactivate user compliance in database"""
        # This would update your database
        logger.info(f"Deactivated user compliance DB: {user_id}")
    
    async def get_compliance_status(self, user_id: str) -> Dict[str, Any]:
        """Get compliance status for user"""
        try:
            if user_id not in self.active_profiles:
                return {
                    "active": False,
                    "profile": None,
                    "message": "No compliance mode active"
                }
            
            profile = self.active_profiles[user_id]
            violations = self.violation_history.get(user_id, [])
            
            # Get recent violations (last 24 hours)
            recent_violations = [
                v for v in violations 
                if (datetime.now() - v["timestamp"]).days < 1
            ]
            
            return {
                "active": True,
                "profile": profile["profile_name"],
                "profile_name": profile["profile"]["name"],
                "activated_at": profile["activated_at"].isoformat(),
                "total_violations": len(violations),
                "recent_violations": len(recent_violations),
                "critical_violations": len([v for v in recent_violations if v["violation"]["severity"] == "critical"]),
                "status": "healthy" if len(recent_violations) == 0 else "warning"
            }
            
        except Exception as e:
            logger.error(f"Failed to get compliance status: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_available_profiles(self) -> Dict[str, Any]:
        """Get available compliance profiles"""
        try:
            profiles = []
            for profile_id, profile_data in self.default_profiles.items():
                profiles.append({
                    "id": profile_id,
                    "name": profile_data["name"],
                    "description": profile_data["description"],
                    "category": "prop_firm" if "prop" in profile_id.lower() else "regulatory",
                    "restrictions_count": len(profile_data["rules"])
                })
            
            return {
                "success": True,
                "profiles": profiles,
                "total": len(profiles)
            }
            
        except Exception as e:
            logger.error(f"Failed to get available profiles: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_profile_details(self, profile_id: str) -> Dict[str, Any]:
        """Get detailed profile information"""
        try:
            if profile_id not in self.default_profiles:
                raise ValueError(f"Profile {profile_id} not found")
            
            profile = self.default_profiles[profile_id]
            
            # Convert restrictions to dict
            restrictions = profile["restrictions"]
            restrictions_dict = {
                "max_lot_size": restrictions.max_lot_size,
                "max_daily_loss": restrictions.max_daily_loss,
                "max_daily_trades": restrictions.max_daily_trades,
                "max_drawdown": restrictions.max_drawdown,
                "allowed_symbols": restrictions.allowed_symbols,
                "forbidden_symbols": restrictions.forbidden_symbols,
                "trading_hours": restrictions.trading_hours,
                "max_positions": restrictions.max_positions,
                "stop_loss_required": restrictions.stop_loss_required,
                "take_profit_required": restrictions.take_profit_required,
                "news_trading_allowed": restrictions.news_trading_allowed,
                "scalping_allowed": restrictions.scalping_allowed,
                "hedging_allowed": restrictions.hedging_allowed
            }
            
            # Convert rules to dict
            rules_dict = []
            for rule in profile["rules"]:
                rules_dict.append({
                    "name": rule.name,
                    "description": rule.description,
                    "rule_type": rule.rule_type,
                    "parameters": rule.parameters,
                    "severity": rule.severity.value,
                    "is_active": rule.is_active
                })
            
            return {
                "success": True,
                "profile": {
                    "id": profile_id,
                    "name": profile["name"],
                    "description": profile["description"],
                    "restrictions": restrictions_dict,
                    "rules": rules_dict
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get profile details: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def create_custom_profile(self, user_id: str, profile_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create custom compliance profile"""
        try:
            profile_id = f"custom_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Validate profile data
            required_fields = ["name", "description", "restrictions"]
            for field in required_fields:
                if field not in profile_data:
                    raise ValueError(f"Missing required field: {field}")
            
            # Create custom profile
            custom_profile = {
                "name": profile_data["name"],
                "description": profile_data["description"],
                "restrictions": TradingRestriction(**profile_data["restrictions"]),
                "rules": []
            }
            
            # Add to profiles
            self.default_profiles[profile_id] = custom_profile
            
            # Save to database
            await self._save_custom_profile_db(user_id, profile_id, custom_profile)
            
            logger.info(f"Custom profile created: {profile_id} for user {user_id}")
            return {
                "success": True,
                "profile_id": profile_id,
                "message": "Custom profile created successfully"
            }
            
        except Exception as e:
            logger.error(f"Failed to create custom profile: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _save_custom_profile_db(self, user_id: str, profile_id: str, profile_data: Dict[str, Any]):
        """Save custom profile to database"""
        # This would save to your database
        logger.info(f"Saved custom profile to DB: {profile_id}")
    
    async def generate_compliance_report(self, user_id: str, days: int = 30) -> Dict[str, Any]:
        """Generate compliance report for user"""
        try:
            if user_id not in self.active_profiles:
                return {
                    "success": False,
                    "error": "No active compliance profile"
                }
            
            profile = self.active_profiles[user_id]
            violations = self.violation_history.get(user_id, [])
            
            # Filter violations by date range
            cutoff_date = datetime.now() - timedelta(days=days)
            period_violations = [
                v for v in violations 
                if v["timestamp"] >= cutoff_date
            ]
            
            # Analyze violations
            violation_summary = {}
            for violation in period_violations:
                rule = violation["violation"]["rule"]
                if rule not in violation_summary:
                    violation_summary[rule] = 0
                violation_summary[rule] += 1
            
            report = {
                "user_id": user_id,
                "profile": profile["profile_name"],
                "report_period": f"{days} days",
                "generated_at": datetime.now().isoformat(),
                "summary": {
                    "total_violations": len(period_violations),
                    "critical_violations": len([v for v in period_violations if v["violation"]["severity"] == "critical"]),
                    "high_violations": len([v for v in period_violations if v["violation"]["severity"] == "high"]),
                    "medium_violations": len([v for v in period_violations if v["violation"]["severity"] == "medium"]),
                    "low_violations": len([v for v in period_violations if v["violation"]["severity"] == "low"])
                },
                "violation_breakdown": violation_summary,
                "compliance_score": max(0, 100 - (len(period_violations) * 5)),  # Simple scoring
                "recommendations": []
            }
            
            # Generate recommendations
            if len(period_violations) > 0:
                report["recommendations"].append("Review trading strategy to reduce compliance violations")
            if violation_summary.get("max_daily_loss", 0) > 0:
                report["recommendations"].append("Implement better risk management to avoid daily loss limits")
            if violation_summary.get("stop_loss_required", 0) > 0:
                report["recommendations"].append("Always set stop loss on trades")
            
            return {
                "success": True,
                "report": report
            }
            
        except Exception as e:
            logger.error(f"Failed to generate compliance report: {e}")
            return {
                "success": False,
                "error": str(e)
            }