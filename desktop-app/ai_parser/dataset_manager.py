#!/usr/bin/env python3
"""
Dataset Manager for SignalOS AI Parser Fine-Tuning
Implements comprehensive dataset preparation, management, and versioning
"""

import json
import logging
import hashlib
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from collections import Counter, defaultdict
import sqlite3

@dataclass
class DatasetSample:
    """Individual dataset sample structure"""
    id: str
    raw_text: str
    parsed_data: Dict[str, Any]
    provider: str
    language: str
    format_type: str
    confidence: float
    timestamp: datetime
    verified: bool = False
    correction_count: int = 0
    
@dataclass
class DatasetMetrics:
    """Dataset quality metrics"""
    total_samples: int
    verified_samples: int
    provider_distribution: Dict[str, int]
    language_distribution: Dict[str, int]
    format_distribution: Dict[str, int]
    quality_score: float
    coverage_score: float

class DatasetManager:
    """Comprehensive dataset management for AI parser training"""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
        # Dataset files
        self.raw_dataset = self.data_dir / "raw_signals.jsonl"
        self.train_dataset = self.data_dir / "train.jsonl"
        self.validation_dataset = self.data_dir / "validation.jsonl"
        self.test_dataset = self.data_dir / "test.jsonl"
        self.feedback_dataset = self.data_dir / "feedback.jsonl"
        
        # Database for efficient management
        self.db_path = self.data_dir / "dataset.db"
        self._init_database()
        
        # Configuration
        self.config = {
            "train_split": 0.8,
            "validation_split": 0.1,
            "test_split": 0.1,
            "min_samples_per_provider": 50,
            "quality_threshold": 0.85,
            "deduplication_threshold": 0.9
        }
        
        self.logger = logging.getLogger(__name__)
        
    def _init_database(self):
        """Initialize SQLite database for dataset management"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS samples (
                    id TEXT PRIMARY KEY,
                    raw_text TEXT NOT NULL,
                    parsed_data TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    language TEXT NOT NULL,
                    format_type TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    timestamp TEXT NOT NULL,
                    verified BOOLEAN DEFAULT FALSE,
                    correction_count INTEGER DEFAULT 0,
                    hash TEXT NOT NULL,
                    split_assignment TEXT
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS corrections (
                    id TEXT PRIMARY KEY,
                    sample_id TEXT NOT NULL,
                    original_parsed TEXT NOT NULL,
                    corrected_parsed TEXT NOT NULL,
                    correction_timestamp TEXT NOT NULL,
                    corrector_id TEXT,
                    FOREIGN KEY (sample_id) REFERENCES samples (id)
                )
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_provider ON samples (provider)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_language ON samples (language)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_hash ON samples (hash)
            """)
    
    def add_sample(self, raw_text: str, parsed_data: Dict[str, Any], 
                   provider: str, language: str = "en", 
                   format_type: str = "standard", confidence: float = 1.0) -> str:
        """Add a new sample to the dataset"""
        
        # Generate unique ID and hash
        sample_id = hashlib.md5(f"{raw_text}{datetime.now().isoformat()}".encode()).hexdigest()
        text_hash = hashlib.md5(raw_text.encode()).hexdigest()
        
        # Check for duplicates
        if self._is_duplicate(text_hash):
            self.logger.warning(f"Duplicate sample detected: {raw_text[:50]}...")
            return None
        
        sample = DatasetSample(
            id=sample_id,
            raw_text=raw_text,
            parsed_data=parsed_data,
            provider=provider,
            language=language,
            format_type=format_type,
            confidence=confidence,
            timestamp=datetime.now()
        )
        
        # Store in database
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO samples 
                (id, raw_text, parsed_data, provider, language, format_type, 
                 confidence, timestamp, hash)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                sample.id, sample.raw_text, json.dumps(sample.parsed_data),
                sample.provider, sample.language, sample.format_type,
                sample.confidence, sample.timestamp.isoformat(), text_hash
            ))
        
        self.logger.info(f"Added sample {sample_id} from {provider}")
        return sample_id
    
    def _is_duplicate(self, text_hash: str) -> bool:
        """Check if sample is duplicate based on text similarity"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM samples WHERE hash = ?", (text_hash,))
            return cursor.fetchone()[0] > 0
    
    def add_correction(self, sample_id: str, corrected_parsed: Dict[str, Any], 
                      corrector_id: str = "system") -> bool:
        """Add correction for an existing sample"""
        
        with sqlite3.connect(self.db_path) as conn:
            # Get original parsed data
            cursor = conn.execute(
                "SELECT parsed_data FROM samples WHERE id = ?", (sample_id,)
            )
            row = cursor.fetchone()
            if not row:
                self.logger.error(f"Sample {sample_id} not found")
                return False
            
            original_parsed = row[0]
            
            # Add correction record
            correction_id = hashlib.md5(f"{sample_id}{datetime.now().isoformat()}".encode()).hexdigest()
            conn.execute("""
                INSERT INTO corrections 
                (id, sample_id, original_parsed, corrected_parsed, correction_timestamp, corrector_id)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                correction_id, sample_id, original_parsed, 
                json.dumps(corrected_parsed), datetime.now().isoformat(), corrector_id
            ))
            
            # Update sample with correction
            conn.execute("""
                UPDATE samples 
                SET parsed_data = ?, correction_count = correction_count + 1, verified = TRUE
                WHERE id = ?
            """, (json.dumps(corrected_parsed), sample_id))
        
        self.logger.info(f"Added correction for sample {sample_id}")
        return True
    
    def import_feedback_data(self, feedback_file: Optional[str] = None) -> int:
        """Import feedback data from parser failures"""
        feedback_path = Path(feedback_file) if feedback_file else self.feedback_dataset
        
        if not feedback_path.exists():
            self.logger.warning(f"Feedback file not found: {feedback_path}")
            return 0
        
        imported_count = 0
        
        try:
            with open(feedback_path, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        feedback_entry = json.loads(line.strip())
                        
                        # Extract relevant information
                        raw_text = feedback_entry.get('raw_text', '')
                        provider = feedback_entry.get('provider', 'unknown')
                        language = feedback_entry.get('language', 'en')
                        
                        # Create parsed data from feedback
                        parsed_data = feedback_entry.get('corrected_parse')
                        if not parsed_data:
                            # Use failed parse as starting point
                            parsed_data = feedback_entry.get('failed_parse', {})
                        
                        if raw_text and parsed_data:
                            sample_id = self.add_sample(
                                raw_text=raw_text,
                                parsed_data=parsed_data,
                                provider=provider,
                                language=language,
                                format_type="feedback",
                                confidence=0.8  # Lower confidence for feedback samples
                            )
                            
                            if sample_id:
                                imported_count += 1
                                
                    except json.JSONDecodeError:
                        continue
                    except Exception as e:
                        self.logger.error(f"Error importing feedback entry: {e}")
                        continue
        
        except Exception as e:
            self.logger.error(f"Error reading feedback file: {e}")
        
        self.logger.info(f"Imported {imported_count} samples from feedback data")
        return imported_count
    
    def generate_splits(self, force_regenerate: bool = False) -> bool:
        """Generate train/validation/test splits"""
        
        if not force_regenerate and self._splits_exist():
            self.logger.info("Splits already exist. Use force_regenerate=True to recreate.")
            return True
        
        # Get all samples
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT id, provider, language, format_type, verified 
                FROM samples 
                ORDER BY timestamp
            """)
            samples = cursor.fetchall()
        
        if len(samples) < 100:
            self.logger.error("Insufficient samples for split generation (minimum 100 required)")
            return False
        
        # Stratified split by provider and language
        stratified_samples = self._stratified_split(samples)
        
        # Assign splits
        train_samples = stratified_samples['train']
        val_samples = stratified_samples['validation']
        test_samples = stratified_samples['test']
        
        # Update database with split assignments
        with sqlite3.connect(self.db_path) as conn:
            for sample_id in train_samples:
                conn.execute("UPDATE samples SET split_assignment = 'train' WHERE id = ?", (sample_id,))
            for sample_id in val_samples:
                conn.execute("UPDATE samples SET split_assignment = 'validation' WHERE id = ?", (sample_id,))
            for sample_id in test_samples:
                conn.execute("UPDATE samples SET split_assignment = 'test' WHERE id = ?", (sample_id,))
        
        # Export to JSONL files
        self._export_split_files()
        
        self.logger.info(f"Generated splits: Train={len(train_samples)}, Val={len(val_samples)}, Test={len(test_samples)}")
        return True
    
    def _stratified_split(self, samples: List[Tuple]) -> Dict[str, List[str]]:
        """Create stratified splits maintaining distribution"""
        
        # Group by provider and language
        groups = defaultdict(list)
        for sample_id, provider, language, format_type, verified in samples:
            key = f"{provider}_{language}"
            groups[key].append(sample_id)
        
        train_samples = []
        val_samples = []
        test_samples = []
        
        for group_samples in groups.values():
            random.shuffle(group_samples)
            
            n_samples = len(group_samples)
            n_train = int(n_samples * self.config['train_split'])
            n_val = int(n_samples * self.config['validation_split'])
            
            train_samples.extend(group_samples[:n_train])
            val_samples.extend(group_samples[n_train:n_train + n_val])
            test_samples.extend(group_samples[n_train + n_val:])
        
        return {
            'train': train_samples,
            'validation': val_samples,
            'test': test_samples
        }
    
    def _splits_exist(self) -> bool:
        """Check if split files exist"""
        return (self.train_dataset.exists() and 
                self.validation_dataset.exists() and 
                self.test_dataset.exists())
    
    def _export_split_files(self):
        """Export split assignments to JSONL files"""
        
        splits = ['train', 'validation', 'test']
        file_mapping = {
            'train': self.train_dataset,
            'validation': self.validation_dataset,
            'test': self.test_dataset
        }
        
        for split in splits:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT raw_text, parsed_data, provider, language, format_type, confidence
                    FROM samples 
                    WHERE split_assignment = ?
                """, (split,))
                
                samples = cursor.fetchall()
            
            # Write to JSONL
            with open(file_mapping[split], 'w', encoding='utf-8') as f:
                for raw_text, parsed_data_json, provider, language, format_type, confidence in samples:
                    try:
                        parsed_data = json.loads(parsed_data_json)
                        
                        entry = {
                            "raw": raw_text,
                            "parsed": parsed_data,
                            "metadata": {
                                "provider": provider,
                                "language": language,
                                "format_type": format_type,
                                "confidence": confidence
                            }
                        }
                        
                        f.write(json.dumps(entry, ensure_ascii=False) + '\n')
                        
                    except json.JSONDecodeError:
                        continue
    
    def get_dataset_metrics(self) -> DatasetMetrics:
        """Calculate comprehensive dataset quality metrics"""
        
        with sqlite3.connect(self.db_path) as conn:
            # Total and verified samples
            cursor = conn.execute("SELECT COUNT(*), SUM(verified) FROM samples")
            total_samples, verified_samples = cursor.fetchone()
            verified_samples = verified_samples or 0
            
            # Provider distribution
            cursor = conn.execute("SELECT provider, COUNT(*) FROM samples GROUP BY provider")
            provider_dist = dict(cursor.fetchall())
            
            # Language distribution
            cursor = conn.execute("SELECT language, COUNT(*) FROM samples GROUP BY language")
            language_dist = dict(cursor.fetchall())
            
            # Format distribution
            cursor = conn.execute("SELECT format_type, COUNT(*) FROM samples GROUP BY format_type")
            format_dist = dict(cursor.fetchall())
            
            # Quality score (based on verification and confidence)
            cursor = conn.execute("SELECT AVG(confidence) FROM samples WHERE verified = TRUE")
            avg_confidence = cursor.fetchone()[0] or 0.5
            
            quality_score = (verified_samples / max(total_samples, 1)) * avg_confidence
            
            # Coverage score (provider and language diversity)
            coverage_score = min(1.0, (len(provider_dist) / 10) * (len(language_dist) / 5))
        
        return DatasetMetrics(
            total_samples=total_samples,
            verified_samples=verified_samples,
            provider_distribution=provider_dist,
            language_distribution=language_dist,
            format_distribution=format_dist,
            quality_score=quality_score,
            coverage_score=coverage_score
        )
    
    def clean_dataset(self, remove_duplicates: bool = True, 
                     quality_threshold: float = 0.5) -> int:
        """Clean dataset by removing duplicates and low-quality samples"""
        
        removed_count = 0
        
        with sqlite3.connect(self.db_path) as conn:
            if remove_duplicates:
                # Find duplicate hashes
                cursor = conn.execute("""
                    SELECT hash, COUNT(*) as count 
                    FROM samples 
                    GROUP BY hash 
                    HAVING count > 1
                """)
                
                duplicate_hashes = [row[0] for row in cursor.fetchall()]
                
                for hash_val in duplicate_hashes:
                    # Keep the first (oldest) sample, remove others
                    cursor = conn.execute("""
                        SELECT id FROM samples 
                        WHERE hash = ? 
                        ORDER BY timestamp
                    """, (hash_val,))
                    
                    sample_ids = [row[0] for row in cursor.fetchall()]
                    
                    # Remove all but the first
                    for sample_id in sample_ids[1:]:
                        conn.execute("DELETE FROM samples WHERE id = ?", (sample_id,))
                        removed_count += 1
            
            # Remove low-quality samples
            cursor = conn.execute("""
                DELETE FROM samples 
                WHERE confidence < ? AND verified = FALSE
            """, (quality_threshold,))
            
            removed_count += cursor.rowcount
        
        self.logger.info(f"Cleaned dataset: removed {removed_count} samples")
        return removed_count
    
    def augment_dataset(self, augmentation_factor: float = 2.0) -> int:
        """Generate augmented samples for data diversity"""
        
        augmented_count = 0
        
        # Get high-quality samples for augmentation
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT raw_text, parsed_data, provider, language 
                FROM samples 
                WHERE verified = TRUE AND confidence > 0.8
                LIMIT 100
            """)
            
            high_quality_samples = cursor.fetchall()
        
        for raw_text, parsed_data_json, provider, language in high_quality_samples:
            try:
                # Simple augmentation techniques
                augmented_texts = self._augment_text(raw_text)
                parsed_data = json.loads(parsed_data_json)
                
                for aug_text in augmented_texts:
                    if aug_text != raw_text:  # Don't duplicate original
                        sample_id = self.add_sample(
                            raw_text=aug_text,
                            parsed_data=parsed_data,
                            provider=f"{provider}_aug",
                            language=language,
                            format_type="augmented",
                            confidence=0.7
                        )
                        
                        if sample_id:
                            augmented_count += 1
                            
                if augmented_count >= len(high_quality_samples) * augmentation_factor:
                    break
                    
            except json.JSONDecodeError:
                continue
        
        self.logger.info(f"Generated {augmented_count} augmented samples")
        return augmented_count
    
    def _augment_text(self, text: str) -> List[str]:
        """Generate text augmentations"""
        augmentations = []
        
        # Punctuation variations
        no_punct = text.replace('!', '').replace('?', '').replace('.', '')
        augmentations.append(no_punct)
        
        # Case variations
        augmentations.append(text.upper())
        augmentations.append(text.lower())
        
        # Spacing variations
        compact = ' '.join(text.split())
        augmentations.append(compact)
        
        # Emoji removal/addition
        import re
        emoji_pattern = re.compile(r'[^\w\s.,!?-]')
        no_emoji = emoji_pattern.sub('', text)
        augmentations.append(no_emoji)
        
        return list(set(augmentations))  # Remove duplicates
    
    def export_training_data(self, format_type: str = "huggingface") -> Dict[str, str]:
        """Export training data in specified format"""
        
        if format_type == "huggingface":
            return self._export_huggingface_format()
        elif format_type == "spacy":
            return self._export_spacy_format()
        else:
            raise ValueError(f"Unsupported format: {format_type}")
    
    def _export_huggingface_format(self) -> Dict[str, str]:
        """Export data in HuggingFace format"""
        
        output_files = {}
        
        for split in ['train', 'validation', 'test']:
            file_path = self.data_dir / f"{split}_hf.jsonl"
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT raw_text, parsed_data 
                    FROM samples 
                    WHERE split_assignment = ?
                """, (split,))
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    for raw_text, parsed_data_json in cursor.fetchall():
                        try:
                            parsed_data = json.loads(parsed_data_json)
                            
                            # HuggingFace format
                            hf_entry = {
                                "input": f"Extract trading signal from: {raw_text}",
                                "output": json.dumps(parsed_data)
                            }
                            
                            f.write(json.dumps(hf_entry, ensure_ascii=False) + '\n')
                            
                        except json.JSONDecodeError:
                            continue
            
            output_files[split] = str(file_path)
        
        return output_files
    
    def _export_spacy_format(self) -> Dict[str, str]:
        """Export data in spaCy training format"""
        
        output_files = {}
        
        for split in ['train', 'validation', 'test']:
            file_path = self.data_dir / f"{split}_spacy.jsonl"
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT raw_text, parsed_data 
                    FROM samples 
                    WHERE split_assignment = ?
                """, (split,))
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    for raw_text, parsed_data_json in cursor.fetchall():
                        try:
                            parsed_data = json.loads(parsed_data_json)
                            
                            # Convert to spaCy NER format
                            entities = self._extract_entities_for_spacy(raw_text, parsed_data)
                            
                            spacy_entry = {
                                "text": raw_text,
                                "entities": entities
                            }
                            
                            f.write(json.dumps(spacy_entry, ensure_ascii=False) + '\n')
                            
                        except json.JSONDecodeError:
                            continue
            
            output_files[split] = str(file_path)
        
        return output_files
    
    def _extract_entities_for_spacy(self, text: str, parsed_data: Dict[str, Any]) -> List[Tuple[int, int, str]]:
        """Extract entity positions for spaCy NER training"""
        entities = []
        
        # Find entity positions in text
        if 'pair' in parsed_data:
            pair = str(parsed_data['pair'])
            start = text.upper().find(pair.upper())
            if start != -1:
                entities.append((start, start + len(pair), "PAIR"))
        
        if 'direction' in parsed_data:
            direction = str(parsed_data['direction'])
            start = text.upper().find(direction.upper())
            if start != -1:
                entities.append((start, start + len(direction), "DIRECTION"))
        
        # Add more entity extraction logic as needed
        
        return entities
    
    def get_sample_by_id(self, sample_id: str) -> Optional[DatasetSample]:
        """Retrieve a specific sample by ID"""
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT * FROM samples WHERE id = ?
            """, (sample_id,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            return DatasetSample(
                id=row[0],
                raw_text=row[1],
                parsed_data=json.loads(row[2]),
                provider=row[3],
                language=row[4],
                format_type=row[5],
                confidence=row[6],
                timestamp=datetime.fromisoformat(row[7]),
                verified=bool(row[8]),
                correction_count=row[9]
            )
    
    def get_status_report(self) -> Dict[str, Any]:
        """Generate comprehensive dataset status report"""
        
        metrics = self.get_dataset_metrics()
        
        return {
            "dataset_metrics": asdict(metrics),
            "file_status": {
                "train_exists": self.train_dataset.exists(),
                "validation_exists": self.validation_dataset.exists(),
                "test_exists": self.test_dataset.exists(),
                "feedback_exists": self.feedback_dataset.exists()
            },
            "data_quality": {
                "quality_score": metrics.quality_score,
                "coverage_score": metrics.coverage_score,
                "verification_rate": metrics.verified_samples / max(metrics.total_samples, 1),
                "ready_for_training": metrics.quality_score > 0.7 and metrics.total_samples > 1000
            },
            "recommendations": self._generate_recommendations(metrics)
        }
    
    def _generate_recommendations(self, metrics: DatasetMetrics) -> List[str]:
        """Generate dataset improvement recommendations"""
        recommendations = []
        
        if metrics.total_samples < 1000:
            recommendations.append("Collect more samples (minimum 1000 recommended)")
        
        if metrics.verified_samples / max(metrics.total_samples, 1) < 0.5:
            recommendations.append("Increase verification rate by reviewing and correcting samples")
        
        if len(metrics.provider_distribution) < 5:
            recommendations.append("Add samples from more signal providers for diversity")
        
        if len(metrics.language_distribution) < 3:
            recommendations.append("Include multilingual samples for better coverage")
        
        if metrics.quality_score < 0.7:
            recommendations.append("Improve sample quality through better curation and verification")
        
        return recommendations