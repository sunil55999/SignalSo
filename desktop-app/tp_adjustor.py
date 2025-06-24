"""
TP Adjustor for SignalOS
Implements dynamic take profit adjustments based on pips, R:R ratios, and strategy overrides
"""

import json
import logging
import math
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class TPAdjustmentType(Enum):
    PIPS_ADDITION = "pips_addition"
    RR_RATIO = "rr_ratio"
    STRATEGY_OVERRIDE = "strategy_override"
    PERCENTAGE = "percentage"


@dataclass
class TPAdjustmentRule:
    adjustment_type: TPAdjustmentType
    value: float
    symbol_pattern: str = "default"
    provider_pattern: Optional[str] = None
    enabled: bool = True
    priority: int = 0


@dataclass
class TPAdjustmentResult:
    original_tp: Optional[float]
    adjusted_tp: Optional[float]
    adjustment_pips: float
    adjustment_type: TPAdjustmentType
    reason: str
    timestamp: datetime
    symbol: str
    entry_price: float
    stop_loss: Optional[float]


class TPAdjustor:
    def __init__(self, config_file: str = "config.json", log_file: str = "logs/tp_adjustor_log.json"):
        self.config_file = config_file
        self.log_file = log_file
        self.config = self._load_config()
        self.adjustment_rules: List[TPAdjustmentRule] = []
        self.adjustment_history: List[TPAdjustmentResult] = []
        
        self._setup_logging()
        self._load_adjustment_rules()
        self._load_history()
        
        # Injected modules
        self.strategy_runtime = None
        self.parser = None

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from JSON file"""
        try:
            if Path(self.config_file).exists():
                with open(self.config_file, 'r') as f:
                    config_data = json.load(f)
                    return config_data.get('tp_adjustor', self._create_default_config())
            else:
                return self._create_default_config()
        except Exception as e:
            logging.warning(f"Failed to load TP adjustor config: {e}")
            return self._create_default_config()

    def _create_default_config(self) -> Dict[str, Any]:
        """Create default TP adjustor configuration"""
        default_config = {
            'enabled': True,
            'default_pip_adjustment': 5.0,
            'default_rr_ratio': 2.0,
            'override_enabled': True,
            'log_adjustments': True,
            'pip_values': {
                'EURUSD': 0.0001,
                'GBPUSD': 0.0001,
                'USDJPY': 0.01,
                'USDCHF': 0.0001,
                'XAUUSD': 0.1,
                'default': 0.0001
            },
            'adjustment_rules': [
                {
                    'symbol_pattern': 'default',
                    'adjustment_type': 'pips_addition',
                    'value': 5.0,
                    'enabled': True,
                    'priority': 0
                }
            ]
        }
        
        try:
            config_data = {}
            if Path(self.config_file).exists():
                with open(self.config_file, 'r') as f:
                    config_data = json.load(f)
            
            config_data['tp_adjustor'] = default_config
            
            with open(self.config_file, 'w') as f:
                json.dump(config_data, f, indent=4)
                
        except Exception as e:
            logging.error(f"Failed to save default TP adjustor config: {e}")
        
        return default_config

    def _setup_logging(self):
        """Setup logging for TP adjustor operations"""
        self.logger = logging.getLogger('TPAdjustor')
        self.logger.setLevel(logging.INFO)
        
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    def _load_adjustment_rules(self):
        """Load TP adjustment rules from configuration"""
        self.adjustment_rules = []
        
        rules_config = self.config.get('adjustment_rules', [])
        
        for rule_data in rules_config:
            try:
                rule = TPAdjustmentRule(
                    adjustment_type=TPAdjustmentType(rule_data['adjustment_type']),
                    value=rule_data['value'],
                    symbol_pattern=rule_data.get('symbol_pattern', 'default'),
                    provider_pattern=rule_data.get('provider_pattern'),
                    enabled=rule_data.get('enabled', True),
                    priority=rule_data.get('priority', 0)
                )
                self.adjustment_rules.append(rule)
                
            except Exception as e:
                self.logger.error(f"Failed to load TP adjustment rule: {e}")
        
        # Sort rules by priority (highest first)
        self.adjustment_rules.sort(key=lambda r: r.priority, reverse=True)
        
        self.logger.info(f"Loaded {len(self.adjustment_rules)} TP adjustment rules")

    def _load_history(self):
        """Load TP adjustment history from log file"""
        try:
            if Path(self.log_file).exists():
                with open(self.log_file, 'r') as f:
                    history_data = json.load(f)
                    
                for entry in history_data.get('adjustments', []):
                    result = TPAdjustmentResult(
                        original_tp=entry.get('original_tp'),
                        adjusted_tp=entry.get('adjusted_tp'),
                        adjustment_pips=entry['adjustment_pips'],
                        adjustment_type=TPAdjustmentType(entry['adjustment_type']),
                        reason=entry['reason'],
                        timestamp=datetime.fromisoformat(entry['timestamp']),
                        symbol=entry['symbol'],
                        entry_price=entry['entry_price'],
                        stop_loss=entry.get('stop_loss')
                    )
                    self.adjustment_history.append(result)
        except Exception as e:
            self.logger.warning(f"Failed to load TP adjustment history: {e}")

    def _save_history(self):
        """Save TP adjustment history to log file"""
        try:
            Path(self.log_file).parent.mkdir(parents=True, exist_ok=True)
            
            # Keep only recent history to prevent file bloat
            recent_history = self.adjustment_history[-1000:] if len(self.adjustment_history) > 1000 else self.adjustment_history
            
            history_data = {
                'adjustments': [
                    {
                        'original_tp': result.original_tp,
                        'adjusted_tp': result.adjusted_tp,
                        'adjustment_pips': result.adjustment_pips,
                        'adjustment_type': result.adjustment_type.value,
                        'reason': result.reason,
                        'timestamp': result.timestamp.isoformat(),
                        'symbol': result.symbol,
                        'entry_price': result.entry_price,
                        'stop_loss': result.stop_loss
                    }
                    for result in recent_history
                ],
                'last_updated': datetime.now().isoformat()
            }
            
            with open(self.log_file, 'w') as f:
                json.dump(history_data, f, indent=2)
                
        except Exception as e:
            self.logger.error(f"Failed to save TP adjustment history: {e}")

    def inject_modules(self, strategy_runtime=None, parser=None):
        """Inject module references"""
        self.strategy_runtime = strategy_runtime
        self.parser = parser
        self.logger.info("TP adjustor modules injected")

    def _get_pip_value(self, symbol: str) -> float:
        """Get pip value for symbol"""
        symbol_upper = symbol.upper()
        pip_values = self.config.get('pip_values', {})
        
        if symbol_upper in pip_values:
            return pip_values[symbol_upper]
        
        # Default pip value logic
        if 'JPY' in symbol_upper:
            return 0.01
        else:
            return pip_values.get('default', 0.0001)

    def _match_pattern(self, value: str, pattern: str) -> bool:
        """Check if value matches pattern (supports wildcards)"""
        value = value.upper()
        pattern = pattern.upper()
        
        if pattern == "DEFAULT":
            return True
        elif pattern.endswith("*"):
            return value.startswith(pattern[:-1])
        elif pattern.startswith("*"):
            return value.endswith(pattern[1:])
        else:
            return value == pattern

    def _find_matching_rule(self, symbol: str, provider: Optional[str] = None) -> Optional[TPAdjustmentRule]:
        """Find the highest priority matching rule for symbol/provider"""
        for rule in self.adjustment_rules:
            if not rule.enabled:
                continue
                
            if self._match_pattern(symbol, rule.symbol_pattern):
                if rule.provider_pattern is None or (provider and self._match_pattern(provider, rule.provider_pattern)):
                    return rule
        
        return None

    def _calculate_rr_tp(self, entry_price: float, stop_loss: float, rr_ratio: float, action: str) -> float:
        """Calculate TP based on risk-reward ratio"""
        if not stop_loss:
            return None
        
        risk_distance = abs(entry_price - stop_loss)
        reward_distance = risk_distance * rr_ratio
        
        if action.upper() == 'BUY':
            return entry_price + reward_distance
        else:  # SELL
            return entry_price - reward_distance

    def adjust_tp_by_pips(self, original_tp: Optional[float], pips_to_add: float, 
                         symbol: str, action: str) -> Optional[float]:
        """Adjust TP by adding specified pips"""
        if not original_tp:
            return None
        
        pip_value = self._get_pip_value(symbol)
        pip_adjustment = pips_to_add * pip_value
        
        if action.upper() == 'BUY':
            return original_tp + pip_adjustment
        else:  # SELL
            return original_tp - pip_adjustment

    def adjust_tp_by_rr(self, entry_price: float, stop_loss: Optional[float], 
                       rr_ratio: float, action: str) -> Optional[float]:
        """Adjust TP based on risk-reward ratio"""
        if not stop_loss:
            return None
        
        return self._calculate_rr_tp(entry_price, stop_loss, rr_ratio, action)

    def adjust_tp_by_percentage(self, original_tp: Optional[float], entry_price: float, 
                               percentage: float, action: str) -> Optional[float]:
        """Adjust TP by percentage of entry-to-TP distance"""
        if not original_tp:
            return None
        
        tp_distance = abs(original_tp - entry_price)
        adjustment = tp_distance * (percentage / 100.0)
        
        if action.upper() == 'BUY':
            return original_tp + adjustment
        else:  # SELL
            return original_tp - adjustment

    def process_tp_adjustment(self, signal_data: Dict[str, Any], strategy_config: Dict[str, Any] = None) -> TPAdjustmentResult:
        """
        Main function to process TP adjustment for a signal
        
        Args:
            signal_data: Dictionary containing signal information
            strategy_config: Optional strategy-specific configuration
            
        Returns:
            TPAdjustmentResult with original and adjusted TP values
        """
        symbol = signal_data.get('symbol', 'UNKNOWN')
        action = signal_data.get('action', 'BUY').upper()
        entry_price = signal_data.get('entry', 0.0)
        original_tp = signal_data.get('takeProfit1') or signal_data.get('take_profit')
        stop_loss = signal_data.get('stopLoss') or signal_data.get('stop_loss')
        provider = signal_data.get('provider')
        
        # Check if adjustments are enabled
        if not self.config.get('enabled', True):
            result = TPAdjustmentResult(
                original_tp=original_tp,
                adjusted_tp=original_tp,
                adjustment_pips=0.0,
                adjustment_type=TPAdjustmentType.STRATEGY_OVERRIDE,
                reason="TP adjustment disabled",
                timestamp=datetime.now(),
                symbol=symbol,
                entry_price=entry_price,
                stop_loss=stop_loss
            )
            return result
        
        # Check for strategy override
        if strategy_config and strategy_config.get('tp_override_enabled', False):
            override_value = strategy_config.get('tp_override_value')
            if override_value and self.config.get('override_enabled', True):
                adjusted_tp = override_value
                pip_value = self._get_pip_value(symbol)
                adjustment_pips = abs(adjusted_tp - original_tp) / pip_value if original_tp else 0
                
                result = TPAdjustmentResult(
                    original_tp=original_tp,
                    adjusted_tp=adjusted_tp,
                    adjustment_pips=adjustment_pips,
                    adjustment_type=TPAdjustmentType.STRATEGY_OVERRIDE,
                    reason="Strategy override applied",
                    timestamp=datetime.now(),
                    symbol=symbol,
                    entry_price=entry_price,
                    stop_loss=stop_loss
                )
                
                self._log_adjustment(result)
                return result
        
        # Find matching adjustment rule
        matching_rule = self._find_matching_rule(symbol, provider)
        
        if not matching_rule:
            # No adjustment rule found, return original TP
            result = TPAdjustmentResult(
                original_tp=original_tp,
                adjusted_tp=original_tp,
                adjustment_pips=0.0,
                adjustment_type=TPAdjustmentType.PIPS_ADDITION,
                reason="No matching adjustment rule",
                timestamp=datetime.now(),
                symbol=symbol,
                entry_price=entry_price,
                stop_loss=stop_loss
            )
            return result
        
        # Apply adjustment based on rule type
        adjusted_tp = original_tp
        adjustment_pips = 0.0
        reason = f"Applied {matching_rule.adjustment_type.value} rule"
        
        if matching_rule.adjustment_type == TPAdjustmentType.PIPS_ADDITION:
            if original_tp:
                adjusted_tp = self.adjust_tp_by_pips(original_tp, matching_rule.value, symbol, action)
                pip_value = self._get_pip_value(symbol)
                adjustment_pips = matching_rule.value
                reason = f"Added {matching_rule.value} pips to TP"
            else:
                reason = "No original TP provided for pip adjustment"
                
        elif matching_rule.adjustment_type == TPAdjustmentType.RR_RATIO:
            if stop_loss:
                adjusted_tp = self.adjust_tp_by_rr(entry_price, stop_loss, matching_rule.value, action)
                if adjusted_tp and original_tp:
                    pip_value = self._get_pip_value(symbol)
                    adjustment_pips = abs(adjusted_tp - original_tp) / pip_value
                reason = f"Adjusted TP to {matching_rule.value}:1 R:R ratio"
            else:
                reason = "No stop loss provided for R:R adjustment"
                adjusted_tp = original_tp
                
        elif matching_rule.adjustment_type == TPAdjustmentType.PERCENTAGE:
            if original_tp:
                adjusted_tp = self.adjust_tp_by_percentage(original_tp, entry_price, matching_rule.value, action)
                pip_value = self._get_pip_value(symbol)
                adjustment_pips = abs(adjusted_tp - original_tp) / pip_value if adjusted_tp != original_tp else 0
                reason = f"Adjusted TP by {matching_rule.value}% of distance"
            else:
                reason = "No original TP provided for percentage adjustment"
        
        # Create result
        result = TPAdjustmentResult(
            original_tp=original_tp,
            adjusted_tp=adjusted_tp,
            adjustment_pips=adjustment_pips,
            adjustment_type=matching_rule.adjustment_type,
            reason=reason,
            timestamp=datetime.now(),
            symbol=symbol,
            entry_price=entry_price,
            stop_loss=stop_loss
        )
        
        # Log the adjustment
        self._log_adjustment(result)
        
        return result

    def _log_adjustment(self, result: TPAdjustmentResult):
        """Log TP adjustment action"""
        if not self.config.get('log_adjustments', True):
            return
        
        self.adjustment_history.append(result)
        self._save_history()
        
        self.logger.info(
            f"TP adjustment: {result.symbol} {result.original_tp} -> {result.adjusted_tp} "
            f"({result.adjustment_pips:+.1f} pips) - {result.reason}"
        )

    def add_adjustment_rule(self, symbol_pattern: str, adjustment_type: str, value: float,
                           provider_pattern: Optional[str] = None, priority: int = 0) -> bool:
        """Add new TP adjustment rule"""
        try:
            rule = TPAdjustmentRule(
                adjustment_type=TPAdjustmentType(adjustment_type),
                value=value,
                symbol_pattern=symbol_pattern,
                provider_pattern=provider_pattern,
                enabled=True,
                priority=priority
            )
            
            self.adjustment_rules.append(rule)
            self.adjustment_rules.sort(key=lambda r: r.priority, reverse=True)
            
            self.logger.info(f"Added TP adjustment rule: {symbol_pattern} {adjustment_type} {value}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to add TP adjustment rule: {e}")
            return False

    def get_adjustment_statistics(self) -> Dict[str, Any]:
        """Get statistics about TP adjustments"""
        if not self.adjustment_history:
            return {
                'total_adjustments': 0,
                'average_adjustment_pips': 0.0,
                'symbols_processed': 0,
                'adjustment_types': {}
            }
        
        total_adjustments = len(self.adjustment_history)
        total_pips = sum(abs(adj.adjustment_pips) for adj in self.adjustment_history)
        average_pips = total_pips / total_adjustments if total_adjustments > 0 else 0
        
        symbols_processed = len(set(adj.symbol for adj in self.adjustment_history))
        
        # Count adjustment types
        adjustment_types = {}
        for adj in self.adjustment_history:
            adj_type = adj.adjustment_type.value
            adjustment_types[adj_type] = adjustment_types.get(adj_type, 0) + 1
        
        return {
            'total_adjustments': total_adjustments,
            'average_adjustment_pips': round(average_pips, 2),
            'symbols_processed': symbols_processed,
            'adjustment_types': adjustment_types,
            'enabled': self.config.get('enabled', True),
            'active_rules': len([r for r in self.adjustment_rules if r.enabled])
        }


# Global instance for easy access
tp_adjustor = TPAdjustor()


def adjust_tp(signal_data: Dict[str, Any], strategy_config: Dict[str, Any] = None) -> float:
    """Convenience function for TP adjustment"""
    result = tp_adjustor.process_tp_adjustment(signal_data, strategy_config)
    return result.adjusted_tp