"""
Strategy Condition Router Engine for SignalOS
Routes signals through different processing paths based on configurable conditions and market states
"""

import json
import time
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import os
import importlib

class ConditionType(Enum):
    MARKET_HOURS = "market_hours"
    VOLATILITY = "volatility"
    NEWS_EVENTS = "news_events"
    SYMBOL_TYPE = "symbol_type"
    PROVIDER = "provider"
    CONFIDENCE = "confidence"
    VOLUME = "volume"
    TIME_WINDOW = "time_window"
    ACCOUNT_STATE = "account_state"
    CUSTOM = "custom"

class RouteAction(Enum):
    PROCESS_NORMAL = "process_normal"
    ROUTE_TO_REVERSE = "route_to_reverse"
    ROUTE_TO_GRID = "route_to_grid"
    ROUTE_TO_MULTI_HANDLER = "route_to_multi_handler"
    BLOCK_SIGNAL = "block_signal"
    DELAY_SIGNAL = "delay_signal"
    SPLIT_SIGNAL = "split_signal"
    ESCALATE_PRIORITY = "escalate_priority"

class ConditionOperator(Enum):
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    GREATER_EQUAL = "greater_equal"
    LESS_EQUAL = "less_equal"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    IN_RANGE = "in_range"
    NOT_IN_RANGE = "not_in_range"

@dataclass
class ConditionRule:
    rule_id: str
    name: str
    condition_type: ConditionType
    operator: ConditionOperator
    value: Any
    enabled: bool = True
    priority: int = 1
    fallback_action: RouteAction = RouteAction.PROCESS_NORMAL

@dataclass
class RoutingRule:
    rule_id: str
    name: str
    conditions: List[ConditionRule]
    condition_logic: str = "AND"  # "AND", "OR", "CUSTOM"
    target_action: RouteAction
    target_params: Dict[str, Any] = None
    enabled: bool = True
    priority: int = 1
    success_count: int = 0
    failure_count: int = 0
    last_executed: Optional[datetime] = None
    
    def __post_init__(self):
        if self.target_params is None:
            self.target_params = {}

@dataclass
class MarketState:
    timestamp: datetime
    volatility_score: float
    market_session: str  # "asian", "european", "american", "overlap"
    news_impact_level: str  # "none", "low", "medium", "high"
    symbol_activity: Dict[str, float]
    account_margin_level: float
    account_equity: float
    active_positions: int

@dataclass
class RouteDecision:
    signal_id: str
    original_action: RouteAction
    routed_action: RouteAction
    routing_rule: Optional[RoutingRule]
    conditions_met: List[str]
    market_state: MarketState
    execution_time: datetime
    success: bool = True
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "signal_id": self.signal_id,
            "original_action": self.original_action.value,
            "routed_action": self.routed_action.value,
            "routing_rule_id": self.routing_rule.rule_id if self.routing_rule else None,
            "conditions_met": self.conditions_met,
            "execution_time": self.execution_time.isoformat(),
            "success": self.success,
            "error_message": self.error_message
        }

