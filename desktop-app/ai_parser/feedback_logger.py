#!/usr/bin/env python3
"""
Feedback Logger for SignalOS Parser
Tracks parsing failures and successes for continuous improvement
"""

import json
import logging
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict


@dataclass
class ParseAttempt:
    """Data structure for a parsing attempt"""
    timestamp: str
    raw_signal: str
    signal_hash: str
    parser_method: str
    success: bool
    result: Optional[Dict[str, Any]]
    error_message: Optional[str]
    parse_time: float
    retry_count: int
    confidence: float


class FeedbackLogger:
    """Logger for tracking parser performance and failures"""
    
    def __init__(self, log_dir: str = "logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        # Log files
        self.failures_log = self.log_dir / "failures.log"
        self.success_log = self.log_dir / "successes.log"
        self.performance_log = self.log_dir / "performance.log"
        self.detailed_log = self.log_dir / "parsing_attempts.jsonl"
        
        self.setup_logging()
        
        # Performance tracking
        self.session_stats = {
            "total_attempts": 0,
            "successes": 0,
            "failures": 0,
            "ai_successes": 0,
            "fallback_successes": 0,
            "total_parse_time": 0.0,
            "session_start": datetime.now().isoformat()
        }
        
    def setup_logging(self):
        """Setup logging configuration"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
    def _hash_signal(self, raw_signal: str) -> str:
        """Create hash of raw signal for deduplication"""
        return hashlib.md5(raw_signal.encode('utf-8')).hexdigest()[:16]
        
    def log_failure(self, raw_signal: str, error: str, parser_method: str, retry_count: int = 1):
        """
        Log a parsing failure
        
        Args:
            raw_signal: Original signal text
            error: Error message
            parser_method: Which parser failed (ai_parser, fallback_parser, etc.)
            retry_count: Number of retries attempted
        """
        try:
            timestamp = datetime.now().isoformat()
            signal_hash = self._hash_signal(raw_signal)
            
            # Update session stats
            self.session_stats["total_attempts"] += 1
            self.session_stats["failures"] += 1
            
            # Log to failures file
            with open(self.failures_log, 'a', encoding='utf-8') as f:
                f.write(f"[{timestamp}] FAILURE\n")
                f.write(f"Hash: {signal_hash}\n")
                f.write(f"Parser: {parser_method}\n") 
                f.write(f"Retries: {retry_count}\n")
                f.write(f"Error: {error}\n")
                f.write(f"Signal: {raw_signal}\n")
                f.write("-" * 80 + "\n")
                
            # Log detailed JSON record
            attempt = ParseAttempt(
                timestamp=timestamp,
                raw_signal=raw_signal,
                signal_hash=signal_hash,
                parser_method=parser_method,
                success=False,
                result=None,
                error_message=error,
                parse_time=0.0,
                retry_count=retry_count,
                confidence=0.0
            )
            
            self._log_detailed_attempt(attempt)
            
            self.logger.warning(f"Parse failure logged: {parser_method} - {error[:100]}")
            
        except Exception as e:
            self.logger.error(f"Failed to log parsing failure: {e}")
            
    def log_success(self, raw_signal: str, result: Dict[str, Any], parse_time: float, parser_method: str):
        """
        Log a successful parsing attempt
        
        Args:
            raw_signal: Original signal text
            result: Parsed result dictionary
            parse_time: Time taken to parse (seconds)
            parser_method: Which parser succeeded
        """
        try:
            timestamp = datetime.now().isoformat()
            signal_hash = self._hash_signal(raw_signal)
            confidence = result.get("confidence", 1.0)
            
            # Update session stats
            self.session_stats["total_attempts"] += 1
            self.session_stats["successes"] += 1
            self.session_stats["total_parse_time"] += parse_time
            
            if parser_method in ["ai", "ai_parser", "mock_ai"]:
                self.session_stats["ai_successes"] += 1
            elif "fallback" in parser_method:
                self.session_stats["fallback_successes"] += 1
                
            # Log to success file
            with open(self.success_log, 'a', encoding='utf-8') as f:
                f.write(f"[{timestamp}] SUCCESS\n")
                f.write(f"Hash: {signal_hash}\n")
                f.write(f"Parser: {parser_method}\n")
                f.write(f"Time: {parse_time:.3f}s\n")
                f.write(f"Confidence: {confidence:.2f}\n")
                f.write(f"Pair: {result.get('pair', 'Unknown')}\n")
                f.write(f"Direction: {result.get('direction', 'Unknown')}\n")
                f.write(f"Signal: {raw_signal}\n")
                f.write("-" * 80 + "\n")
                
            # Log detailed JSON record
            attempt = ParseAttempt(
                timestamp=timestamp,
                raw_signal=raw_signal,
                signal_hash=signal_hash,
                parser_method=parser_method,
                success=True,
                result=result,
                error_message=None,
                parse_time=parse_time,
                retry_count=1,
                confidence=confidence
            )
            
            self._log_detailed_attempt(attempt)
            
            self.logger.info(f"Parse success logged: {parser_method} - {result.get('pair', 'Unknown')} {result.get('direction', 'Unknown')}")
            
        except Exception as e:
            self.logger.error(f"Failed to log parsing success: {e}")
            
    def log_performance(self, performance_stats: Dict[str, Any]):
        """
        Log performance statistics
        
        Args:
            performance_stats: Dictionary of performance metrics
        """
        try:
            timestamp = datetime.now().isoformat()
            
            with open(self.performance_log, 'a', encoding='utf-8') as f:
                f.write(f"[{timestamp}] PERFORMANCE STATS\n")
                f.write(json.dumps(performance_stats, indent=2))
                f.write("\n" + "-" * 80 + "\n")
                
            self.logger.info("Performance stats logged")
            
        except Exception as e:
            self.logger.error(f"Failed to log performance: {e}")
            
    def _log_detailed_attempt(self, attempt: ParseAttempt):
        """Log detailed attempt data as JSON Lines"""
        try:
            with open(self.detailed_log, 'a', encoding='utf-8') as f:
                json_line = json.dumps(asdict(attempt), ensure_ascii=False)
                f.write(json_line + "\n")
                
        except Exception as e:
            self.logger.error(f"Failed to log detailed attempt: {e}")
            
    def get_failure_patterns(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Analyze recent failures to identify patterns
        
        Args:
            limit: Maximum number of recent failures to analyze
            
        Returns:
            List of failure analysis results
        """
        try:
            failures = []
            
            if not self.detailed_log.exists():
                return failures
                
            with open(self.detailed_log, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
            # Get recent failures
            recent_lines = lines[-limit:] if len(lines) > limit else lines
            
            for line in recent_lines:
                try:
                    attempt = json.loads(line.strip())
                    if not attempt.get("success", True):
                        failures.append(attempt)
                except json.JSONDecodeError:
                    continue
                    
            return failures
            
        except Exception as e:
            self.logger.error(f"Failed to analyze failure patterns: {e}")
            return []
            
    def get_success_patterns(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Analyze recent successes to identify patterns
        
        Args:
            limit: Maximum number of recent successes to analyze
            
        Returns:
            List of success analysis results
        """
        try:
            successes = []
            
            if not self.detailed_log.exists():
                return successes
                
            with open(self.detailed_log, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
            # Get recent successes
            recent_lines = lines[-limit:] if len(lines) > limit else lines
            
            for line in recent_lines:
                try:
                    attempt = json.loads(line.strip())
                    if attempt.get("success", False):
                        successes.append(attempt)
                except json.JSONDecodeError:
                    continue
                    
            return successes
            
        except Exception as e:
            self.logger.error(f"Failed to analyze success patterns: {e}")
            return []
            
    def generate_feedback_report(self) -> Dict[str, Any]:
        """
        Generate comprehensive feedback report
        
        Returns:
            Dictionary containing analysis and recommendations
        """
        try:
            # Get recent patterns
            failures = self.get_failure_patterns(50)
            successes = self.get_success_patterns(50)
            
            # Analyze failure patterns
            failure_analysis = self._analyze_failures(failures)
            success_analysis = self._analyze_successes(successes)
            
            # Calculate session statistics
            total_attempts = self.session_stats["total_attempts"]
            success_rate = (self.session_stats["successes"] / total_attempts * 100) if total_attempts > 0 else 0
            avg_parse_time = (self.session_stats["total_parse_time"] / self.session_stats["successes"]) if self.session_stats["successes"] > 0 else 0
            
            report = {
                "timestamp": datetime.now().isoformat(),
                "session_stats": {
                    **self.session_stats,
                    "success_rate": success_rate,
                    "avg_parse_time": avg_parse_time
                },
                "failure_analysis": failure_analysis,
                "success_analysis": success_analysis,
                "recommendations": self._generate_recommendations(failure_analysis, success_analysis)
            }
            
            return report
            
        except Exception as e:
            self.logger.error(f"Failed to generate feedback report: {e}")
            return {"error": str(e)}
            
    def _analyze_failures(self, failures: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze failure patterns"""
        if not failures:
            return {"total_failures": 0}
            
        # Count by parser method
        parser_failures = {}
        error_types = {}
        common_signals = {}
        
        for failure in failures:
            parser = failure.get("parser_method", "unknown")
            parser_failures[parser] = parser_failures.get(parser, 0) + 1
            
            error = failure.get("error_message", "unknown")
            error_types[error[:50]] = error_types.get(error[:50], 0) + 1
            
            signal_hash = failure.get("signal_hash", "unknown")
            common_signals[signal_hash] = common_signals.get(signal_hash, 0) + 1
            
        return {
            "total_failures": len(failures),
            "parser_failures": parser_failures,
            "common_errors": dict(sorted(error_types.items(), key=lambda x: x[1], reverse=True)[:5]),
            "repeated_failures": dict(sorted(common_signals.items(), key=lambda x: x[1], reverse=True)[:5])
        }
        
    def _analyze_successes(self, successes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze success patterns"""
        if not successes:
            return {"total_successes": 0}
            
        # Count by parser method
        parser_successes = {}
        confidence_levels = []
        parse_times = []
        
        for success in successes:
            parser = success.get("parser_method", "unknown")
            parser_successes[parser] = parser_successes.get(parser, 0) + 1
            
            confidence = success.get("confidence", 0)
            confidence_levels.append(confidence)
            
            parse_time = success.get("parse_time", 0)
            parse_times.append(parse_time)
            
        avg_confidence = sum(confidence_levels) / len(confidence_levels) if confidence_levels else 0
        avg_parse_time = sum(parse_times) / len(parse_times) if parse_times else 0
        
        return {
            "total_successes": len(successes),
            "parser_successes": parser_successes,
            "avg_confidence": avg_confidence,
            "avg_parse_time": avg_parse_time
        }
        
    def _generate_recommendations(self, failure_analysis: Dict[str, Any], success_analysis: Dict[str, Any]) -> List[str]:
        """Generate improvement recommendations based on analysis"""
        recommendations = []
        
        # Analyze parser performance
        total_failures = failure_analysis.get("total_failures", 0)
        total_successes = success_analysis.get("total_successes", 0)
        
        if total_failures > total_successes:
            recommendations.append("Consider improving AI model training with recent failure examples")
            
        # Check confidence levels
        avg_confidence = success_analysis.get("avg_confidence", 1.0)
        if avg_confidence < 0.8:
            recommendations.append("Low average confidence detected - review AI model parameters")
            
        # Check parse times
        avg_parse_time = success_analysis.get("avg_parse_time", 0)
        if avg_parse_time > 2.0:
            recommendations.append("Parse times are high - consider optimizing AI model or timeout settings")
            
        # Check repeated failures
        repeated_failures = failure_analysis.get("repeated_failures", {})
        if repeated_failures:
            recommendations.append("Some signals are consistently failing - add specific patterns to regex fallback")
            
        # Check fallback usage
        parser_successes = success_analysis.get("parser_successes", {})
        fallback_count = sum(count for parser, count in parser_successes.items() if "fallback" in parser)
        ai_count = sum(count for parser, count in parser_successes.items() if "ai" in parser or "mock" in parser)
        
        if fallback_count > ai_count:
            recommendations.append("Fallback parser is used more than AI - consider retraining or updating AI model")
            
        if not recommendations:
            recommendations.append("Parser performance is optimal - continue monitoring")
            
        return recommendations
        
    def export_training_data(self, output_file: str = "parser_training_data.json") -> bool:
        """
        Export parsing attempts as training data for AI model improvement
        
        Args:
            output_file: Output file path
            
        Returns:
            True if successful
        """
        try:
            if not self.detailed_log.exists():
                return False
                
            training_data = []
            
            with open(self.detailed_log, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        attempt = json.loads(line.strip())
                        
                        # Format for training
                        training_example = {
                            "input": attempt["raw_signal"],
                            "output": attempt["result"] if attempt["success"] else None,
                            "success": attempt["success"],
                            "confidence": attempt["confidence"],
                            "parser_method": attempt["parser_method"]
                        }
                        
                        training_data.append(training_example)
                        
                    except json.JSONDecodeError:
                        continue
                        
            # Save training data
            output_path = self.log_dir / output_file
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(training_data, f, indent=2, ensure_ascii=False)
                
            self.logger.info(f"Training data exported: {output_path} ({len(training_data)} examples)")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to export training data: {e}")
            return False


# Global logger instance
_global_logger: Optional[FeedbackLogger] = None


def get_feedback_logger() -> FeedbackLogger:
    """Get global feedback logger instance"""
    global _global_logger
    if _global_logger is None:
        _global_logger = FeedbackLogger()
    return _global_logger


def log_failure(raw_signal: str, error: str, parser_method: str, retry_count: int = 1):
    """Convenience function to log parsing failure"""
    logger = get_feedback_logger()
    logger.log_failure(raw_signal, error, parser_method, retry_count)


def log_success(raw_signal: str, result: Dict[str, Any], parse_time: float, parser_method: str):
    """Convenience function to log parsing success"""
    logger = get_feedback_logger()
    logger.log_success(raw_signal, result, parse_time, parser_method)


def log_performance(stats: Dict[str, Any]):
    """Convenience function to log performance statistics"""
    logger = get_feedback_logger()
    logger.log_performance(stats)


def generate_parser_report() -> Dict[str, Any]:
    """Generate comprehensive parser feedback report"""
    logger = get_feedback_logger()
    return logger.generate_feedback_report()


# Testing function
def test_feedback_logger():
    """Test feedback logging functionality"""
    print("📊 Testing Feedback Logger")
    print("=" * 40)
    
    logger = FeedbackLogger()
    
    # Test logging failures
    logger.log_failure(
        "Invalid signal text",
        "No trading pair found",
        "ai_parser",
        2
    )
    
    # Test logging successes
    test_result = {
        "pair": "EURUSD",
        "direction": "BUY",
        "entry": [1.0850],
        "sl": 1.0800,
        "tp": [1.0900],
        "confidence": 0.85
    }
    
    logger.log_success(
        "BUY EURUSD @ 1.0850, SL: 1.0800, TP: 1.0900",
        test_result,
        0.245,
        "ai_parser"
    )
    
    # Generate report
    report = logger.generate_feedback_report()
    print(f"Report generated: {len(report)} sections")
    print(f"Session stats: {report.get('session_stats', {})}")
    print(f"Recommendations: {len(report.get('recommendations', []))}")
    
    # Export training data
    success = logger.export_training_data("test_training_data.json")
    print(f"Training data export: {'✅' if success else '❌'}")
    
    print("✅ Feedback logger testing complete")


if __name__ == "__main__":
    test_feedback_logger()