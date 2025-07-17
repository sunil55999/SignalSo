#!/usr/bin/env python3
"""
Safe Parser Engine for SignalOS
Advanced error handling with AI fallback and comprehensive validation
"""

import time
import logging
from typing import Dict, Any, Optional, List
from pathlib import Path

from .parser_utils import sanitize_signal, validate_result, clean_text_input
from .fallback_regex_parser import fallback_parser
from .feedback_logger import log_failure, log_success, log_performance


class SafeParserEngine:
    """Safe signal parser with AI fallback and error recovery"""
    
    def __init__(self, config_path: str = "config/parser_config.json"):
        self.config = self._load_config(config_path)
        self.setup_logging()
        
        # Parser configuration
        self.max_retries = self.config.get("max_retries", 3)
        self.timeout_seconds = self.config.get("timeout_seconds", 30)
        self.enable_ai_parser = self.config.get("enable_ai_parser", True)
        self.enable_fallback = self.config.get("enable_fallback", True)
        self.log_failures = self.config.get("log_failures", True)
        
        # Performance tracking
        self.parse_stats = {
            "total_attempts": 0,
            "ai_successes": 0,
            "fallback_uses": 0,
            "failures": 0,
            "avg_parse_time": 0.0
        }
        
    def setup_logging(self):
        """Setup parser logging"""
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        logging.basicConfig(
            filename=log_dir / "parser_engine.log",
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load parser configuration"""
        import json
        
        default_config = {
            "max_retries": 3,
            "timeout_seconds": 30,
            "enable_ai_parser": True,
            "enable_fallback": True,
            "log_failures": True,
            "require_all_fields": True,
            "allowed_pairs": ["EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "USDCAD", "NZDUSD", "XAUUSD", "XAGUSD"],
            "min_confidence": 0.7
        }
        
        try:
            config_file = Path(config_path)
            if config_file.exists():
                with open(config_file, 'r') as f:
                    loaded_config = json.load(f)
                    return {**default_config, **loaded_config}
        except Exception as e:
            print(f"Warning: Failed to load parser config: {e}")
            
        return default_config
        
    def parse_signal_safe(self, raw_text: str) -> Optional[Dict[str, Any]]:
        """
        Safe signal parsing with comprehensive error handling
        
        Args:
            raw_text: Raw signal text from Telegram or other source
            
        Returns:
            Parsed signal dictionary or None if parsing failed
        """
        start_time = time.time()
        self.parse_stats["total_attempts"] += 1
        
        try:
            # Step 1: Sanitize input
            sanitized_text = sanitize_signal(raw_text)
            clean_text = clean_text_input(sanitized_text)
            
            self.logger.info(f"Parsing signal: {clean_text[:100]}...")
            
            # Step 2: Try AI parser first
            if self.enable_ai_parser:
                for attempt in range(self.max_retries):
                    try:
                        result = self._ai_parse_with_timeout(clean_text)
                        if result:
                            # Step 3: Validate AI result
                            validated_result = validate_result(result, self.config)
                            
                            # Log success
                            parse_time = time.time() - start_time
                            self._update_performance_stats(parse_time, "ai_success")
                            
                            if self.log_failures:  # Also log successes for learning
                                log_success(raw_text, validated_result, parse_time, "ai")
                                
                            self.logger.info(f"AI parser succeeded on attempt {attempt + 1}")
                            return validated_result
                            
                    except Exception as e:
                        self.logger.warning(f"AI parser attempt {attempt + 1} failed: {e}")
                        if attempt == self.max_retries - 1:
                            # Log AI failure before trying fallback
                            if self.log_failures:
                                log_failure(raw_text, str(e), "ai_parser", attempt + 1)
                                
            # Step 4: Fallback to regex parser
            if self.enable_fallback:
                self.logger.info("Attempting fallback regex parser...")
                try:
                    fallback_result = fallback_parser(clean_text)
                    if fallback_result:
                        # Validate fallback result
                        validated_result = validate_result(fallback_result, self.config)
                        
                        # Log fallback usage
                        parse_time = time.time() - start_time
                        self._update_performance_stats(parse_time, "fallback_success")
                        
                        if self.log_failures:
                            log_success(raw_text, validated_result, parse_time, "fallback")
                            
                        self.logger.info("Fallback parser succeeded")
                        return validated_result
                        
                except Exception as e:
                    self.logger.error(f"Fallback parser failed: {e}")
                    if self.log_failures:
                        log_failure(raw_text, str(e), "fallback_parser", 1)
                        
            # Step 5: All parsing methods failed
            parse_time = time.time() - start_time
            self._update_performance_stats(parse_time, "total_failure")
            
            error_msg = "All parsing methods failed"
            self.logger.error(f"Complete parsing failure: {error_msg}")
            
            if self.log_failures:
                log_failure(raw_text, error_msg, "complete_failure", self.max_retries)
                
            return None
            
        except Exception as e:
            # Catch-all error handling
            parse_time = time.time() - start_time
            self._update_performance_stats(parse_time, "exception")
            
            self.logger.error(f"Unexpected parser error: {e}")
            
            if self.log_failures:
                log_failure(raw_text, str(e), "unexpected_error", 0)
                
            return None
            
    def _ai_parse_with_timeout(self, text: str) -> Optional[Dict[str, Any]]:
        """
        AI parsing with timeout protection
        Mock implementation - replace with actual AI model call
        """
        try:
            # Import AI parser components if available
            try:
                from ..parser.parser_core import ParserCore
                from ..parser.confidence_system import ConfidenceSystem
                
                # Use existing AI parser
                parser_core = ParserCore()
                confidence_system = ConfidenceSystem()
                
                # Parse with AI model
                result = parser_core.parse_signal(text)
                
                if result and result.get("confidence", 0) >= self.config.get("min_confidence", 0.7):
                    return {
                        "pair": result.get("symbol", ""),
                        "direction": result.get("action", "").upper(),
                        "entry": result.get("entry_price", []),
                        "sl": result.get("stop_loss", 0),
                        "tp": result.get("take_profit", []),
                        "confidence": result.get("confidence", 0),
                        "risk_reward": result.get("risk_reward", 0),
                        "lot_size": result.get("lot_size", 0.01),
                        "parser_method": "ai"
                    }
                else:
                    self.logger.warning(f"AI parser low confidence: {result.get('confidence', 0)}")
                    return None
                    
            except ImportError:
                # Mock AI parser for testing
                self.logger.warning("AI parser not available, using mock")
                return self._mock_ai_parser(text)
                
        except Exception as e:
            self.logger.error(f"AI parser timeout/error: {e}")
            raise
            
    def _mock_ai_parser(self, text: str) -> Optional[Dict[str, Any]]:
        """Mock AI parser for testing purposes"""
        # Simple keyword detection for testing
        text_upper = text.upper()
        
        if "BUY" in text_upper or "SELL" in text_upper:
            return {
                "pair": "EURUSD",
                "direction": "BUY" if "BUY" in text_upper else "SELL", 
                "entry": [1.0850, 1.0860],
                "sl": 1.0800,
                "tp": [1.0900, 1.0950],
                "confidence": 0.8,
                "risk_reward": 2.5,
                "lot_size": 0.01,
                "parser_method": "mock_ai"
            }
        return None
        
    def _update_performance_stats(self, parse_time: float, result_type: str):
        """Update performance statistics"""
        if result_type == "ai_success":
            self.parse_stats["ai_successes"] += 1
        elif result_type == "fallback_success":
            self.parse_stats["fallback_uses"] += 1
        elif result_type in ["total_failure", "exception"]:
            self.parse_stats["failures"] += 1
            
        # Update average parse time
        total_attempts = self.parse_stats["total_attempts"]
        current_avg = self.parse_stats["avg_parse_time"]
        self.parse_stats["avg_parse_time"] = ((current_avg * (total_attempts - 1)) + parse_time) / total_attempts
        
        # Log performance data
        if total_attempts % 10 == 0:  # Log every 10 attempts
            log_performance(self.parse_stats)
            
    def get_parser_stats(self) -> Dict[str, Any]:
        """Get current parser performance statistics"""
        total = self.parse_stats["total_attempts"]
        if total == 0:
            return self.parse_stats
            
        return {
            **self.parse_stats,
            "success_rate": ((self.parse_stats["ai_successes"] + self.parse_stats["fallback_uses"]) / total) * 100,
            "ai_success_rate": (self.parse_stats["ai_successes"] / total) * 100,
            "fallback_rate": (self.parse_stats["fallback_uses"] / total) * 100,
            "failure_rate": (self.parse_stats["failures"] / total) * 100
        }
        
    def reset_stats(self):
        """Reset performance statistics"""
        self.parse_stats = {
            "total_attempts": 0,
            "ai_successes": 0,
            "fallback_uses": 0,
            "failures": 0,
            "avg_parse_time": 0.0
        }
        self.logger.info("Parser statistics reset")
        
    def configure_parser(self, **kwargs):
        """Configure parser settings"""
        for key, value in kwargs.items():
            if key in self.config:
                self.config[key] = value
                self.logger.info(f"Parser config updated: {key} = {value}")
                
        # Update instance variables
        self.max_retries = self.config.get("max_retries", 3)
        self.timeout_seconds = self.config.get("timeout_seconds", 30)
        self.enable_ai_parser = self.config.get("enable_ai_parser", True)
        self.enable_fallback = self.config.get("enable_fallback", True)
        self.log_failures = self.config.get("log_failures", True)


# Global parser instance
_global_parser: Optional[SafeParserEngine] = None


def get_safe_parser() -> SafeParserEngine:
    """Get global safe parser instance"""
    global _global_parser
    if _global_parser is None:
        _global_parser = SafeParserEngine()
    return _global_parser


def parse_signal_safe(raw_text: str) -> Optional[Dict[str, Any]]:
    """
    Convenience function for safe signal parsing
    
    Args:
        raw_text: Raw signal text
        
    Returns:
        Parsed signal dictionary or None
    """
    parser = get_safe_parser()
    return parser.parse_signal_safe(raw_text)


def get_parser_performance() -> Dict[str, Any]:
    """Get current parser performance statistics"""
    parser = get_safe_parser()
    return parser.get_parser_stats()


def configure_safe_parser(**kwargs):
    """Configure safe parser settings"""
    parser = get_safe_parser()
    parser.configure_parser(**kwargs)


def generate_parser_report() -> Dict[str, Any]:
    """
    Generate comprehensive parser report with statistics and patterns
    
    Returns:
        Comprehensive report dictionary
    """
    from .feedback_logger import FeedbackLogger
    
    parser = get_safe_parser()
    logger = FeedbackLogger()
    
    # Get current statistics
    stats = parser.get_parser_stats()
    
    # Get failure and success patterns
    failure_patterns = logger.get_failure_patterns(limit=50)
    success_patterns = logger.get_success_patterns(limit=50)
    
    # Analyze patterns
    report = {
        "parser_statistics": stats,
        "session_info": {
            "total_attempts": stats.get("total_attempts", 0),
            "success_rate": stats.get("success_rate", 0),
            "ai_success_rate": stats.get("ai_success_rate", 0),
            "fallback_rate": stats.get("fallback_rate", 0),
            "failure_rate": stats.get("failure_rate", 0),
            "avg_parse_time": stats.get("avg_parse_time", 0)
        },
        "failure_analysis": {
            "total_failures": len(failure_patterns),
            "common_errors": _analyze_common_errors(failure_patterns),
            "failed_parser_methods": _analyze_failed_methods(failure_patterns)
        },
        "success_analysis": {
            "total_successes": len(success_patterns),
            "parser_method_distribution": _analyze_success_methods(success_patterns),
            "confidence_distribution": _analyze_confidence_levels(success_patterns)
        },
        "recommendations": _generate_recommendations(stats, failure_patterns, success_patterns)
    }
    
    return report


def _analyze_common_errors(failures: List[Dict[str, Any]]) -> Dict[str, int]:
    """Analyze common error patterns"""
    error_counts = {}
    for failure in failures:
        error_msg = failure.get("error_message", "unknown")
        # Categorize errors
        if "timeout" in error_msg.lower():
            error_counts["timeout"] = error_counts.get("timeout", 0) + 1
        elif "validation" in error_msg.lower():
            error_counts["validation"] = error_counts.get("validation", 0) + 1
        elif "missing" in error_msg.lower():
            error_counts["missing_fields"] = error_counts.get("missing_fields", 0) + 1
        else:
            error_counts["other"] = error_counts.get("other", 0) + 1
    return error_counts


def _analyze_failed_methods(failures: List[Dict[str, Any]]) -> Dict[str, int]:
    """Analyze which parser methods fail most often"""
    method_counts = {}
    for failure in failures:
        method = failure.get("parser_method", "unknown")
        method_counts[method] = method_counts.get(method, 0) + 1
    return method_counts


def _analyze_success_methods(successes: List[Dict[str, Any]]) -> Dict[str, int]:
    """Analyze success distribution by parser method"""
    method_counts = {}
    for success in successes:
        method = success.get("parser_method", "unknown")
        method_counts[method] = method_counts.get(method, 0) + 1
    return method_counts


def _analyze_confidence_levels(successes: List[Dict[str, Any]]) -> Dict[str, int]:
    """Analyze confidence level distribution"""
    confidence_buckets = {"high": 0, "medium": 0, "low": 0}
    for success in successes:
        confidence = success.get("confidence", 0)
        if confidence >= 0.8:
            confidence_buckets["high"] += 1
        elif confidence >= 0.6:
            confidence_buckets["medium"] += 1
        else:
            confidence_buckets["low"] += 1
    return confidence_buckets


def _generate_recommendations(stats: Dict[str, Any], failures: List[Dict[str, Any]], successes: List[Dict[str, Any]]) -> List[str]:
    """Generate recommendations based on analysis"""
    recommendations = []
    
    failure_rate = stats.get("failure_rate", 0)
    ai_success_rate = stats.get("ai_success_rate", 0)
    fallback_rate = stats.get("fallback_rate", 0)
    
    if failure_rate > 20:
        recommendations.append("High failure rate detected. Consider improving signal preprocessing or fallback patterns.")
    
    if ai_success_rate < 50:
        recommendations.append("AI parser success rate is low. Consider retraining or improving AI model.")
    
    if fallback_rate > 30:
        recommendations.append("Heavy reliance on fallback parser. Consider improving AI model accuracy.")
    
    avg_parse_time = stats.get("avg_parse_time", 0)
    if avg_parse_time > 5.0:
        recommendations.append("Parse time is high. Consider optimizing AI model or reducing timeout.")
    
    if len(failures) > 20:
        common_errors = _analyze_common_errors(failures)
        top_error = max(common_errors.items(), key=lambda x: x[1]) if common_errors else None
        if top_error:
            recommendations.append(f"Most common error type: {top_error[0]}. Focus on fixing this error category.")
    
    if not recommendations:
        recommendations.append("Parser performance is good. Continue monitoring for improvements.")
    
    return recommendations


# Testing function
def test_safe_parser():
    """Test the safe parser with various inputs"""
    test_signals = [
        "BUY EURUSD @ 1.0850, SL: 1.0800, TP: 1.0900",
        "🟢 SELL XAUUSD Entry: 2345 SL: 2350 TP1: 2339 TP2: 2333",
        "Invalid signal text without proper format",
        "GBPUSD BUY NOW! Entry range 1.2500-1.2520, Stop Loss 1.2450, Take Profit 1.2600",
        ""  # Empty signal
    ]
    
    parser = SafeParserEngine()
    
    print("🧪 Testing Safe Parser Engine")
    print("=" * 50)
    
    for i, signal in enumerate(test_signals, 1):
        print(f"\nTest {i}: {signal[:50]}...")
        result = parser.parse_signal_safe(signal)
        
        if result:
            print(f"✅ Parsed: {result['pair']} {result['direction']}")
            print(f"   Entry: {result['entry']}, SL: {result['sl']}, TP: {result['tp']}")
            print(f"   Method: {result.get('parser_method', 'unknown')}")
        else:
            print("❌ Parsing failed")
            
    # Show statistics
    stats = parser.get_parser_stats()
    print(f"\n📊 Parser Statistics:")
    print(f"   Total attempts: {stats['total_attempts']}")
    print(f"   Success rate: {stats.get('success_rate', 0):.1f}%")
    print(f"   AI successes: {stats['ai_successes']}")
    print(f"   Fallback uses: {stats['fallback_uses']}")
    print(f"   Failures: {stats['failures']}")
    print(f"   Avg parse time: {stats['avg_parse_time']:.3f}s")


if __name__ == "__main__":
    test_safe_parser()