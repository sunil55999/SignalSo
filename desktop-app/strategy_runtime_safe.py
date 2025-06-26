"""
Safe Strategy Runtime for SignalOS Desktop App
Replaces unsafe eval() usage with secure expression evaluation
"""

import ast
import operator
import logging
from typing import Any, Dict, Union, List
from dataclasses import dataclass

# Fix #1: Safe expression evaluator to replace eval()
class SafeExpressionEvaluator:
    """
    Secure expression evaluator that prevents code injection
    Replaces dangerous eval() calls with controlled AST evaluation
    """
    
    # Allowed operators for safe evaluation
    SAFE_OPERATORS = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
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
        ast.And: operator.and_,
        ast.Or: operator.or_,
        ast.Not: operator.not_,
    }
    
    # Allowed builtin functions
    SAFE_FUNCTIONS = {
        'abs': abs,
        'min': min,
        'max': max,
        'round': round,
        'float': float,
        'int': int,
        'bool': bool,
        'str': str,
        'len': len,
    }
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def evaluate_expression(self, expression: str, context: Dict[str, Any] = None) -> Any:
        """
        Safely evaluate a mathematical or logical expression
        
        Args:
            expression: The expression string to evaluate
            context: Variables available in the expression context
            
        Returns:
            The result of the expression evaluation
            
        Raises:
            ValueError: If expression contains unsafe operations
            SyntaxError: If expression has invalid syntax
        """
        if context is None:
            context = {}
            
        try:
            # Parse the expression into an AST
            tree = ast.parse(expression, mode='eval')
            
            # Validate the AST for safety
            self._validate_ast(tree)
            
            # Evaluate the expression
            return self._evaluate_node(tree.body, context)
            
        except (SyntaxError, ValueError) as e:
            self.logger.error(f"Expression evaluation failed: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error in expression evaluation: {e}")
            raise ValueError(f"Expression evaluation error: {str(e)}")
    
    def _validate_ast(self, tree: ast.AST) -> None:
        """Validate that the AST only contains safe operations"""
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if not isinstance(node.func, ast.Name):
                    raise ValueError("Only simple function calls are allowed")
                if node.func.id not in self.SAFE_FUNCTIONS:
                    raise ValueError(f"Function '{node.func.id}' is not allowed")
            elif isinstance(node, (ast.Import, ast.ImportFrom, ast.Exec, ast.Global)):
                raise ValueError("Import and exec statements are not allowed")
            elif isinstance(node, ast.Attribute):
                raise ValueError("Attribute access is not allowed")
    
    def _evaluate_node(self, node: ast.AST, context: Dict[str, Any]) -> Any:
        """Recursively evaluate AST nodes"""
        if isinstance(node, ast.Constant):
            return node.value
        elif isinstance(node, ast.Name):
            if node.id in context:
                return context[node.id]
            elif node.id in self.SAFE_FUNCTIONS:
                return self.SAFE_FUNCTIONS[node.id]
            else:
                raise ValueError(f"Undefined variable: {node.id}")
        elif isinstance(node, ast.BinOp):
            left = self._evaluate_node(node.left, context)
            right = self._evaluate_node(node.right, context)
            op = self.SAFE_OPERATORS.get(type(node.op))
            if op is None:
                raise ValueError(f"Operator {type(node.op).__name__} is not allowed")
            return op(left, right)
        elif isinstance(node, ast.UnaryOp):
            operand = self._evaluate_node(node.operand, context)
            op = self.SAFE_OPERATORS.get(type(node.op))
            if op is None:
                raise ValueError(f"Unary operator {type(node.op).__name__} is not allowed")
            return op(operand)
        elif isinstance(node, ast.Compare):
            left = self._evaluate_node(node.left, context)
            result = left
            for op, comparator in zip(node.ops, node.comparators):
                right = self._evaluate_node(comparator, context)
                op_func = self.SAFE_OPERATORS.get(type(op))
                if op_func is None:
                    raise ValueError(f"Comparison operator {type(op).__name__} is not allowed")
                result = op_func(result, right)
                if not result:
                    break
            return result
        elif isinstance(node, ast.BoolOp):
            values = [self._evaluate_node(value, context) for value in node.values]
            op = self.SAFE_OPERATORS.get(type(node.op))
            if op is None:
                raise ValueError(f"Boolean operator {type(node.op).__name__} is not allowed")
            if isinstance(node.op, ast.And):
                return all(values)
            elif isinstance(node.op, ast.Or):
                return any(values)
        elif isinstance(node, ast.Call):
            func_name = node.func.id
            if func_name not in self.SAFE_FUNCTIONS:
                raise ValueError(f"Function '{func_name}' is not allowed")
            func = self.SAFE_FUNCTIONS[func_name]
            args = [self._evaluate_node(arg, context) for arg in node.args]
            return func(*args)
        else:
            raise ValueError(f"AST node type {type(node).__name__} is not allowed")

