"""
Secure Strategy Runtime Engine for SignalOS
Replaces unsafe eval() with secure AST-based expression evaluation
"""

import ast
import operator
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from enum import Enum

# Safe operators allowed in expressions
SAFE_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
    ast.Eq: operator.eq,
    ast.NotEq: operator.ne,
    ast.Lt: operator.lt,
    ast.LtE: operator.le,
    ast.Gt: operator.gt,
    ast.GtE: operator.ge,
    ast.And: lambda x, y: x and y,
    ast.Or: lambda x, y: x or y,
    ast.Not: operator.not_,
}

# Safe functions allowed in expressions
SAFE_FUNCTIONS = {
    'abs': abs,
    'min': min,
    'max': max,
    'round': round,
    'len': len,
    'sum': sum,
    'float': float,
    'int': int,
    'str': str,
    'bool': bool,
}

class SecurityError(Exception):
    """Raised when unsafe operations are detected"""
    pass

class SafeExpressionEvaluator:
    """Secure expression evaluator using AST parsing"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    def evaluate(self, expression: str, context: Optional[Dict[str, Any]] = None) -> Any:
        """
        Safely evaluate a mathematical/logical expression
        
        Args:
            expression: String expression to evaluate
            context: Variables available to the expression
            
        Returns:
            Evaluation result
            
        Raises:
            SecurityError: If unsafe operations detected
            ValueError: If expression is invalid
        """
        if not expression or not isinstance(expression, str):
            raise ValueError("Expression must be a non-empty string")
            
        if len(expression) > 1000:
            raise ValueError("Expression too long (max 1000 characters)")
            
        try:
            # Parse expression into AST
            node = ast.parse(expression, mode='eval')
            
            # Validate AST for security
            self._validate_ast(node)
            
            # Evaluate with controlled context
            return self._eval_node(node.body, context or {})
            
        except SyntaxError as e:
            raise ValueError(f"Invalid expression syntax: {e}")
        except Exception as e:
            self.logger.error(f"Expression evaluation failed: {e}")
            raise
            
    def _validate_ast(self, node: ast.AST) -> None:
        """Validate AST nodes for security violations"""
        for child in ast.walk(node):
            # Block dangerous node types
            if isinstance(child, (ast.Import, ast.ImportFrom, ast.Call)):
                # Only allow whitelisted function calls
                if isinstance(child, ast.Call):
                    if not isinstance(child.func, ast.Name) or child.func.id not in SAFE_FUNCTIONS:
                        raise SecurityError(f"Function call not allowed: {ast.dump(child)}")
                else:
                    raise SecurityError(f"Import statements not allowed: {ast.dump(child)}")
                    
            elif isinstance(child, (ast.Attribute, ast.Subscript)):
                # Block attribute access and subscripting for security
                if isinstance(child, ast.Attribute):
                    # Allow basic attribute access on numbers/strings
                    continue
                else:
                    raise SecurityError(f"Subscript access not allowed: {ast.dump(child)}")
                    
            elif isinstance(child, (ast.Lambda, ast.FunctionDef, ast.ClassDef)):
                raise SecurityError(f"Function/class definitions not allowed: {ast.dump(child)}")
                
            # Note: ast.Exec and ast.Eval were removed in Python 3.8+
            # They're included here for compatibility with older Python versions
                
    def _eval_node(self, node: ast.AST, context: Dict[str, Any]) -> Any:
        """Recursively evaluate AST node"""
        if isinstance(node, ast.Constant):
            return node.value
            
        elif isinstance(node, ast.Name):
            if node.id in context:
                return context[node.id]
            elif node.id in SAFE_FUNCTIONS:
                return SAFE_FUNCTIONS[node.id]
            else:
                raise NameError(f"Variable '{node.id}' not defined")
                
        elif isinstance(node, ast.BinOp):
            left = self._eval_node(node.left, context)
            right = self._eval_node(node.right, context)
            op_type = type(node.op)
            if op_type in SAFE_OPERATORS:
                return SAFE_OPERATORS[op_type](left, right)
            else:
                raise SecurityError(f"Operator not allowed: {op_type}")
                
        elif isinstance(node, ast.UnaryOp):
            operand = self._eval_node(node.operand, context)
            op_type = type(node.op)
            if op_type in SAFE_OPERATORS:
                return SAFE_OPERATORS[op_type](operand)
            else:
                raise SecurityError(f"Unary operator not allowed: {op_type}")
                
        elif isinstance(node, ast.Compare):
            left = self._eval_node(node.left, context)
            result = True
            
            for op, comparator in zip(node.ops, node.comparators):
                right = self._eval_node(comparator, context)
                op_type = type(op)
                if op_type in SAFE_OPERATORS:
                    result = result and SAFE_OPERATORS[op_type](left, right)
                    left = right
                else:
                    raise SecurityError(f"Comparison operator not allowed: {op_type}")
                    
            return result
            
        elif isinstance(node, ast.BoolOp):
            values = [self._eval_node(value, context) for value in node.values]
            
            if isinstance(node.op, ast.And):
                return all(values)
            elif isinstance(node.op, ast.Or):
                return any(values)
            else:
                raise SecurityError(f"Boolean operator not allowed: {type(node.op)}")
                
        elif isinstance(node, ast.Call):
            func_name = node.func.id if isinstance(node.func, ast.Name) else None
            if func_name in SAFE_FUNCTIONS:
                func = SAFE_FUNCTIONS[func_name]
                args = [self._eval_node(arg, context) for arg in node.args]
                return func(*args)
            else:
                raise SecurityError(f"Function call not allowed: {func_name}")
                
        else:
            raise SecurityError(f"AST node type not allowed: {type(node)}")

class SecureStrategyRuntime:
    """Secure strategy runtime using safe expression evaluation"""
    
    def __init__(self, config_file: str = "config.json"):
        self.config_file = config_file
        self.evaluator = SafeExpressionEvaluator()
        self.logger = logging.getLogger(__name__)
        self._load_config()
        
    def _load_config(self):
        """Load configuration safely"""
        try:
            with open(self.config_file, 'r') as f:
                self.config = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            self.logger.warning(f"Config load failed: {e}, using defaults")
            self.config = {"strategy_timeout": 30, "max_expression_length": 1000}
            
    def evaluate_condition(self, condition_expr: str, signal_data: Dict[str, Any]) -> bool:
        """
        Safely evaluate strategy condition
        
        Args:
            condition_expr: Condition expression string
            signal_data: Signal data context
            
        Returns:
            Boolean result of condition evaluation
        """
        try:
            # Prepare secure context
            context = {
                'confidence': signal_data.get('confidence', 0),
                'symbol': signal_data.get('symbol', ''),
                'action': signal_data.get('action', ''),
                'entry': float(signal_data.get('entry', 0)),
                'stop_loss': float(signal_data.get('stop_loss', 0)),
                'take_profit': float(signal_data.get('take_profit', 0)),
                'current_time': datetime.now().hour,
                'current_minute': datetime.now().minute,
            }
            
            # Add safe mathematical constants
            context.update({
                'PI': 3.14159265359,
                'E': 2.71828182846,
            })
            
            result = self.evaluator.evaluate(condition_expr, context)
            return bool(result)
            
        except Exception as e:
            self.logger.error(f"Condition evaluation failed: {e}")
            return False
            
    def apply_action_parameters(self, action_expr: str, signal_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Safely calculate action parameters
        
        Args:
            action_expr: Action parameter expression
            signal_data: Signal data context
            
        Returns:
            Dictionary of calculated parameters
        """
        try:
            context = {
                'lot_size': float(signal_data.get('lot_size', 0.01)),
                'entry': float(signal_data.get('entry', 0)),
                'stop_loss': float(signal_data.get('stop_loss', 0)),
                'take_profit': float(signal_data.get('take_profit', 0)),
                'account_balance': float(signal_data.get('account_balance', 10000)),
                'risk_percent': float(signal_data.get('risk_percent', 2)),
            }
            
            result = self.evaluator.evaluate(action_expr, context)
            
            if isinstance(result, (int, float)):
                return {'calculated_value': float(result)}
            elif isinstance(result, dict):
                return result
            else:
                return {'result': str(result)}
                
        except Exception as e:
            self.logger.error(f"Action parameter calculation failed: {e}")
            return {}

# Global instance
secure_runtime = SecureStrategyRuntime()

def safe_evaluate_expression(expression: str, context: Optional[Dict[str, Any]] = None) -> Any:
    """Global function for safe expression evaluation"""
    return secure_runtime.evaluator.evaluate(expression, context)

def evaluate_strategy_condition(condition: str, signal_data: Dict[str, Any]) -> bool:
    """Global function for strategy condition evaluation"""
    return secure_runtime.evaluate_condition(condition, signal_data)