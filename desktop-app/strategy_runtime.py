"""
Strategy Runtime Engine for SignalOS
Evaluates trading strategies and applies conditional logic to signals
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from enum import Enum
from spread_checker import spread_checker, SpreadCheckResult
from randomized_lot_inserter import maybe_randomize_lot
from lotsize_engine import extract_lotsize

class ConditionType(Enum):
    CONFIDENCE_THRESHOLD = "confidence_threshold"
    TIME_FILTER = "time_filter"
    SYMBOL_FILTER = "symbol_filter"
    RISK_MANAGEMENT = "risk_management"
    MARKET_CONDITION = "market_condition"
    TP_HIT_ACTION = "tp_hit_action"
    SL_ADJUSTMENT = "sl_adjustment"
    CUSTOM_LOGIC = "custom_logic"

class ActionType(Enum):
    SKIP_TRADE = "skip_trade"
    MODIFY_TRADE = "modify_trade"
    MOVE_SL_TO_ENTRY = "move_sl_to_entry"
    CLOSE_PARTIAL = "close_partial"
    SCALE_LOT_SIZE = "scale_lot_size"
    ADD_POSITION = "add_position"
    SEND_ALERT = "send_alert"
    EXECUTE_NORMAL = "execute_normal"

@dataclass
class Condition:
    type: ConditionType
    parameters: Dict[str, Any]
    description: str = ""

@dataclass
class Action:
    type: ActionType
    parameters: Dict[str, Any]
    description: str = ""

@dataclass
class StrategyRule:
    id: str
    name: str
    condition: Condition
    action: Action
    enabled: bool = True
    priority: int = 0

@dataclass
class Strategy:
    id: str
    name: str
    description: str
    rules: List[StrategyRule]
    global_settings: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "rules": [
                {
                    "id": rule.id,
                    "name": rule.name,
                    "condition": {
                        "type": rule.condition.type.value,
                        "parameters": rule.condition.parameters,
                        "description": rule.condition.description
                    },
                    "action": {
                        "type": rule.action.type.value,
                        "parameters": rule.action.parameters,
                        "description": rule.action.description
                    },
                    "enabled": rule.enabled,
                    "priority": rule.priority
                }
                for rule in self.rules
            ],
            "global_settings": self.global_settings,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }

@dataclass
class SignalContext:
    signal_data: Dict[str, Any]
    market_data: Dict[str, Any] = None
    account_info: Dict[str, Any] = None
    current_positions: List[Dict[str, Any]] = None
    historical_performance: Dict[str, Any] = None

class StrategyRuntime:
    def __init__(self, config_file: str = "config.json"):
        self.config = self._load_config(config_file)
        self._setup_logging()
        self.current_strategy: Optional[Strategy] = None
        self.execution_history: List[Dict[str, Any]] = []
        
    def _load_config(self, config_file: str) -> Dict[str, Any]:
        """Load configuration from JSON file"""
        try:
            with open(config_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
    
    def _setup_logging(self):
        """Setup logging for strategy execution"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger('StrategyRuntime')
    
    def load_strategy(self, strategy_data: Dict[str, Any]) -> Strategy:
        """Load strategy from JSON data"""
        rules = []
        for rule_data in strategy_data.get("rules", []):
            condition = Condition(
                type=ConditionType(rule_data["condition"]["type"]),
                parameters=rule_data["condition"]["parameters"],
                description=rule_data["condition"].get("description", "")
            )
            
            action = Action(
                type=ActionType(rule_data["action"]["type"]),
                parameters=rule_data["action"]["parameters"],
                description=rule_data["action"].get("description", "")
            )
            
            rule = StrategyRule(
                id=rule_data["id"],
                name=rule_data["name"],
                condition=condition,
                action=action,
                enabled=rule_data.get("enabled", True),
                priority=rule_data.get("priority", 0)
            )
            rules.append(rule)
        
        # Sort rules by priority
        rules.sort(key=lambda x: x.priority, reverse=True)
        
        strategy = Strategy(
            id=strategy_data["id"],
            name=strategy_data["name"],
            description=strategy_data.get("description", ""),
            rules=rules,
            global_settings=strategy_data.get("global_settings", {}),
            created_at=datetime.fromisoformat(strategy_data.get("created_at", datetime.now().isoformat())),
            updated_at=datetime.fromisoformat(strategy_data.get("updated_at", datetime.now().isoformat()))
        )
        
        self.current_strategy = strategy
        self.logger.info(f"Loaded strategy: {strategy.name} with {len(strategy.rules)} rules")
        return strategy
    
    def evaluate_signal(self, signal_data: Dict[str, Any], context: SignalContext = None) -> Dict[str, Any]:
        """Evaluate signal against current strategy and return modified signal or action"""
        if not self.current_strategy:
            self.logger.warning("No strategy loaded, executing signal normally")
            return {"action": ActionType.EXECUTE_NORMAL.value, "signal": signal_data}
        
        if context is None:
            context = SignalContext(signal_data=signal_data)
        
        self.logger.info(f"Evaluating signal {signal_data.get('id')} against strategy {self.current_strategy.name}")
        
        # Check spread before proceeding with strategy evaluation
        symbol = signal_data.get('symbol', '')
        if symbol:
            spread_check_result, spread_info = spread_checker.check_spread_before_trade(symbol, signal_data)
            if spread_check_result == SpreadCheckResult.BLOCKED_HIGH_SPREAD:
                self.logger.warning(f"Signal blocked due to high spread: {symbol}")
                return {
                    "action": ActionType.SKIP_TRADE.value,
                    "signal": signal_data,
                    "parameters": {"reason": "high_spread", "spread_info": spread_info.to_dict() if spread_info else None},
                    "applied_rules": [{"rule_id": "spread_filter", "rule_name": "Spread Filter", "action_type": "skip_trade"}],
                    "strategy_id": self.current_strategy.id,
                    "evaluation_timestamp": datetime.now().isoformat()
                }
            elif spread_check_result in [SpreadCheckResult.BLOCKED_NO_QUOTES, SpreadCheckResult.BLOCKED_STALE_QUOTES]:
                self.logger.warning(f"Signal blocked due to quote issues: {symbol}")
                return {
                    "action": ActionType.SKIP_TRADE.value,
                    "signal": signal_data,
                    "parameters": {"reason": "quote_issues", "spread_info": spread_info.to_dict() if spread_info else None},
                    "applied_rules": [{"rule_id": "spread_filter", "rule_name": "Spread Filter", "action_type": "skip_trade"}],
                    "strategy_id": self.current_strategy.id,
                    "evaluation_timestamp": datetime.now().isoformat()
                }
        
        modified_signal = signal_data.copy()
        final_action = ActionType.EXECUTE_NORMAL
        action_parameters = {}
        applied_rules = []
        
        # Evaluate each rule in priority order
        for rule in self.current_strategy.rules:
            if not rule.enabled:
                continue
            
            if self._evaluate_condition(rule.condition, context):
                self.logger.info(f"Rule '{rule.name}' condition met, applying action")
                
                action_result = self._apply_action(rule.action, modified_signal, context)
                
                if action_result["signal_modified"]:
                    modified_signal = action_result["modified_signal"]
                
                if action_result["action_type"] != ActionType.EXECUTE_NORMAL:
                    final_action = action_result["action_type"]
                    action_parameters.update(action_result.get("parameters", {}))
                
                applied_rules.append({
                    "rule_id": rule.id,
                    "rule_name": rule.name,
                    "action_type": action_result["action_type"].value,
                    "timestamp": datetime.now().isoformat()
                })
                
                # Check if this is a terminal action (skip trade, etc.)
                if action_result["action_type"] in [ActionType.SKIP_TRADE]:
                    break
        
        result = {
            "action": final_action.value,
            "signal": modified_signal,
            "parameters": action_parameters,
            "applied_rules": applied_rules,
            "strategy_id": self.current_strategy.id,
            "evaluation_timestamp": datetime.now().isoformat()
        }
        
        # Log execution result
        self.execution_history.append(result)
        self.logger.info(f"Signal evaluation complete: {final_action.value}")
        
        return result
    
    def _evaluate_condition(self, condition: Condition, context: SignalContext) -> bool:
        """Evaluate a specific condition against signal context"""
        signal = context.signal_data
        
        if condition.type == ConditionType.CONFIDENCE_THRESHOLD:
            threshold = condition.parameters.get("min_confidence", 70.0)
            signal_confidence = float(signal.get("confidence", 0))
            return signal_confidence >= threshold
        
        elif condition.type == ConditionType.TIME_FILTER:
            allowed_hours = condition.parameters.get("allowed_hours", [])
            current_hour = datetime.now().hour
            return current_hour in allowed_hours if allowed_hours else True
        
        elif condition.type == ConditionType.SYMBOL_FILTER:
            allowed_symbols = condition.parameters.get("allowed_symbols", [])
            blocked_symbols = condition.parameters.get("blocked_symbols", [])
            signal_symbol = signal.get("symbol", "")
            
            if blocked_symbols and signal_symbol in blocked_symbols:
                return False
            if allowed_symbols:
                return signal_symbol in allowed_symbols
            return True
        
        elif condition.type == ConditionType.RISK_MANAGEMENT:
            max_risk_percent = condition.parameters.get("max_risk_percent", 2.0)
            account_balance = context.account_info.get("balance", 10000) if context.account_info else 10000
            
            # Calculate signal risk
            entry = float(signal.get("entry", 0))
            stop_loss = float(signal.get("stop_loss", 0))
            lot_size = float(signal.get("lot_size", 0.01))
            
            if entry and stop_loss:
                pip_value = 10  # Simplified pip value calculation
                risk_amount = abs(entry - stop_loss) * lot_size * pip_value
                risk_percent = (risk_amount / account_balance) * 100
                return risk_percent <= max_risk_percent
            
            return True
        
        elif condition.type == ConditionType.MARKET_CONDITION:
            spread_threshold = condition.parameters.get("max_spread_pips", 3.0)
            if context.market_data:
                current_spread = context.market_data.get("spread_pips", 0)
                return current_spread <= spread_threshold
            return True
        
        elif condition.type == ConditionType.TP_HIT_ACTION:
            # Check if any TP level has been hit
            current_price = context.market_data.get("current_price") if context.market_data else None
            if current_price and context.current_positions:
                for position in context.current_positions:
                    if position.get("signal_id") == signal.get("id"):
                        tp_levels = [signal.get(f"take_profit_{i}") for i in range(1, 6)]
                        action_type = signal.get("action", "").upper()
                        
                        for tp in tp_levels:
                            if tp and self._is_tp_hit(current_price, float(tp), action_type):
                                return True
            return False
        
        elif condition.type == ConditionType.CUSTOM_LOGIC:
            # Execute custom Python code (be careful with this in production)
            custom_code = condition.parameters.get("code", "")
            if custom_code:
                try:
                    # Create safe execution environment
                    safe_globals = {
                        "signal": signal,
                        "context": context,
                        "datetime": datetime,
                        "abs": abs,
                        "float": float,
                        "int": int,
                        "str": str,
                        "len": len,
                        "max": max,
                        "min": min,
                    }
                    return bool(eval(custom_code, safe_globals))
                except Exception as e:
                    self.logger.error(f"Error in custom condition: {e}")
                    return False
            return True
        
        return False
    
    def _apply_action(self, action: Action, signal: Dict[str, Any], context: SignalContext) -> Dict[str, Any]:
        """Apply action to signal and return result"""
        modified_signal = signal.copy()
        signal_modified = False
        action_parameters = {}
        
        if action.type == ActionType.SKIP_TRADE:
            return {
                "action_type": ActionType.SKIP_TRADE,
                "signal_modified": False,
                "modified_signal": signal,
                "parameters": {"reason": action.parameters.get("reason", "Strategy rule triggered skip")}
            }
        
        elif action.type == ActionType.MOVE_SL_TO_ENTRY:
            modified_signal["stop_loss"] = signal.get("entry")
            signal_modified = True
            self.logger.info("Moved stop loss to entry price")
        
        elif action.type == ActionType.SCALE_LOT_SIZE:
            scale_factor = action.parameters.get("scale_factor", 1.0)
            current_lot = float(signal.get("lot_size", 0.01))
            modified_signal["lot_size"] = current_lot * scale_factor
            signal_modified = True
            self.logger.info(f"Scaled lot size by {scale_factor}")
        
        elif action.type == ActionType.MODIFY_TRADE:
            modifications = action.parameters.get("modifications", {})
            for key, value in modifications.items():
                if key in modified_signal:
                    modified_signal[key] = value
                    signal_modified = True
        
        elif action.type == ActionType.CLOSE_PARTIAL:
            close_percent = action.parameters.get("close_percent", 50)
            action_parameters["close_percent"] = close_percent
            self.logger.info(f"Scheduled partial close of {close_percent}%")
        
        elif action.type == ActionType.SEND_ALERT:
            alert_message = action.parameters.get("message", "Strategy alert triggered")
            action_parameters["alert_message"] = alert_message
            self.logger.info(f"Alert scheduled: {alert_message}")
        
        return {
            "action_type": action.type,
            "signal_modified": signal_modified,
            "modified_signal": modified_signal,
            "parameters": action_parameters
        }
    
    def _is_tp_hit(self, current_price: float, tp_price: float, action_type: str) -> bool:
        """Check if take profit has been hit"""
        if action_type == "BUY":
            return current_price >= tp_price
        elif action_type == "SELL":
            return current_price <= tp_price
        return False
    
    def create_default_strategy(self) -> Strategy:
        """Create a default conservative strategy"""
        rules = [
            StrategyRule(
                id="confidence_filter",
                name="Confidence Filter",
                condition=Condition(
                    type=ConditionType.CONFIDENCE_THRESHOLD,
                    parameters={"min_confidence": 70.0},
                    description="Skip signals with confidence below 70%"
                ),
                action=Action(
                    type=ActionType.SKIP_TRADE,
                    parameters={"reason": "Low confidence signal"},
                    description="Skip trade due to low confidence"
                ),
                priority=100
            ),
            StrategyRule(
                id="risk_management",
                name="Risk Management",
                condition=Condition(
                    type=ConditionType.RISK_MANAGEMENT,
                    parameters={"max_risk_percent": 2.0},
                    description="Limit risk per trade to 2%"
                ),
                action=Action(
                    type=ActionType.SCALE_LOT_SIZE,
                    parameters={"scale_factor": 0.5},
                    description="Reduce lot size for high risk trades"
                ),
                priority=90
            ),
            StrategyRule(
                id="market_hours",
                name="Market Hours Filter",
                condition=Condition(
                    type=ConditionType.TIME_FILTER,
                    parameters={"allowed_hours": list(range(8, 17))},  # 8 AM to 5 PM
                    description="Only trade during market hours"
                ),
                action=Action(
                    type=ActionType.EXECUTE_NORMAL,
                    parameters={},
                    description="Execute during allowed hours"
                ),
                priority=80
            ),
            StrategyRule(
                id="tp1_hit_move_sl",
                name="Move SL to Entry on TP1",
                condition=Condition(
                    type=ConditionType.TP_HIT_ACTION,
                    parameters={"tp_level": 1},
                    description="When TP1 is hit, move SL to entry"
                ),
                action=Action(
                    type=ActionType.MOVE_SL_TO_ENTRY,
                    parameters={},
                    description="Move stop loss to break-even"
                ),
                priority=70
            )
        ]
        
        strategy = Strategy(
            id="default_conservative",
            name="Default Conservative Strategy",
            description="Conservative trading strategy with risk management and basic rules",
            rules=rules,
            global_settings={
                "max_concurrent_trades": 5,
                "default_lot_size": 0.01,
                "emergency_stop": False
            },
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        self.current_strategy = strategy
        return strategy
    
    def get_strategy_performance(self) -> Dict[str, Any]:
        """Get performance metrics for current strategy"""
        if not self.execution_history:
            return {"total_signals": 0, "actions_taken": {}}
        
        action_counts = {}
        total_signals = len(self.execution_history)
        
        for execution in self.execution_history:
            action = execution["action"]
            action_counts[action] = action_counts.get(action, 0) + 1
        
        return {
            "total_signals": total_signals,
            "actions_taken": action_counts,
            "strategy_id": self.current_strategy.id if self.current_strategy else None,
            "performance_period": {
                "start": self.execution_history[0]["evaluation_timestamp"],
                "end": self.execution_history[-1]["evaluation_timestamp"]
            }
        }
    
    def export_strategy(self, strategy: Strategy = None) -> str:
        """Export strategy to JSON string"""
        target_strategy = strategy or self.current_strategy
        if not target_strategy:
            raise ValueError("No strategy to export")
        
        return json.dumps(target_strategy.to_dict(), indent=2)
    
    def import_strategy(self, strategy_json: str) -> Strategy:
        """Import strategy from JSON string"""
        strategy_data = json.loads(strategy_json)
        return self.load_strategy(strategy_data)

# Example usage and testing
if __name__ == "__main__":
    # Initialize strategy runtime
    runtime = StrategyRuntime()
    
    # Create and load default strategy
    strategy = runtime.create_default_strategy()
    print(f"Loaded strategy: {strategy.name}")
    
    # Example signal
    signal_data = {
        "id": 123,
        "symbol": "EURUSD",
        "action": "BUY",
        "entry": 1.1000,
        "stop_loss": 1.0950,
        "take_profit_1": 1.1050,
        "take_profit_2": 1.1100,
        "lot_size": 0.01,
        "confidence": 85.5,
        "created_at": datetime.now().isoformat()
    }
    
    # Create context with market data
    context = SignalContext(
        signal_data=signal_data,
        market_data={"current_price": 1.1000, "spread_pips": 1.5},
        account_info={"balance": 10000, "equity": 9800}
    )
    
    # Evaluate signal
    result = runtime.evaluate_signal(signal_data, context)
    print(f"Evaluation result: {json.dumps(result, indent=2)}")
    
    # Show strategy performance
    performance = runtime.get_strategy_performance()
    print(f"Strategy performance: {json.dumps(performance, indent=2)}")
    
    # Export strategy
    exported = runtime.export_strategy()
    print(f"Exported strategy length: {len(exported)} characters")