@dataclass
class StrategyContext:
    """Context variables available to strategy expressions"""
    signal_data: Dict[str, Any]
    market_data: Dict[str, Any]
    account_info: Dict[str, Any]
    current_time: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for expression evaluation"""
        return {
            'signal': self.signal_data,
            'market': self.market_data,
            'account': self.account_info,
            'time': self.current_time,
            # Add common trading variables
            'balance': self.account_info.get('balance', 0),
            'equity': self.account_info.get('equity', 0),
            'margin': self.account_info.get('margin', 0),
            'price': self.signal_data.get('entry_price', 0),
            'sl': self.signal_data.get('stop_loss', 0),
            'tp': self.signal_data.get('take_profit', 0),
        }

class SecureStrategyRuntime:
    """
    Secure strategy runtime that replaces dangerous eval() usage
    """
    
    def __init__(self):
        self.evaluator = SafeExpressionEvaluator()
        self.logger = logging.getLogger(__name__)
    
    def execute_strategy_condition(self, condition: str, context: StrategyContext) -> bool:
        """
        Safely execute a strategy condition
        
        Args:
            condition: Strategy condition expression
            context: Strategy execution context
            
        Returns:
            Boolean result of the condition evaluation
        """
        try:
            context_dict = context.to_dict()
            result = self.evaluator.evaluate_expression(condition, context_dict)
            
            # Ensure result is boolean
            if not isinstance(result, bool):
                result = bool(result)
                
            self.logger.debug(f"Strategy condition '{condition}' evaluated to: {result}")
            return result
            
        except Exception as e:
            self.logger.error(f"Strategy condition evaluation failed: {e}")
            # Fail safely - reject the signal if condition evaluation fails
            return False
    
    def calculate_position_size(self, formula: str, context: StrategyContext) -> float:
        """
        Safely calculate position size using a formula
        
        Args:
            formula: Position size calculation formula
            context: Strategy execution context
            
        Returns:
            Calculated position size
        """
        try:
            context_dict = context.to_dict()
            result = self.evaluator.evaluate_expression(formula, context_dict)
            
            # Ensure result is numeric and positive
            if not isinstance(result, (int, float)):
                raise ValueError(f"Position size formula must return a number, got {type(result)}")
            
            if result <= 0:
                raise ValueError("Position size must be positive")
                
            self.logger.debug(f"Position size formula '{formula}' calculated: {result}")
            return float(result)
            
        except Exception as e:
            self.logger.error(f"Position size calculation failed: {e}")
            # Return minimal position size as fallback
            return 0.01

# Global instance for use throughout the application
safe_strategy_runtime = SecureStrategyRuntime()

def evaluate_strategy_safely(expression: str, signal_data: Dict, market_data: Dict, account_info: Dict) -> Any:
    """
    Global function to safely evaluate strategy expressions
    Replaces any dangerous eval() calls in the codebase
    """
    import time
    
    context = StrategyContext(
        signal_data=signal_data,
        market_data=market_data,
        account_info=account_info,
        current_time=time.time()
    )
    
    return safe_strategy_runtime.execute_strategy_condition(expression, context)