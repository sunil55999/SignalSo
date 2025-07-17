#!/usr/bin/env python3
"""
Continuous Learning System for SignalOS AI Parser
Implements A/B testing, feedback loops, and automated retraining
"""

import json
import logging
import asyncio
import hashlib
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
import sqlite3
from enum import Enum

from dataset_manager import DatasetManager
from model_trainer import ModelTrainer
from evaluation_metrics import EvaluationEngine

class ABTestStatus(Enum):
    ACTIVE = "active"
    COMPLETED = "completed" 
    PAUSED = "paused"
    FAILED = "failed"

@dataclass
class ABTestConfig:
    """A/B test configuration"""
    test_id: str
    model_a: str
    model_b: str
    traffic_split: float  # 0.0 to 1.0
    duration_hours: int
    success_metric: str
    significance_threshold: float
    min_samples: int

@dataclass
class ABTestResult:
    """A/B test results"""
    test_id: str
    model_a_performance: Dict[str, float]
    model_b_performance: Dict[str, float]
    winner: Optional[str]
    confidence: float
    statistical_significance: bool
    total_samples: int
    duration: float

class ContinuousLearningEngine:
    """Continuous learning and improvement system"""
    
    def __init__(self, models_dir: str = "models", data_dir: str = "data"):
        self.models_dir = Path(models_dir)
        self.data_dir = Path(data_dir)
        self.learning_dir = Path("learning")
        self.learning_dir.mkdir(exist_ok=True)
        
        # Initialize components
        self.dataset_manager = DatasetManager(str(self.data_dir))
        self.model_trainer = ModelTrainer(str(self.models_dir), str(self.data_dir))
        self.evaluation_engine = EvaluationEngine(str(self.models_dir))
        
        # A/B testing database
        self.ab_db = self.learning_dir / "ab_tests.db"
        self._init_ab_database()
        
        # Learning configuration
        self.config = {
            "feedback_threshold": 10,  # Min feedback samples before retraining
            "retraining_schedule": 86400,  # 24 hours
            "performance_threshold": 0.8,
            "ab_test_duration": 48,  # 48 hours
            "traffic_split_default": 0.5,
            "significance_threshold": 0.05
        }
        
        self.logger = logging.getLogger(__name__)
        
        # Active A/B tests
        self.active_tests: Dict[str, ABTestConfig] = {}
        self.model_routing: Dict[str, str] = {}  # user_id -> model_version
    
    def _init_ab_database(self):
        """Initialize A/B testing database"""
        with sqlite3.connect(self.ab_db) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS ab_tests (
                    test_id TEXT PRIMARY KEY,
                    model_a TEXT NOT NULL,
                    model_b TEXT NOT NULL,
                    traffic_split REAL NOT NULL,
                    start_time TEXT NOT NULL,
                    end_time TEXT,
                    status TEXT NOT NULL,
                    config TEXT NOT NULL,
                    results TEXT
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS ab_samples (
                    id TEXT PRIMARY KEY,
                    test_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    model_version TEXT NOT NULL,
                    input_text TEXT NOT NULL,
                    output_result TEXT,
                    performance_score REAL,
                    timestamp TEXT NOT NULL,
                    FOREIGN KEY (test_id) REFERENCES ab_tests (test_id)
                )
            """)
    
    async def start_ab_test(self, model_a: str, model_b: str, 
                           duration_hours: int = 48,
                           traffic_split: float = 0.5,
                           success_metric: str = "accuracy") -> str:
        """Start A/B test between two models"""
        
        test_id = f"ab_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hashlib.md5(f'{model_a}_{model_b}'.encode()).hexdigest()[:8]}"
        
        config = ABTestConfig(
            test_id=test_id,
            model_a=model_a,
            model_b=model_b,
            traffic_split=traffic_split,
            duration_hours=duration_hours,
            success_metric=success_metric,
            significance_threshold=self.config['significance_threshold'],
            min_samples=100
        )
        
        # Store in database
        with sqlite3.connect(self.ab_db) as conn:
            conn.execute("""
                INSERT INTO ab_tests 
                (test_id, model_a, model_b, traffic_split, start_time, status, config)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                test_id, model_a, model_b, traffic_split,
                datetime.now().isoformat(), ABTestStatus.ACTIVE.value,
                json.dumps(asdict(config))
            ))
        
        # Add to active tests
        self.active_tests[test_id] = config
        
        # Schedule automatic completion
        asyncio.create_task(self._schedule_test_completion(test_id, duration_hours))
        
        self.logger.info(f"Started A/B test {test_id}: {model_a} vs {model_b}")
        return test_id
    
    async def _schedule_test_completion(self, test_id: str, duration_hours: int):
        """Schedule automatic A/B test completion"""
        
        await asyncio.sleep(duration_hours * 3600)  # Convert to seconds
        
        if test_id in self.active_tests:
            await self.complete_ab_test(test_id)
    
    def route_request(self, user_id: str, test_id: Optional[str] = None) -> str:
        """Route user request to appropriate model"""
        
        if test_id and test_id in self.active_tests:
            config = self.active_tests[test_id]
            
            # Use consistent routing based on user ID hash
            user_hash = hashlib.md5(user_id.encode()).hexdigest()
            hash_value = int(user_hash[:8], 16) / (16**8)
            
            if hash_value < config.traffic_split:
                model = config.model_a
            else:
                model = config.model_b
            
            # Store routing decision
            self.model_routing[user_id] = model
            
            return model
        else:
            # Default to latest production model
            return self._get_production_model()
    
    def _get_production_model(self) -> str:
        """Get current production model version"""
        
        version_file = self.models_dir / "version.json"
        
        if version_file.exists():
            with open(version_file, 'r') as f:
                version_info = json.load(f)
                return version_info.get("current_version", "default")
        
        return "default"
    
    async def log_ab_sample(self, test_id: str, user_id: str, 
                           input_text: str, output_result: Dict[str, Any],
                           performance_score: float):
        """Log A/B test sample result"""
        
        if test_id not in self.active_tests:
            return
        
        model_version = self.model_routing.get(user_id, "unknown")
        
        sample_id = hashlib.md5(f"{test_id}_{user_id}_{datetime.now().isoformat()}".encode()).hexdigest()
        
        with sqlite3.connect(self.ab_db) as conn:
            conn.execute("""
                INSERT INTO ab_samples 
                (id, test_id, user_id, model_version, input_text, output_result, performance_score, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                sample_id, test_id, user_id, model_version,
                input_text, json.dumps(output_result), performance_score,
                datetime.now().isoformat()
            ))
    
    async def complete_ab_test(self, test_id: str) -> ABTestResult:
        """Complete A/B test and analyze results"""
        
        if test_id not in self.active_tests:
            raise ValueError(f"A/B test {test_id} not found")
        
        config = self.active_tests[test_id]
        
        # Collect results from database
        with sqlite3.connect(self.ab_db) as conn:
            cursor = conn.execute("""
                SELECT model_version, performance_score, timestamp
                FROM ab_samples 
                WHERE test_id = ?
            """, (test_id,))
            
            samples = cursor.fetchall()
        
        if not samples:
            self.logger.warning(f"No samples found for A/B test {test_id}")
            return ABTestResult(
                test_id=test_id,
                model_a_performance={},
                model_b_performance={},
                winner=None,
                confidence=0.0,
                statistical_significance=False,
                total_samples=0,
                duration=0.0
            )
        
        # Analyze results
        model_a_scores = [score for model, score, _ in samples if model == config.model_a]
        model_b_scores = [score for model, score, _ in samples if model == config.model_b]
        
        model_a_performance = self._calculate_performance_metrics(model_a_scores)
        model_b_performance = self._calculate_performance_metrics(model_b_scores)
        
        # Statistical significance test
        significance_result = self._test_statistical_significance(model_a_scores, model_b_scores)
        
        # Determine winner
        winner = None
        if significance_result['significant']:
            if model_a_performance['mean'] > model_b_performance['mean']:
                winner = config.model_a
            else:
                winner = config.model_b
        
        # Calculate test duration
        start_time = datetime.fromisoformat(samples[0][2])
        end_time = datetime.fromisoformat(samples[-1][2])
        duration = (end_time - start_time).total_seconds() / 3600  # Hours
        
        result = ABTestResult(
            test_id=test_id,
            model_a_performance=model_a_performance,
            model_b_performance=model_b_performance,
            winner=winner,
            confidence=significance_result['confidence'],
            statistical_significance=significance_result['significant'],
            total_samples=len(samples),
            duration=duration
        )
        
        # Update database
        with sqlite3.connect(self.ab_db) as conn:
            conn.execute("""
                UPDATE ab_tests 
                SET end_time = ?, status = ?, results = ?
                WHERE test_id = ?
            """, (
                datetime.now().isoformat(),
                ABTestStatus.COMPLETED.value,
                json.dumps(asdict(result)),
                test_id
            ))
        
        # Remove from active tests
        if test_id in self.active_tests:
            del self.active_tests[test_id]
        
        # Auto-deploy winner if significant improvement
        if winner and significance_result['significant']:
            await self._auto_deploy_winner(winner, result)
        
        self.logger.info(f"A/B test {test_id} completed. Winner: {winner}")
        return result
    
    def _calculate_performance_metrics(self, scores: List[float]) -> Dict[str, float]:
        """Calculate performance metrics for a model"""
        
        if not scores:
            return {"mean": 0.0, "std": 0.0, "count": 0}
        
        import statistics
        
        return {
            "mean": statistics.mean(scores),
            "std": statistics.stdev(scores) if len(scores) > 1 else 0.0,
            "count": len(scores),
            "min": min(scores),
            "max": max(scores)
        }
    
    def _test_statistical_significance(self, scores_a: List[float], 
                                     scores_b: List[float]) -> Dict[str, Any]:
        """Test statistical significance between two groups"""
        
        if len(scores_a) < 10 or len(scores_b) < 10:
            return {"significant": False, "confidence": 0.0, "p_value": 1.0}
        
        # Simplified t-test (would use scipy.stats in production)
        import statistics
        
        mean_a = statistics.mean(scores_a)
        mean_b = statistics.mean(scores_b)
        
        # Calculate effect size
        pooled_std = ((statistics.stdev(scores_a)**2 + statistics.stdev(scores_b)**2) / 2) ** 0.5
        effect_size = abs(mean_a - mean_b) / max(pooled_std, 1e-6)
        
        # Mock p-value calculation (replace with proper statistical test)
        p_value = max(0.001, 0.1 / (1 + effect_size * 10))
        
        significant = p_value < self.config['significance_threshold']
        confidence = 1 - p_value
        
        return {
            "significant": significant,
            "confidence": confidence,
            "p_value": p_value,
            "effect_size": effect_size
        }
    
    async def _auto_deploy_winner(self, winning_model: str, result: ABTestResult):
        """Auto-deploy winning model if criteria met"""
        
        # Check if improvement is substantial
        model_a_perf = result.model_a_performance.get('mean', 0.0)
        model_b_perf = result.model_b_performance.get('mean', 0.0)
        
        improvement = abs(model_a_perf - model_b_perf)
        
        if improvement > 0.05:  # 5% improvement threshold
            success = self.model_trainer.deploy_model(winning_model, "production")
            
            if success:
                self.logger.info(f"Auto-deployed winning model {winning_model}")
            else:
                self.logger.error(f"Failed to auto-deploy model {winning_model}")
    
    async def run_feedback_loop(self) -> bool:
        """Run feedback collection and retraining loop"""
        
        try:
            # Import latest feedback
            new_samples = self.dataset_manager.import_feedback_data()
            
            if new_samples >= self.config['feedback_threshold']:
                self.logger.info(f"Processing {new_samples} new feedback samples")
                
                # Clean and prepare dataset
                self.dataset_manager.clean_dataset()
                self.dataset_manager.generate_splits(force_regenerate=True)
                
                # Check dataset quality
                metrics = self.dataset_manager.get_dataset_metrics()
                
                if metrics.quality_score > 0.7:
                    # Trigger retraining
                    await self._trigger_automatic_retraining()
                    return True
                else:
                    self.logger.warning("Dataset quality too low for retraining")
                    return False
            else:
                self.logger.info(f"Insufficient feedback samples ({new_samples} < {self.config['feedback_threshold']})")
                return False
                
        except Exception as e:
            self.logger.error(f"Feedback loop failed: {e}")
            return False
    
    async def _trigger_automatic_retraining(self):
        """Trigger automatic model retraining"""
        
        self.logger.info("Starting automatic retraining...")
        
        try:
            # Export training data
            hf_files = self.dataset_manager.export_training_data("huggingface")
            
            # Train new model
            training_result = self.model_trainer.train_llm_parser(hf_files)
            
            if training_result.success:
                # Evaluate new model against current production
                current_model = self._get_production_model()
                
                # Start A/B test between current and new model
                test_id = await self.start_ab_test(
                    model_a=current_model,
                    model_b=training_result.model_version,
                    duration_hours=24  # Shorter test for automatic retraining
                )
                
                self.logger.info(f"Started automatic A/B test {test_id}")
            else:
                self.logger.error("Automatic retraining failed")
                
        except Exception as e:
            self.logger.error(f"Automatic retraining error: {e}")
    
    def get_learning_status(self) -> Dict[str, Any]:
        """Get comprehensive learning system status"""
        
        # Get active A/B tests
        active_tests = []
        for test_id, config in self.active_tests.items():
            with sqlite3.connect(self.ab_db) as conn:
                cursor = conn.execute("""
                    SELECT COUNT(*) FROM ab_samples WHERE test_id = ?
                """, (test_id,))
                sample_count = cursor.fetchone()[0]
            
            active_tests.append({
                "test_id": test_id,
                "model_a": config.model_a,
                "model_b": config.model_b,
                "duration_remaining": self._calculate_remaining_time(test_id),
                "samples_collected": sample_count
            })
        
        # Get recent feedback
        dataset_metrics = self.dataset_manager.get_dataset_metrics()
        
        # Get training history
        training_status = self.model_trainer.get_training_status()
        
        return {
            "continuous_learning": {
                "active_ab_tests": len(active_tests),
                "ab_test_details": active_tests,
                "feedback_samples": dataset_metrics.total_samples,
                "verified_samples": dataset_metrics.verified_samples,
                "last_retraining": training_status.get("last_training"),
                "dataset_quality": dataset_metrics.quality_score
            },
            "performance_monitoring": {
                "current_model": self._get_production_model(),
                "performance_threshold": self.config['performance_threshold'],
                "retraining_schedule": self.config['retraining_schedule']
            },
            "recommendations": self._generate_learning_recommendations(dataset_metrics)
        }
    
    def _calculate_remaining_time(self, test_id: str) -> float:
        """Calculate remaining time for A/B test"""
        
        if test_id not in self.active_tests:
            return 0.0
        
        config = self.active_tests[test_id]
        
        with sqlite3.connect(self.ab_db) as conn:
            cursor = conn.execute("""
                SELECT start_time FROM ab_tests WHERE test_id = ?
            """, (test_id,))
            
            result = cursor.fetchone()
            if result:
                start_time = datetime.fromisoformat(result[0])
                elapsed = (datetime.now() - start_time).total_seconds() / 3600
                remaining = max(0, config.duration_hours - elapsed)
                return remaining
        
        return 0.0
    
    def _generate_learning_recommendations(self, metrics) -> List[str]:
        """Generate recommendations for continuous learning"""
        
        recommendations = []
        
        if metrics.quality_score < 0.7:
            recommendations.append("Improve dataset quality through better verification")
        
        if metrics.total_samples < 1000:
            recommendations.append("Collect more training samples for better model performance")
        
        if len(self.active_tests) == 0:
            recommendations.append("Consider running A/B tests to evaluate model improvements")
        
        verification_rate = metrics.verified_samples / max(metrics.total_samples, 1)
        if verification_rate < 0.5:
            recommendations.append("Increase sample verification rate for better training quality")
        
        return recommendations
    
    async def cleanup_old_tests(self, days_old: int = 30):
        """Clean up old A/B test data"""
        
        cutoff_date = datetime.now() - timedelta(days=days_old)
        
        with sqlite3.connect(self.ab_db) as conn:
            # Delete old test samples
            conn.execute("""
                DELETE FROM ab_samples 
                WHERE timestamp < ?
            """, (cutoff_date.isoformat(),))
            
            # Delete old completed tests
            conn.execute("""
                DELETE FROM ab_tests 
                WHERE end_time < ? AND status = ?
            """, (cutoff_date.isoformat(), ABTestStatus.COMPLETED.value))
        
        self.logger.info(f"Cleaned up A/B test data older than {days_old} days")
    
    async def export_learning_data(self, output_dir: str):
        """Export learning data for analysis"""
        
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        # Export A/B test results
        with sqlite3.connect(self.ab_db) as conn:
            # Export tests
            cursor = conn.execute("SELECT * FROM ab_tests")
            tests = [dict(zip([col[0] for col in cursor.description], row)) 
                    for row in cursor.fetchall()]
            
            with open(output_path / "ab_tests.json", 'w') as f:
                json.dump(tests, f, indent=2)
            
            # Export samples
            cursor = conn.execute("SELECT * FROM ab_samples")
            samples = [dict(zip([col[0] for col in cursor.description], row)) 
                      for row in cursor.fetchall()]
            
            with open(output_path / "ab_samples.json", 'w') as f:
                json.dump(samples, f, indent=2)
        
        self.logger.info(f"Learning data exported to {output_path}")