class StrategyConditionRouter:
    def __init__(self, config_path: str = "config.json", log_path: str = "logs/strategy_condition_router.log"):
        self.config_path = config_path
        self.log_path = log_path
        self.config = self._load_config()
        self.logger = self._setup_logger()
        
        # Routing system
        self.routing_rules: List[RoutingRule] = []
        self.route_decisions: List[RouteDecision] = []
        self.market_state: Optional[MarketState] = None
        
        # Strategy modules
        self.strategy_modules: Dict[str, Any] = {}
        
        # Performance tracking
        self.routing_stats = {
            "total_signals": 0,
            "successful_routes": 0,
            "failed_routes": 0,
            "blocked_signals": 0,
            "escalated_signals": 0
        }
        
        # Background monitoring
        self.monitoring_task = None
        self.is_monitoring = False
        
        # Load configuration and modules
        self._load_routing_rules()
        self._load_strategy_modules()
        self._load_routing_data()
        
    def _load_config(self) -> Dict[str, Any]:
        """Load strategy condition router configuration"""
        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)
                
            if "strategy_condition_router" not in config:
                config["strategy_condition_router"] = {
                    "enabled": True,
                    "monitoring_interval": 10.0,
                    "market_state_update_interval": 30.0,
                    "enable_fallback_routing": True,
                    "default_action": "process_normal",
                    "max_routing_depth": 3,
                    "routing_rules": [
                        {
                            "rule_id": "high_volatility_to_reverse",
                            "name": "Route High Volatility to Reverse Strategy",
                            "conditions": [
                                {
                                    "rule_id": "vol_condition",
                                    "name": "High Volatility",
                                    "condition_type": "volatility",
                                    "operator": "greater_than",
                                    "value": 2.0,
                                    "enabled": True,
                                    "priority": 1
                                }
                            ],
                            "condition_logic": "AND",
                            "target_action": "route_to_reverse",
                            "enabled": True,
                            "priority": 1
                        },
                        {
                            "rule_id": "ranging_market_to_grid",
                            "name": "Route Ranging Market to Grid Strategy",
                            "conditions": [
                                {
                                    "rule_id": "low_vol_condition",
                                    "name": "Low Volatility",
                                    "condition_type": "volatility",
                                    "operator": "less_than",
                                    "value": 1.0,
                                    "enabled": True,
                                    "priority": 1
                                },
                                {
                                    "rule_id": "no_news_condition",
                                    "name": "No News Events",
                                    "condition_type": "news_events",
                                    "operator": "equals",
                                    "value": "none",
                                    "enabled": True,
                                    "priority": 1
                                }
                            ],
                            "condition_logic": "AND",
                            "target_action": "route_to_grid",
                            "enabled": False,
                            "priority": 2
                        },
                        {
                            "rule_id": "multiple_signals_handler",
                            "name": "Route Multiple Signals to Handler",
                            "conditions": [
                                {
                                    "rule_id": "multi_signal_condition",
                                    "name": "Multiple Concurrent Signals",
                                    "condition_type": "custom",
                                    "operator": "greater_than",
                                    "value": 2,
                                    "enabled": True,
                                    "priority": 1
                                }
                            ],
                            "condition_logic": "AND",
                            "target_action": "route_to_multi_handler",
                            "enabled": True,
                            "priority": 3
                        }
                    ],
                    "market_sessions": {
                        "asian": {"start": "21:00", "end": "06:00"},
                        "european": {"start": "07:00", "end": "16:00"},
                        "american": {"start": "13:00", "end": "22:00"}
                    },
                    "symbol_classifications": {
                        "major_pairs": ["EURUSD", "GBPUSD", "AUDUSD", "NZDUSD", "USDCAD", "USDCHF", "USDJPY"],
                        "minor_pairs": ["EURGBP", "EURAUD", "EURCHF", "GBPAUD", "GBPCHF"],
                        "exotic_pairs": ["USDZAR", "USDTRY", "USDRUB"],
                        "commodities": ["XAUUSD", "XAGUSD", "USOIL", "UKOIL"],
                        "crypto": ["BTCUSD", "ETHUSD"]
                    }
                }
                self._save_config(config)
                
            return config.get("strategy_condition_router", {})
            
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
            "monitoring_interval": 10.0,
            "market_state_update_interval": 30.0,
            "enable_fallback_routing": True,
            "default_action": "process_normal",
            "max_routing_depth": 3,
            "routing_rules": [],
            "market_sessions": {},
            "symbol_classifications": {}
        }
        
    def _save_config(self, full_config: Dict[str, Any]):
        """Save updated configuration"""
        try:
            with open(self.config_path, 'w') as f:
                json.dump(full_config, f, indent=4)
        except Exception as e:
            self.logger.error(f"Failed to save config: {e}")
            
    def _setup_logger(self) -> logging.Logger:
        """Setup dedicated logger for strategy condition router"""
        logger = logging.getLogger("strategy_condition_router")
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
        
    def _load_routing_rules(self):
        """Load routing rules from configuration"""
        rules_config = self.config.get("routing_rules", [])
        
        for rule_config in rules_config:
            try:
                # Parse conditions
                conditions = []
                for cond_config in rule_config.get("conditions", []):
                    condition = ConditionRule(
                        rule_id=cond_config.get("rule_id", ""),
                        name=cond_config.get("name", ""),
                        condition_type=ConditionType(cond_config.get("condition_type", "custom")),
                        operator=ConditionOperator(cond_config.get("operator", "equals")),
                        value=cond_config.get("value"),
                        enabled=cond_config.get("enabled", True),
                        priority=cond_config.get("priority", 1)
                    )
                    conditions.append(condition)
                    
                # Create routing rule
                rule = RoutingRule(
                    rule_id=rule_config.get("rule_id", ""),
                    name=rule_config.get("name", ""),
                    conditions=conditions,
                    condition_logic=rule_config.get("condition_logic", "AND"),
                    target_action=RouteAction(rule_config.get("target_action", "process_normal")),
                    target_params=rule_config.get("target_params", {}),
                    enabled=rule_config.get("enabled", True),
                    priority=rule_config.get("priority", 1)
                )
                
                self.routing_rules.append(rule)
                
            except Exception as e:
                self.logger.error(f"Error loading routing rule: {e}")
                
        # Sort by priority
        self.routing_rules.sort(key=lambda x: x.priority)
        self.logger.info(f"Loaded {len(self.routing_rules)} routing rules")
        
    def _load_strategy_modules(self):
        """Load and initialize strategy modules"""
        try:
            # Import strategy modules dynamically
            module_names = [
                'reverse_strategy',
                'grid_strategy', 
                'multi_signal_handler'
            ]
            
            for module_name in module_names:
                try:
                    module = importlib.import_module(module_name)
                    # Get the global instance from each module
                    if hasattr(module, module_name.replace('_', '_')):
                        instance = getattr(module, module_name.replace('_', '_'))
                        self.strategy_modules[module_name] = instance
                        self.logger.info(f"Loaded strategy module: {module_name}")
                except ImportError as e:
                    self.logger.warning(f"Could not import {module_name}: {e}")
                except Exception as e:
                    self.logger.error(f"Error loading {module_name}: {e}")
                    
        except Exception as e:
            self.logger.error(f"Error loading strategy modules: {e}")
            
    def _load_routing_data(self):
        """Load existing routing data from storage"""
        routing_file = self.log_path.replace('.log', '_routing.json')
        try:
            if os.path.exists(routing_file):
                with open(routing_file, 'r') as f:
                    routing_data = json.load(f)
                    
                # Load statistics
                if 'statistics' in routing_data:
                    self.routing_stats.update(routing_data['statistics'])
                    
                self.logger.info(f"Loaded routing data from storage")
                
        except Exception as e:
            self.logger.error(f"Error loading routing data: {e}")
            
    def _save_routing_data(self):
        """Save routing data to storage"""
        routing_file = self.log_path.replace('.log', '_routing.json')
        try:
            # Keep only recent decisions (last 1000)
            recent_decisions = self.route_decisions[-1000:] if len(self.route_decisions) > 1000 else self.route_decisions
            
            routing_data = {
                'recent_decisions': [decision.to_dict() for decision in recent_decisions],
                'statistics': self.routing_stats,
                'last_updated': datetime.now().isoformat()
            }
            
            with open(routing_file, 'w') as f:
                json.dump(routing_data, f, indent=4)
                
            # Update in-memory decisions
            self.route_decisions = recent_decisions
            
        except Exception as e:
            self.logger.error(f"Error saving routing data: {e}")
            
    def _get_current_market_session(self) -> str:
        """Determine current market session"""
        try:
            current_time = datetime.now().time()
            sessions = self.config.get("market_sessions", {})
            
            for session_name, session_times in sessions.items():
                start_time = datetime.strptime(session_times["start"], "%H:%M").time()
                end_time = datetime.strptime(session_times["end"], "%H:%M").time()
                
                # Handle sessions that cross midnight
                if start_time > end_time:
                    if current_time >= start_time or current_time <= end_time:
                        return session_name
                else:
                    if start_time <= current_time <= end_time:
                        return session_name
                        
            return "unknown"
            
        except Exception as e:
            self.logger.error(f"Error determining market session: {e}")
            return "unknown"
            
    def _calculate_volatility_score(self, symbol: str) -> float:
        """Calculate volatility score for symbol"""
        try:
            # Simplified volatility calculation
            # In production, this would use actual market data
            volatility_map = {
                "XAUUSD": 2.5,
                "BTCUSD": 3.0,
                "ETHUSD": 2.8,
                "USDZAR": 2.2,
                "USDTRY": 2.0,
                "EURUSD": 1.0,
                "GBPUSD": 1.2,
                "AUDUSD": 1.1,
                "USDCAD": 0.9,
                "USDCHF": 0.8
            }
            
            return volatility_map.get(symbol, 1.0)
            
        except Exception as e:
            self.logger.error(f"Error calculating volatility for {symbol}: {e}")
            return 1.0
            
    def _get_news_impact_level(self, symbol: str) -> str:
        """Get current news impact level for symbol"""
        try:
            # Check with news filter if available
            if 'news_filter' in self.strategy_modules:
                news_filter = self.strategy_modules['news_filter']
                filter_result = news_filter.check_symbol_filter(symbol)
                
                if filter_result.status.value == "blocked_news":
                    if len(filter_result.news_events) > 2:
                        return "high"
                    elif len(filter_result.news_events) > 1:
                        return "medium"
                    else:
                        return "low"
                        
            return "none"
            
        except Exception as e:
            self.logger.error(f"Error getting news impact for {symbol}: {e}")
            return "none"
            
    async def _update_market_state(self):
        """Update current market state"""
        try:
            # Get account information (simplified)
            account_margin_level = 500.0  # Default safe level
            account_equity = 10000.0      # Default account size
            active_positions = 0          # Default no positions
            
            # Calculate symbol activities
            symbol_activity = {}
            symbols = ["EURUSD", "GBPUSD", "XAUUSD", "BTCUSD"]
            for symbol in symbols:
                volatility = self._calculate_volatility_score(symbol)
                symbol_activity[symbol] = volatility
                
            self.market_state = MarketState(
                timestamp=datetime.now(),
                volatility_score=sum(symbol_activity.values()) / len(symbol_activity),
                market_session=self._get_current_market_session(),
                news_impact_level=self._get_news_impact_level("EURUSD"),  # Use major pair as reference
                symbol_activity=symbol_activity,
                account_margin_level=account_margin_level,
                account_equity=account_equity,
                active_positions=active_positions
            )
            
        except Exception as e:
            self.logger.error(f"Error updating market state: {e}")
            
    def _evaluate_condition(self, condition: ConditionRule, signal_data: Dict[str, Any]) -> bool:
        """Evaluate a single condition against signal data and market state"""
        try:
            if not condition.enabled:
                return True  # Disabled conditions always pass
                
            condition_value = None
            
            # Get the value to compare based on condition type
            if condition.condition_type == ConditionType.VOLATILITY:
                if self.market_state:
                    symbol = signal_data.get("symbol", "")
                    condition_value = self.market_state.symbol_activity.get(symbol, 
                                    self.market_state.volatility_score)
                else:
                    condition_value = self._calculate_volatility_score(signal_data.get("symbol", ""))
                    
            elif condition.condition_type == ConditionType.NEWS_EVENTS:
                if self.market_state:
                    condition_value = self.market_state.news_impact_level
                else:
                    condition_value = self._get_news_impact_level(signal_data.get("symbol", ""))
                    
            elif condition.condition_type == ConditionType.SYMBOL_TYPE:
                symbol = signal_data.get("symbol", "")
                symbol_classifications = self.config.get("symbol_classifications", {})
                
                for symbol_type, symbols in symbol_classifications.items():
                    if symbol in symbols:
                        condition_value = symbol_type
                        break
                else:
                    condition_value = "unknown"
                    
            elif condition.condition_type == ConditionType.PROVIDER:
                condition_value = signal_data.get("provider_id", "")
                
            elif condition.condition_type == ConditionType.CONFIDENCE:
                condition_value = signal_data.get("confidence", 0.0)
                
            elif condition.condition_type == ConditionType.VOLUME:
                condition_value = signal_data.get("volume", 0.0)
                
            elif condition.condition_type == ConditionType.MARKET_HOURS:
                if self.market_state:
                    condition_value = self.market_state.market_session
                else:
                    condition_value = self._get_current_market_session()
                    
            elif condition.condition_type == ConditionType.ACCOUNT_STATE:
                if self.market_state:
                    condition_value = self.market_state.account_margin_level
                else:
                    condition_value = 500.0  # Default safe level
                    
            elif condition.condition_type == ConditionType.CUSTOM:
                # Custom condition evaluation (simplified)
                condition_value = 1  # Default value for custom conditions
                
            else:
                return True  # Unknown condition types pass by default
                
            # Evaluate the condition based on operator
            target_value = condition.value
            
            if condition.operator == ConditionOperator.EQUALS:
                return condition_value == target_value
            elif condition.operator == ConditionOperator.NOT_EQUALS:
                return condition_value != target_value
            elif condition.operator == ConditionOperator.GREATER_THAN:
                return float(condition_value) > float(target_value)
            elif condition.operator == ConditionOperator.LESS_THAN:
                return float(condition_value) < float(target_value)
            elif condition.operator == ConditionOperator.GREATER_EQUAL:
                return float(condition_value) >= float(target_value)
            elif condition.operator == ConditionOperator.LESS_EQUAL:
                return float(condition_value) <= float(target_value)
            elif condition.operator == ConditionOperator.CONTAINS:
                return str(target_value) in str(condition_value)
            elif condition.operator == ConditionOperator.NOT_CONTAINS:
                return str(target_value) not in str(condition_value)
            elif condition.operator == ConditionOperator.IN_RANGE:
                if isinstance(target_value, list) and len(target_value) == 2:
                    return target_value[0] <= float(condition_value) <= target_value[1]
            elif condition.operator == ConditionOperator.NOT_IN_RANGE:
                if isinstance(target_value, list) and len(target_value) == 2:
                    return not (target_value[0] <= float(condition_value) <= target_value[1])
                    
            return False
            
        except Exception as e:
            self.logger.error(f"Error evaluating condition {condition.rule_id}: {e}")
            return False
            
    def _evaluate_routing_rule(self, rule: RoutingRule, signal_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Evaluate if a routing rule applies to the signal"""
        try:
            if not rule.enabled:
                return False, []
                
            condition_results = []
            met_conditions = []
            
            for condition in rule.conditions:
                result = self._evaluate_condition(condition, signal_data)
                condition_results.append(result)
                if result:
                    met_conditions.append(condition.name)
                    
            # Apply condition logic
            if rule.condition_logic == "AND":
                rule_applies = all(condition_results)
            elif rule.condition_logic == "OR":
                rule_applies = any(condition_results)
            else:
                # Custom logic evaluation (simplified - just use AND)
                rule_applies = all(condition_results)
                
            return rule_applies, met_conditions
            
        except Exception as e:
            self.logger.error(f"Error evaluating routing rule {rule.rule_id}: {e}")
            return False, []
            
    async def _execute_route_action(self, action: RouteAction, signal_data: Dict[str, Any], 
                                  params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute the routed action on the signal"""
        try:
            if params is None:
                params = {}
                
            if action == RouteAction.PROCESS_NORMAL:
                # Pass through without modification
                return signal_data
                
            elif action == RouteAction.ROUTE_TO_REVERSE:
                # Route to reverse strategy
                if 'reverse_strategy' in self.strategy_modules:
                    reverse_module = self.strategy_modules['reverse_strategy']
                    result = reverse_module.process_signal(signal_data)
                    return result if result is not None else signal_data
                else:
                    self.logger.warning("Reverse strategy module not available")
                    return signal_data
                    
            elif action == RouteAction.ROUTE_TO_GRID:
                # Route to grid strategy (signal would trigger grid creation)
                if 'grid_strategy' in self.strategy_modules:
                    # Grid strategy doesn't process signals directly, 
                    # but we can mark this for grid consideration
                    modified_signal = signal_data.copy()
                    modified_signal['route_suggestion'] = 'grid_strategy'
                    modified_signal['grid_params'] = params
                    return modified_signal
                else:
                    self.logger.warning("Grid strategy module not available")
                    return signal_data
                    
            elif action == RouteAction.ROUTE_TO_MULTI_HANDLER:
                # Route to multi-signal handler
                if 'multi_signal_handler' in self.strategy_modules:
                    multi_handler = self.strategy_modules['multi_signal_handler']
                    success = multi_handler.add_signal(signal_data)
                    if success:
                        # Signal was added to multi-handler, return None to indicate handling
                        return None
                    else:
                        return signal_data
                else:
                    self.logger.warning("Multi-signal handler module not available")
                    return signal_data
                    
            elif action == RouteAction.BLOCK_SIGNAL:
                # Block the signal
                self.logger.info(f"Signal {signal_data.get('signal_id', 'unknown')} blocked by routing rule")
                self.routing_stats["blocked_signals"] += 1
                return None
                
            elif action == RouteAction.DELAY_SIGNAL:
                # Delay signal processing
                delay_minutes = params.get('delay_minutes', 5)
                modified_signal = signal_data.copy()
                modified_signal['process_after'] = (datetime.now() + timedelta(minutes=delay_minutes)).isoformat()
                return modified_signal
                
            elif action == RouteAction.SPLIT_SIGNAL:
                # Split signal into multiple parts
                split_count = params.get('split_count', 2)
                original_volume = signal_data.get('volume', 0.1)
                split_volume = original_volume / split_count
                
                # Return the first split, others would need separate handling
                modified_signal = signal_data.copy()
                modified_signal['volume'] = split_volume
                modified_signal['split_info'] = {
                    'is_split': True,
                    'split_count': split_count,
                    'split_index': 1,
                    'original_volume': original_volume
                }
                return modified_signal
                
            elif action == RouteAction.ESCALATE_PRIORITY:
                # Escalate signal priority
                modified_signal = signal_data.copy()
                current_confidence = modified_signal.get('confidence', 0.5)
                modified_signal['confidence'] = min(1.0, current_confidence + 0.2)
                modified_signal['priority_escalated'] = True
                self.routing_stats["escalated_signals"] += 1
                return modified_signal
                
            else:
                # Unknown action, process normally
                return signal_data
                
        except Exception as e:
            self.logger.error(f"Error executing route action {action.value}: {e}")
            return signal_data
            
    async def route_signal(self, signal_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Route a signal through the condition system"""
        try:
            if not self.config.get("enabled", True):
                return signal_data
                
            signal_id = signal_data.get("signal_id", f"route_{int(datetime.now().timestamp())}")
            
            # Update market state if needed
            if not self.market_state or (datetime.now() - self.market_state.timestamp).total_seconds() > 60:
                await self._update_market_state()
                
            # Find matching routing rule
            matched_rule = None
            met_conditions = []
            
            for rule in self.routing_rules:
                rule_applies, conditions_met = self._evaluate_routing_rule(rule, signal_data)
                if rule_applies:
                    matched_rule = rule
                    met_conditions = conditions_met
                    break
                    
            # Determine action
            if matched_rule:
                target_action = matched_rule.target_action
                target_params = matched_rule.target_params
                
                # Update rule statistics
                matched_rule.last_executed = datetime.now()
                
            else:
                # No rule matched, use default action
                default_action = self.config.get("default_action", "process_normal")
                target_action = RouteAction(default_action)
                target_params = {}
                
            # Execute the routing action
            try:
                result = await self._execute_route_action(target_action, signal_data, target_params)
                
                # Update statistics
                self.routing_stats["total_signals"] += 1
                
                if result is not None:
                    self.routing_stats["successful_routes"] += 1
                    if matched_rule:
                        matched_rule.success_count += 1
                        
                # Record routing decision
                decision = RouteDecision(
                    signal_id=signal_id,
                    original_action=RouteAction.PROCESS_NORMAL,
                    routed_action=target_action,
                    routing_rule=matched_rule,
                    conditions_met=met_conditions,
                    market_state=self.market_state,
                    execution_time=datetime.now(),
                    success=True
                )
                
                self.route_decisions.append(decision)
                
                if matched_rule:
                    self.logger.info(f"Signal {signal_id} routed via rule {matched_rule.name} to action {target_action.value}")
                else:
                    self.logger.info(f"Signal {signal_id} processed with default action {target_action.value}")
                    
                return result
                
            except Exception as e:
                # Route execution failed
                self.routing_stats["failed_routes"] += 1
                if matched_rule:
                    matched_rule.failure_count += 1
                    
                # Record failed decision
                decision = RouteDecision(
                    signal_id=signal_id,
                    original_action=RouteAction.PROCESS_NORMAL,
                    routed_action=target_action,
                    routing_rule=matched_rule,
                    conditions_met=met_conditions,
                    market_state=self.market_state,
                    execution_time=datetime.now(),
                    success=False,
                    error_message=str(e)
                )
                
                self.route_decisions.append(decision)
                
                self.logger.error(f"Failed to execute routing action {target_action.value} for signal {signal_id}: {e}")
                
                # Fallback to default processing if enabled
                if self.config.get("enable_fallback_routing", True):
                    return signal_data
                else:
                    return None
                    
        except Exception as e:
            self.logger.error(f"Error routing signal: {e}")
            return signal_data  # Fallback to original signal
            
    async def _monitor_routing_performance(self):
        """Background task to monitor routing performance"""
        while self.is_monitoring:
            try:
                # Save routing data periodically
                self._save_routing_data()
                
                # Log performance statistics
                if self.routing_stats["total_signals"] > 0:
                    success_rate = (self.routing_stats["successful_routes"] / 
                                  self.routing_stats["total_signals"] * 100)
                    self.logger.info(f"Routing performance: {success_rate:.1f}% success rate, "
                                   f"{self.routing_stats['total_signals']} total signals processed")
                
                await asyncio.sleep(self.config.get("monitoring_interval", 10.0))
                
            except Exception as e:
                self.logger.error(f"Error in routing monitoring loop: {e}")
                await asyncio.sleep(60)  # Prevent tight error loop
                
    def start_monitoring(self):
        """Start background routing monitoring"""
        if not self.config.get('enabled', True):
            self.logger.info("Strategy condition router is disabled")
            return
            
        if not self.is_monitoring:
            self.is_monitoring = True
            try:
                self.monitoring_task = asyncio.create_task(self._monitor_routing_performance())
                self.logger.info("Routing monitoring started")
            except RuntimeError:
                self.is_monitoring = False
                self.logger.warning("No event loop running, cannot start monitoring")
                
    def stop_monitoring(self):
        """Stop background monitoring"""
        if self.is_monitoring:
            self.is_monitoring = False
            if self.monitoring_task:
                self.monitoring_task.cancel()
            self.logger.info("Routing monitoring stopped")
            
    def get_routing_statistics(self) -> Dict[str, Any]:
        """Get routing performance statistics"""
        rule_stats = {}
        for rule in self.routing_rules:
            if rule.success_count > 0 or rule.failure_count > 0:
                total_executions = rule.success_count + rule.failure_count
                success_rate = (rule.success_count / total_executions * 100) if total_executions > 0 else 0
                
                rule_stats[rule.rule_id] = {
                    "name": rule.name,
                    "enabled": rule.enabled,
                    "success_count": rule.success_count,
                    "failure_count": rule.failure_count,
                    "success_rate": success_rate,
                    "last_executed": rule.last_executed.isoformat() if rule.last_executed else None
                }
                
        return {
            **self.routing_stats,
            "active_rules": len([r for r in self.routing_rules if r.enabled]),
            "total_rules": len(self.routing_rules),
            "rule_statistics": rule_stats,
            "monitoring_active": self.is_monitoring,
            "market_state": {
                "volatility_score": self.market_state.volatility_score if self.market_state else 0,
                "market_session": self.market_state.market_session if self.market_state else "unknown",
                "news_impact": self.market_state.news_impact_level if self.market_state else "none",
                "last_updated": self.market_state.timestamp.isoformat() if self.market_state else None
            }
        }
        
    def get_recent_decisions(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent routing decisions"""
        recent = sorted(self.route_decisions, key=lambda x: x.execution_time, reverse=True)[:limit]
        return [decision.to_dict() for decision in recent]
        
    def add_routing_rule(self, rule: RoutingRule) -> bool:
        """Add a new routing rule"""
        try:
            self.routing_rules.append(rule)
            self.routing_rules.sort(key=lambda x: x.priority)
            
            self.logger.info(f"Added routing rule: {rule.name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error adding routing rule: {e}")
            return False
            
    def remove_routing_rule(self, rule_id: str) -> bool:
        """Remove a routing rule by ID"""
        try:
            self.routing_rules = [r for r in self.routing_rules if r.rule_id != rule_id]
            self.logger.info(f"Removed routing rule: {rule_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error removing routing rule: {e}")
            return False

# Global instance for easy access
strategy_condition_router = StrategyConditionRouter()