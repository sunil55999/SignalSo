#!/usr/bin/env python3
"""
Evaluation Metrics for SignalOS AI Parser
Implements comprehensive evaluation and performance monitoring
"""

import json
import logging
import statistics
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, asdict
from collections import defaultdict, Counter
import re

@dataclass
class ParseEvaluation:
    """Individual parse evaluation result"""
    sample_id: str
    raw_text: str
    expected_result: Dict[str, Any]
    predicted_result: Optional[Dict[str, Any]]
    field_scores: Dict[str, float]
    overall_score: float
    parse_time: float
    method_used: str
    errors: List[str]

@dataclass
class EvaluationMetrics:
    """Comprehensive evaluation metrics"""
    accuracy: float
    field_f1_scores: Dict[str, float]
    average_latency: float
    error_breakdown: Dict[str, int]
    confidence_distribution: Dict[str, int]
    method_performance: Dict[str, Dict[str, float]]
    temporal_performance: List[Dict[str, float]]

class EvaluationEngine:
    """Comprehensive evaluation and metrics calculation"""
    
    def __init__(self, models_dir: str = "models", evaluations_dir: str = "evaluations"):
        self.models_dir = Path(models_dir)
        self.evaluations_dir = Path(evaluations_dir)
        self.evaluations_dir.mkdir(exist_ok=True)
        
        self.logger = logging.getLogger(__name__)
        
        # Field importance weights
        self.field_weights = {
            'pair': 0.3,
            'direction': 0.2,
            'entry': 0.2,
            'sl': 0.15,
            'tp': 0.15
        }
        
        # Error categories
        self.error_categories = {
            'parse_failure': 'Complete parsing failure',
            'missing_pair': 'Currency pair not detected',
            'missing_direction': 'Trade direction not detected',
            'missing_entry': 'Entry price not detected',
            'invalid_format': 'Invalid data format',
            'confidence_low': 'Low confidence score',
            'timeout': 'Parse timeout exceeded'
        }
    
    def evaluate_parser_performance(self, test_dataset: str, 
                                  parser_function, 
                                  output_file: Optional[str] = None) -> EvaluationMetrics:
        """Comprehensive parser performance evaluation"""
        
        self.logger.info(f"Starting parser evaluation on {test_dataset}")
        
        # Load test dataset
        test_samples = self._load_test_dataset(test_dataset)
        
        if not test_samples:
            raise ValueError(f"No valid test samples found in {test_dataset}")
        
        # Evaluate each sample
        evaluations = []
        for sample in test_samples:
            eval_result = self._evaluate_single_sample(sample, parser_function)
            evaluations.append(eval_result)
        
        # Calculate comprehensive metrics
        metrics = self._calculate_metrics(evaluations)
        
        # Save detailed results
        if output_file:
            self._save_evaluation_results(evaluations, metrics, output_file)
        
        self.logger.info(f"Evaluation completed: {metrics.accuracy:.3f} accuracy")
        return metrics
    
    def _load_test_dataset(self, dataset_file: str) -> List[Dict[str, Any]]:
        """Load and validate test dataset"""
        
        samples = []
        
        try:
            with open(dataset_file, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    try:
                        sample = json.loads(line.strip())
                        
                        # Validate required fields
                        if 'raw' not in sample or 'parsed' not in sample:
                            self.logger.warning(f"Invalid sample at line {line_num}: missing required fields")
                            continue
                        
                        # Add sample ID if not present
                        if 'id' not in sample:
                            sample['id'] = f"sample_{line_num}"
                        
                        samples.append(sample)
                        
                    except json.JSONDecodeError as e:
                        self.logger.warning(f"JSON decode error at line {line_num}: {e}")
                        continue
                        
        except FileNotFoundError:
            self.logger.error(f"Test dataset file not found: {dataset_file}")
            return []
        except Exception as e:
            self.logger.error(f"Error loading test dataset: {e}")
            return []
        
        self.logger.info(f"Loaded {len(samples)} test samples")
        return samples
    
    def _evaluate_single_sample(self, sample: Dict[str, Any], 
                               parser_function) -> ParseEvaluation:
        """Evaluate parser on a single sample"""
        
        sample_id = sample.get('id', 'unknown')
        raw_text = sample['raw']
        expected_result = sample['parsed']
        
        start_time = datetime.now()
        errors = []
        
        try:
            # Parse the sample
            predicted_result = parser_function(raw_text)
            parse_time = (datetime.now() - start_time).total_seconds()
            
            if predicted_result is None:
                errors.append('parse_failure')
                predicted_result = {}
            
            # Calculate field-level scores
            field_scores = self._calculate_field_scores(expected_result, predicted_result)
            
            # Calculate overall score
            overall_score = self._calculate_overall_score(field_scores)
            
            # Determine method used
            method_used = predicted_result.get('parser_method', 'unknown')
            
        except Exception as e:
            parse_time = (datetime.now() - start_time).total_seconds()
            predicted_result = {}
            field_scores = {field: 0.0 for field in self.field_weights.keys()}
            overall_score = 0.0
            method_used = 'error'
            errors.append(f'exception: {str(e)}')
        
        return ParseEvaluation(
            sample_id=sample_id,
            raw_text=raw_text,
            expected_result=expected_result,
            predicted_result=predicted_result,
            field_scores=field_scores,
            overall_score=overall_score,
            parse_time=parse_time,
            method_used=method_used,
            errors=errors
        )
    
    def _calculate_field_scores(self, expected: Dict[str, Any], 
                               predicted: Dict[str, Any]) -> Dict[str, float]:
        """Calculate accuracy scores for individual fields"""
        
        field_scores = {}
        
        for field in self.field_weights.keys():
            expected_value = expected.get(field)
            predicted_value = predicted.get(field)
            
            if expected_value is None:
                # Field not in expected result
                field_scores[field] = 1.0 if predicted_value is None else 0.5
            elif predicted_value is None:
                # Field missing in prediction
                field_scores[field] = 0.0
            else:
                # Both values present, calculate similarity
                field_scores[field] = self._calculate_field_similarity(
                    expected_value, predicted_value, field
                )
        
        return field_scores
    
    def _calculate_field_similarity(self, expected: Any, predicted: Any, 
                                   field_type: str) -> float:
        """Calculate similarity between expected and predicted field values"""
        
        if field_type == 'pair':
            return self._compare_currency_pairs(expected, predicted)
        elif field_type == 'direction':
            return self._compare_directions(expected, predicted)
        elif field_type in ['entry', 'sl', 'tp']:
            return self._compare_numeric_values(expected, predicted, field_type)
        else:
            # Generic string comparison
            return 1.0 if str(expected).lower() == str(predicted).lower() else 0.0
    
    def _compare_currency_pairs(self, expected: str, predicted: str) -> float:
        """Compare currency pair strings"""
        
        # Normalize pairs (remove common suffixes)
        def normalize_pair(pair):
            pair = str(pair).upper().replace('/', '').replace('_', '')
            # Remove common broker suffixes
            for suffix in ['M', 'PRO', 'ECN', '.', '-']:
                pair = pair.replace(suffix, '')
            return pair
        
        exp_norm = normalize_pair(expected)
        pred_norm = normalize_pair(predicted)
        
        return 1.0 if exp_norm == pred_norm else 0.0
    
    def _compare_directions(self, expected: str, predicted: str) -> float:
        """Compare trade directions"""
        
        direction_map = {
            'buy': ['buy', 'long', 'bull', 'شراء'],
            'sell': ['sell', 'short', 'bear', 'بيع']
        }
        
        exp_str = str(expected).lower()
        pred_str = str(predicted).lower()
        
        # Find expected direction category
        exp_category = None
        for category, variations in direction_map.items():
            if any(var in exp_str for var in variations):
                exp_category = category
                break
        
        # Find predicted direction category
        pred_category = None
        for category, variations in direction_map.items():
            if any(var in pred_str for var in variations):
                pred_category = category
                break
        
        return 1.0 if exp_category == pred_category else 0.0
    
    def _compare_numeric_values(self, expected: Union[float, List[float]], 
                               predicted: Union[float, List[float]], 
                               field_type: str) -> float:
        """Compare numeric values with tolerance"""
        
        # Convert to lists for uniform handling
        exp_values = expected if isinstance(expected, list) else [expected]
        pred_values = predicted if isinstance(predicted, list) else [predicted]
        
        # Filter out None values and convert to float
        exp_nums = []
        pred_nums = []
        
        for val in exp_values:
            if val is not None:
                try:
                    exp_nums.append(float(val))
                except (ValueError, TypeError):
                    pass
        
        for val in pred_values:
            if val is not None:
                try:
                    pred_nums.append(float(val))
                except (ValueError, TypeError):
                    pass
        
        if not exp_nums and not pred_nums:
            return 1.0  # Both empty
        
        if not exp_nums or not pred_nums:
            return 0.0  # One empty, one not
        
        # For single values, check if they're close
        if len(exp_nums) == 1 and len(pred_nums) == 1:
            tolerance = 0.01  # 1% tolerance
            exp_val = exp_nums[0]
            pred_val = pred_nums[0]
            
            if abs(exp_val - pred_val) / max(abs(exp_val), 1e-6) <= tolerance:
                return 1.0
            else:
                return 0.0
        
        # For lists, calculate overlap score
        matches = 0
        tolerance = 0.01
        
        for exp_val in exp_nums:
            for pred_val in pred_nums:
                if abs(exp_val - pred_val) / max(abs(exp_val), 1e-6) <= tolerance:
                    matches += 1
                    break
        
        return matches / max(len(exp_nums), len(pred_nums))
    
    def _calculate_overall_score(self, field_scores: Dict[str, float]) -> float:
        """Calculate weighted overall score"""
        
        weighted_sum = 0.0
        total_weight = 0.0
        
        for field, score in field_scores.items():
            weight = self.field_weights.get(field, 0.1)
            weighted_sum += score * weight
            total_weight += weight
        
        return weighted_sum / max(total_weight, 1e-6)
    
    def _calculate_metrics(self, evaluations: List[ParseEvaluation]) -> EvaluationMetrics:
        """Calculate comprehensive evaluation metrics"""
        
        if not evaluations:
            return EvaluationMetrics(
                accuracy=0.0,
                field_f1_scores={},
                average_latency=0.0,
                error_breakdown={},
                confidence_distribution={},
                method_performance={},
                temporal_performance=[]
            )
        
        # Overall accuracy
        accuracy = statistics.mean([eval.overall_score for eval in evaluations])
        
        # Field-level F1 scores
        field_f1_scores = {}
        for field in self.field_weights.keys():
            field_scores = [eval.field_scores.get(field, 0.0) for eval in evaluations]
            field_f1_scores[field] = statistics.mean(field_scores)
        
        # Average latency
        latencies = [eval.parse_time for eval in evaluations]
        average_latency = statistics.mean(latencies)
        
        # Error breakdown
        error_breakdown = defaultdict(int)
        for eval in evaluations:
            if eval.errors:
                for error in eval.errors:
                    error_type = error.split(':')[0]  # Get error category
                    error_breakdown[error_type] += 1
            else:
                error_breakdown['no_error'] += 1
        
        # Confidence distribution (mock implementation)
        confidence_distribution = {
            'high': sum(1 for eval in evaluations if eval.overall_score > 0.8),
            'medium': sum(1 for eval in evaluations if 0.5 <= eval.overall_score <= 0.8),
            'low': sum(1 for eval in evaluations if eval.overall_score < 0.5)
        }
        
        # Method performance
        method_performance = defaultdict(lambda: {'count': 0, 'accuracy': 0.0})
        for eval in evaluations:
            method = eval.method_used
            method_performance[method]['count'] += 1
            method_performance[method]['accuracy'] += eval.overall_score
        
        # Calculate average accuracy per method
        for method, stats in method_performance.items():
            if stats['count'] > 0:
                stats['accuracy'] /= stats['count']
        
        # Temporal performance (hourly breakdown)
        temporal_performance = self._calculate_temporal_performance(evaluations)
        
        return EvaluationMetrics(
            accuracy=accuracy,
            field_f1_scores=field_f1_scores,
            average_latency=average_latency,
            error_breakdown=dict(error_breakdown),
            confidence_distribution=confidence_distribution,
            method_performance=dict(method_performance),
            temporal_performance=temporal_performance
        )
    
    def _calculate_temporal_performance(self, evaluations: List[ParseEvaluation]) -> List[Dict[str, float]]:
        """Calculate performance over time periods"""
        
        # Group by time periods (simplified - would use actual timestamps in production)
        periods = []
        
        # Split evaluations into time buckets
        bucket_size = max(1, len(evaluations) // 10)  # 10 time periods
        
        for i in range(0, len(evaluations), bucket_size):
            bucket = evaluations[i:i + bucket_size]
            if bucket:
                period_accuracy = statistics.mean([eval.overall_score for eval in bucket])
                period_latency = statistics.mean([eval.parse_time for eval in bucket])
                
                periods.append({
                    'period': i // bucket_size,
                    'accuracy': period_accuracy,
                    'latency': period_latency,
                    'samples': len(bucket)
                })
        
        return periods
    
    def _save_evaluation_results(self, evaluations: List[ParseEvaluation], 
                               metrics: EvaluationMetrics, 
                               output_file: str):
        """Save detailed evaluation results"""
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = self.evaluations_dir / f"{output_file}_{timestamp}.json"
        
        results = {
            "evaluation_metadata": {
                "timestamp": datetime.now().isoformat(),
                "total_samples": len(evaluations),
                "evaluation_version": "1.0"
            },
            "summary_metrics": asdict(metrics),
            "detailed_results": [asdict(eval) for eval in evaluations],
            "analysis": self._generate_analysis(evaluations, metrics)
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"Evaluation results saved to {output_path}")
    
    def _generate_analysis(self, evaluations: List[ParseEvaluation], 
                          metrics: EvaluationMetrics) -> Dict[str, Any]:
        """Generate detailed analysis and recommendations"""
        
        analysis = {
            "performance_summary": {
                "overall_grade": self._grade_performance(metrics.accuracy),
                "strengths": [],
                "weaknesses": [],
                "recommendations": []
            },
            "error_analysis": self._analyze_errors(evaluations),
            "field_analysis": self._analyze_fields(evaluations),
            "method_analysis": self._analyze_methods(evaluations)
        }
        
        # Identify strengths and weaknesses
        if metrics.accuracy > 0.9:
            analysis["performance_summary"]["strengths"].append("Excellent overall accuracy")
        elif metrics.accuracy > 0.8:
            analysis["performance_summary"]["strengths"].append("Good overall accuracy")
        else:
            analysis["performance_summary"]["weaknesses"].append("Low overall accuracy needs improvement")
        
        if metrics.average_latency < 0.1:
            analysis["performance_summary"]["strengths"].append("Fast parsing speed")
        elif metrics.average_latency > 1.0:
            analysis["performance_summary"]["weaknesses"].append("Slow parsing speed")
        
        # Generate recommendations
        if metrics.accuracy < 0.8:
            analysis["performance_summary"]["recommendations"].append("Consider retraining with more diverse data")
        
        if metrics.average_latency > 0.5:
            analysis["performance_summary"]["recommendations"].append("Optimize parsing algorithms for speed")
        
        return analysis
    
    def _grade_performance(self, accuracy: float) -> str:
        """Grade performance based on accuracy"""
        
        if accuracy >= 0.95:
            return "A+ (Excellent)"
        elif accuracy >= 0.9:
            return "A (Very Good)"
        elif accuracy >= 0.8:
            return "B (Good)"
        elif accuracy >= 0.7:
            return "C (Fair)"
        elif accuracy >= 0.6:
            return "D (Poor)"
        else:
            return "F (Failing)"
    
    def _analyze_errors(self, evaluations: List[ParseEvaluation]) -> Dict[str, Any]:
        """Analyze error patterns"""
        
        error_patterns = defaultdict(list)
        
        for eval in evaluations:
            if eval.errors:
                for error in eval.errors:
                    error_patterns[error].append({
                        "sample_id": eval.sample_id,
                        "raw_text": eval.raw_text[:100],  # First 100 chars
                        "score": eval.overall_score
                    })
        
        return {
            "common_errors": dict(error_patterns),
            "error_rate": len([e for e in evaluations if e.errors]) / len(evaluations),
            "most_problematic": self._find_problematic_samples(evaluations)
        }
    
    def _analyze_fields(self, evaluations: List[ParseEvaluation]) -> Dict[str, Any]:
        """Analyze field-level performance"""
        
        field_analysis = {}
        
        for field in self.field_weights.keys():
            field_scores = [eval.field_scores.get(field, 0.0) for eval in evaluations]
            
            field_analysis[field] = {
                "average_score": statistics.mean(field_scores),
                "success_rate": sum(1 for score in field_scores if score > 0.5) / len(field_scores),
                "perfect_rate": sum(1 for score in field_scores if score == 1.0) / len(field_scores)
            }
        
        return field_analysis
    
    def _analyze_methods(self, evaluations: List[ParseEvaluation]) -> Dict[str, Any]:
        """Analyze parsing method performance"""
        
        method_stats = defaultdict(lambda: {
            'samples': 0,
            'total_score': 0.0,
            'total_time': 0.0,
            'errors': 0
        })
        
        for eval in evaluations:
            method = eval.method_used
            method_stats[method]['samples'] += 1
            method_stats[method]['total_score'] += eval.overall_score
            method_stats[method]['total_time'] += eval.parse_time
            if eval.errors:
                method_stats[method]['errors'] += 1
        
        # Calculate averages
        method_analysis = {}
        for method, stats in method_stats.items():
            if stats['samples'] > 0:
                method_analysis[method] = {
                    'accuracy': stats['total_score'] / stats['samples'],
                    'average_latency': stats['total_time'] / stats['samples'],
                    'error_rate': stats['errors'] / stats['samples'],
                    'usage_rate': stats['samples'] / len(evaluations)
                }
        
        return method_analysis
    
    def _find_problematic_samples(self, evaluations: List[ParseEvaluation]) -> List[Dict[str, Any]]:
        """Find most problematic samples for analysis"""
        
        # Sort by score (lowest first)
        sorted_evals = sorted(evaluations, key=lambda x: x.overall_score)
        
        problematic = []
        for eval in sorted_evals[:10]:  # Top 10 worst
            problematic.append({
                "sample_id": eval.sample_id,
                "raw_text": eval.raw_text,
                "score": eval.overall_score,
                "errors": eval.errors,
                "expected": eval.expected_result,
                "predicted": eval.predicted_result
            })
        
        return problematic
    
    def run_continuous_evaluation(self, parser_function, 
                                 test_dataset: str, 
                                 threshold: float = 0.8) -> Dict[str, Any]:
        """Run continuous evaluation and alert on performance degradation"""
        
        try:
            # Run evaluation
            metrics = self.evaluate_parser_performance(test_dataset, parser_function)
            
            # Check performance threshold
            performance_alert = {
                "timestamp": datetime.now().isoformat(),
                "accuracy": metrics.accuracy,
                "threshold": threshold,
                "status": "pass" if metrics.accuracy >= threshold else "fail",
                "latency": metrics.average_latency,
                "recommendations": []
            }
            
            if metrics.accuracy < threshold:
                performance_alert["recommendations"].append("Performance below threshold - consider retraining")
            
            if metrics.average_latency > 1.0:
                performance_alert["recommendations"].append("High latency detected - optimize parsing speed")
            
            # Log performance alert
            alert_file = self.evaluations_dir / "performance_alerts.jsonl"
            with open(alert_file, 'a') as f:
                f.write(json.dumps(performance_alert) + '\n')
            
            return performance_alert
            
        except Exception as e:
            self.logger.error(f"Continuous evaluation failed: {e}")
            return {"status": "error", "message": str(e)}