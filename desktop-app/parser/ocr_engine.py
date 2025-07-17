#!/usr/bin/env python3
"""
OCR Engine for SignalOS Desktop Application

Implements OCR-based signal reading using computer vision libraries.
Extracts text from images and screenshots for signal processing.
"""

import cv2
import numpy as np
import logging
import json
import base64
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from PIL import Image
import io
import re
import sqlite3

try:
    import easyocr
    EASYOCR_AVAILABLE = True
except ImportError:
    EASYOCR_AVAILABLE = False
    logging.warning("EasyOCR not available, using fallback OCR methods")

try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False

@dataclass
class OCRResult:
    """Result of OCR text extraction"""
    text: str
    confidence: float
    bounding_box: Tuple[int, int, int, int]  # x, y, width, height
    language: str
    extraction_method: str

@dataclass
class SignalOCRExtraction:
    """Complete OCR extraction result for a signal image"""
    source_image: str  # Base64 encoded image
    extracted_texts: List[OCRResult]
    processed_signal: Optional[Dict[str, Any]]
    confidence_score: float
    extraction_timestamp: datetime
    preprocessing_applied: List[str]

class OCREngine:
    """OCR engine for extracting trading signals from images"""
    
    def __init__(self, config_file: str = "config.json", log_file: str = "logs/ocr_engine.log"):
        self.config_file = config_file
        self.log_file = log_file
        self.config = self._load_config()
        self._setup_logging()
        
        # Initialize OCR readers
        self.easyocr_reader = None
        self.supported_languages = ['en', 'ar', 'es', 'fr', 'de', 'it', 'pt', 'ru', 'zh', 'ja']
        
        # Initialize OCR engines
        self._initialize_ocr_engines()
        
        # Signal patterns for text extraction
        self.signal_patterns = self._load_signal_patterns()
        
        # Learning database for OCR improvements
        self.learning_db = self._init_learning_database()
        
        # Statistics
        self.stats = {
            "total_extractions": 0,
            "successful_extractions": 0,
            "failed_extractions": 0,
            "average_confidence": 0.0,
            "extractions_by_method": {},
            "languages_detected": {}
        }
    
    def _init_learning_database(self) -> Optional[sqlite3.Connection]:
        """Initialize learning database for OCR improvements"""
        try:
            db_path = Path("logs/ocr_learning.db")
            db_path.parent.mkdir(parents=True, exist_ok=True)
            
            db = sqlite3.connect(str(db_path))
            
            # Create tables
            db.execute('''
                CREATE TABLE IF NOT EXISTS ocr_extractions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    image_hash TEXT,
                    extracted_text TEXT,
                    confidence_score REAL,
                    method_used TEXT,
                    language_detected TEXT,
                    preprocessing_applied TEXT,
                    timestamp TEXT,
                    validation_result TEXT,
                    user_feedback TEXT
                )
            ''')
            
            db.execute('''
                CREATE TABLE IF NOT EXISTS ocr_improvements (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    image_hash TEXT,
                    original_text TEXT,
                    corrected_text TEXT,
                    improvement_type TEXT,
                    timestamp TEXT
                )
            ''')
            
            db.commit()
            return db
            
        except Exception as e:
            self.logger.error(f"Failed to initialize OCR learning database: {e}")
            return None
        
    def _load_config(self) -> Dict[str, Any]:
        """Load OCR engine configuration"""
        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)
                return config.get('ocr_engine', self._get_default_config())
        except FileNotFoundError:
            return self._create_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default OCR configuration"""
        return {
            "enabled": True,
            "preferred_method": "easyocr",  # easyocr, tesseract, both
            "languages": ["en", "ar"],  # Supported languages
            "confidence_threshold": 0.6,
            "preprocessing": {
                "resize_factor": 2.0,
                "apply_gaussian_blur": True,
                "apply_threshold": True,
                "apply_morphology": True,
                "noise_removal": True
            },
            "text_detection": {
                "min_text_size": 10,
                "max_text_size": 200,
                "text_merge_threshold": 5
            },
            "signal_extraction": {
                "enable_pattern_matching": True,
                "enable_ml_classification": False,
                "confidence_boost_patterns": True
            }
        }
    
    def _create_default_config(self) -> Dict[str, Any]:
        """Create default configuration and save to file"""
        default_config = {
            "ocr_engine": self._get_default_config()
        }
        
        try:
            with open(self.config_file, 'w') as f:
                json.dump(default_config, f, indent=4)
        except Exception as e:
            logging.error(f"Failed to save default config: {e}")
            
        return default_config["ocr_engine"]
    
    def _setup_logging(self):
        """Setup logging for OCR engine"""
        self.logger = logging.getLogger('OCREngine')
        self.logger.setLevel(logging.INFO)
        
        if not self.logger.handlers:
            # Ensure log directory exists
            Path(self.log_file).parent.mkdir(parents=True, exist_ok=True)
            
            # File handler
            file_handler = logging.FileHandler(self.log_file)
            file_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            file_handler.setFormatter(file_formatter)
            self.logger.addHandler(file_handler)
            
            # Console handler
            console_handler = logging.StreamHandler()
            console_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            console_handler.setFormatter(console_formatter)
            self.logger.addHandler(console_handler)
    
    def _initialize_ocr_engines(self):
        """Initialize available OCR engines"""
        self.logger.info("Initializing OCR engines...")
        
        # Initialize EasyOCR if available
        if EASYOCR_AVAILABLE:
            try:
                languages = self.config.get("languages", ["en", "ar"])
                self.easyocr_reader = easyocr.Reader(languages, gpu=False)
                self.logger.info(f"EasyOCR initialized with languages: {languages}")
            except Exception as e:
                self.logger.error(f"Failed to initialize EasyOCR: {e}")
                self.easyocr_reader = None
        
        # Check Tesseract availability
        if TESSERACT_AVAILABLE:
            try:
                # Test Tesseract installation
                test_image = np.ones((100, 100), dtype=np.uint8) * 255
                pytesseract.image_to_string(test_image)
                self.logger.info("Tesseract OCR available")
            except Exception as e:
                self.logger.warning(f"Tesseract not properly configured: {e}")
        
        available_methods = []
        if self.easyocr_reader:
            available_methods.append("easyocr")
        if TESSERACT_AVAILABLE:
            available_methods.append("tesseract")
            
        self.logger.info(f"Available OCR methods: {available_methods}")
    
    def _load_signal_patterns(self) -> Dict[str, List[str]]:
        """Load trading signal patterns for text extraction"""
        return {
            "entry_patterns": [
                r"(?:entry|buy|sell|open)\s*:?\s*([0-9.,]+)",
                r"(?:at|@)\s*([0-9.,]+)",
                r"(?:price|nivel|سعر)\s*:?\s*([0-9.,]+)"
            ],
            "stop_loss_patterns": [
                r"(?:sl|stop|stop\s*loss|وقف\s*خسارة)\s*:?\s*([0-9.,]+)",
                r"(?:stop\s*at|detener\s*en)\s*([0-9.,]+)"
            ],
            "take_profit_patterns": [
                r"(?:tp|take\s*profit|objetivo|هدف)\s*:?\s*([0-9.,]+)",
                r"(?:target|profit\s*at)\s*([0-9.,]+)"
            ],
            "symbol_patterns": [
                r"(EUR\/USD|EURUSD|EUR-USD)",
                r"(GBP\/USD|GBPUSD|GBP-USD)", 
                r"(USD\/JPY|USDJPY|USD-JPY)",
                r"(AUD\/USD|AUDUSD|AUD-USD)",
                r"(USD\/CAD|USDCAD|USD-CAD)",
                r"(NZD\/USD|NZDUSD|NZD-USD)",
                r"(USD\/CHF|USDCHF|USD-CHF)",
                r"(XAU\/USD|XAUUSD|GOLD)",
                r"(XAG\/USD|XAGUSD|SILVER)"
            ],
            "direction_patterns": [
                r"(?:buy|long|شراء|comprar)",
                r"(?:sell|short|بيع|vender)"
            ]
        }
    
    def preprocess_image(self, image: np.ndarray) -> Tuple[np.ndarray, List[str]]:
        """Preprocess image for better OCR results"""
        preprocessing_applied = []
        processed_image = image.copy()
        
        try:
            # Convert to grayscale if needed
            if len(processed_image.shape) == 3:
                processed_image = cv2.cvtColor(processed_image, cv2.COLOR_BGR2GRAY)
                preprocessing_applied.append("grayscale_conversion")
            
            # Resize image for better OCR
            if self.config.get("preprocessing", {}).get("resize_factor", 2.0) > 1.0:
                resize_factor = self.config["preprocessing"]["resize_factor"]
                height, width = processed_image.shape[:2]
                new_width = int(width * resize_factor)
                new_height = int(height * resize_factor)
                processed_image = cv2.resize(processed_image, (new_width, new_height), interpolation=cv2.INTER_CUBIC)
                preprocessing_applied.append(f"resize_{resize_factor}x")
            
            # Apply Gaussian blur to reduce noise
            if self.config.get("preprocessing", {}).get("apply_gaussian_blur", True):
                processed_image = cv2.GaussianBlur(processed_image, (5, 5), 0)
                preprocessing_applied.append("gaussian_blur")
            
            # Apply threshold
            if self.config.get("preprocessing", {}).get("apply_threshold", True):
                _, processed_image = cv2.threshold(processed_image, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                preprocessing_applied.append("otsu_threshold")
            
            # Apply morphological operations
            if self.config.get("preprocessing", {}).get("apply_morphology", True):
                kernel = np.ones((2, 2), np.uint8)
                processed_image = cv2.morphologyEx(processed_image, cv2.MORPH_CLOSE, kernel)
                preprocessing_applied.append("morphology_close")
            
            # Noise removal
            if self.config.get("preprocessing", {}).get("noise_removal", True):
                processed_image = cv2.medianBlur(processed_image, 3)
                preprocessing_applied.append("median_blur")
                
        except Exception as e:
            self.logger.error(f"Error in image preprocessing: {e}")
            return image, ["error_in_preprocessing"]
        
        return processed_image, preprocessing_applied
    
    def extract_text_easyocr(self, image: np.ndarray) -> List[OCRResult]:
        """Extract text using EasyOCR"""
        if not self.easyocr_reader:
            return []
        
        try:
            results = self.easyocr_reader.readtext(image)
            ocr_results = []
            
            for (bbox, text, confidence) in results:
                # Convert bbox to x, y, width, height format
                x_coords = [point[0] for point in bbox]
                y_coords = [point[1] for point in bbox]
                x, y = int(min(x_coords)), int(min(y_coords))
                width = int(max(x_coords) - x)
                height = int(max(y_coords) - y)
                
                ocr_result = OCRResult(
                    text=text.strip(),
                    confidence=confidence,
                    bounding_box=(x, y, width, height),
                    language="auto",  # EasyOCR handles language detection
                    extraction_method="easyocr"
                )
                ocr_results.append(ocr_result)
            
            return ocr_results
            
        except Exception as e:
            self.logger.error(f"Error in EasyOCR extraction: {e}")
            return []
    
    def extract_text_tesseract(self, image: np.ndarray) -> List[OCRResult]:
        """Extract text using Tesseract OCR"""
        if not TESSERACT_AVAILABLE:
            return []
        
        try:
            # Get detailed data from Tesseract
            data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
            
            ocr_results = []
            for i in range(len(data['text'])):
                text = data['text'][i].strip()
                confidence = int(data['conf'][i])
                
                if text and confidence > 0:
                    # Convert confidence from 0-100 to 0-1 scale
                    confidence_normalized = confidence / 100.0
                    
                    x, y, w, h = data['left'][i], data['top'][i], data['width'][i], data['height'][i]
                    
                    ocr_result = OCRResult(
                        text=text,
                        confidence=confidence_normalized,
                        bounding_box=(x, y, w, h),
                        language="auto",
                        extraction_method="tesseract"
                    )
                    ocr_results.append(ocr_result)
            
            return ocr_results
            
        except Exception as e:
            self.logger.error(f"Error in Tesseract extraction: {e}")
            return []
    
    def extract_text_from_image(self, image: np.ndarray) -> List[OCRResult]:
        """Extract text using all available OCR methods"""
        all_results = []
        
        # Preprocess image
        processed_image, preprocessing_applied = self.preprocess_image(image)
        
        # Try EasyOCR
        if self.config.get("preferred_method") in ["easyocr", "both"] and self.easyocr_reader:
            easyocr_results = self.extract_text_easyocr(processed_image)
            all_results.extend(easyocr_results)
            self.stats["extractions_by_method"]["easyocr"] = self.stats["extractions_by_method"].get("easyocr", 0) + 1
        
        # Try Tesseract
        if self.config.get("preferred_method") in ["tesseract", "both"] and TESSERACT_AVAILABLE:
            tesseract_results = self.extract_text_tesseract(processed_image)
            all_results.extend(tesseract_results)
            self.stats["extractions_by_method"]["tesseract"] = self.stats["extractions_by_method"].get("tesseract", 0) + 1
        
        # Filter by confidence threshold
        confidence_threshold = self.config.get("confidence_threshold", 0.6)
        filtered_results = [
            result for result in all_results 
            if result.confidence >= confidence_threshold
        ]
        
        return filtered_results
    
    def extract_signal_from_text(self, ocr_results: List[OCRResult]) -> Optional[Dict[str, Any]]:
        """Extract trading signal information from OCR text results"""
        combined_text = " ".join([result.text for result in ocr_results])
        
        signal_data = {
            "symbol": None,
            "direction": None,
            "entry_price": None,
            "stop_loss": None,
            "take_profit": [],
            "confidence": 0.0,
            "raw_text": combined_text
        }
        
        confidence_scores = []
        
        try:
            # Extract symbol
            for pattern in self.signal_patterns["symbol_patterns"]:
                match = re.search(pattern, combined_text, re.IGNORECASE)
                if match:
                    signal_data["symbol"] = match.group(1).replace("/", "").replace("-", "")
                    confidence_scores.append(0.9)
                    break
            
            # Extract direction
            for pattern in self.signal_patterns["direction_patterns"]:
                match = re.search(pattern, combined_text, re.IGNORECASE)
                if match:
                    direction_text = match.group(0).lower()
                    if any(word in direction_text for word in ["buy", "long", "شراء", "comprar"]):
                        signal_data["direction"] = "BUY"
                    elif any(word in direction_text for word in ["sell", "short", "بيع", "vender"]):
                        signal_data["direction"] = "SELL"
                    confidence_scores.append(0.8)
                    break
            
            # Extract entry price
            for pattern in self.signal_patterns["entry_patterns"]:
                match = re.search(pattern, combined_text, re.IGNORECASE)
                if match:
                    try:
                        price_str = match.group(1).replace(",", ".")
                        signal_data["entry_price"] = float(price_str)
                        confidence_scores.append(0.8)
                        break
                    except ValueError:
                        continue
            
            # Extract stop loss
            for pattern in self.signal_patterns["stop_loss_patterns"]:
                match = re.search(pattern, combined_text, re.IGNORECASE)
                if match:
                    try:
                        sl_str = match.group(1).replace(",", ".")
                        signal_data["stop_loss"] = float(sl_str)
                        confidence_scores.append(0.7)
                        break
                    except ValueError:
                        continue
            
            # Extract take profit levels
            for pattern in self.signal_patterns["take_profit_patterns"]:
                matches = re.finditer(pattern, combined_text, re.IGNORECASE)
                for match in matches:
                    try:
                        tp_str = match.group(1).replace(",", ".")
                        tp_value = float(tp_str)
                        if tp_value not in signal_data["take_profit"]:
                            signal_data["take_profit"].append(tp_value)
                            confidence_scores.append(0.7)
                    except ValueError:
                        continue
            
            # Calculate overall confidence
            if confidence_scores:
                signal_data["confidence"] = sum(confidence_scores) / len(confidence_scores)
            
            # Apply confidence boost for pattern matching
            if (self.config.get("signal_extraction", {}).get("confidence_boost_patterns", True) and 
                signal_data["symbol"] and signal_data["direction"]):
                signal_data["confidence"] = min(signal_data["confidence"] * 1.2, 1.0)
            
            return signal_data if signal_data["confidence"] > 0.3 else None
            
        except Exception as e:
            self.logger.error(f"Error extracting signal from text: {e}")
            return None
    
    def process_image(self, image_data: bytes, source_name: str = "unknown") -> SignalOCRExtraction:
        """Process image and extract trading signal"""
        try:
            # Convert bytes to numpy array
            nparr = np.frombuffer(image_data, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if image is None:
                raise ValueError("Could not decode image data")
            
            # Extract text
            ocr_results = self.extract_text_from_image(image)
            
            # Extract signal
            signal_data = None
            if ocr_results:
                signal_data = self.extract_signal_from_text(ocr_results)
            
            # Calculate overall confidence
            if ocr_results:
                avg_confidence = sum(result.confidence for result in ocr_results) / len(ocr_results)
            else:
                avg_confidence = 0.0
            
            # Encode image to base64 for storage
            _, buffer = cv2.imencode('.png', image)
            encoded_image = base64.b64encode(buffer).decode('utf-8')
            
            # Update statistics
            self.stats["total_extractions"] += 1
            if signal_data and signal_data["confidence"] > 0.5:
                self.stats["successful_extractions"] += 1
            else:
                self.stats["failed_extractions"] += 1
            
            # Update average confidence
            total_extractions = self.stats["total_extractions"]
            current_avg = self.stats["average_confidence"]
            self.stats["average_confidence"] = ((current_avg * (total_extractions - 1)) + avg_confidence) / total_extractions
            
            extraction_result = SignalOCRExtraction(
                source_image=encoded_image,
                extracted_texts=ocr_results,
                processed_signal=signal_data,
                confidence_score=avg_confidence,
                extraction_timestamp=datetime.now(),
                preprocessing_applied=[]  # Will be set by preprocessing function
            )
            
            self.logger.info(f"Processed image '{source_name}': {len(ocr_results)} text regions, signal_detected={bool(signal_data)}")
            
            return extraction_result
            
        except Exception as e:
            self.logger.error(f"Error processing image '{source_name}': {e}")
            self.stats["total_extractions"] += 1
            self.stats["failed_extractions"] += 1
            
            return SignalOCRExtraction(
                source_image="",
                extracted_texts=[],
                processed_signal=None,
                confidence_score=0.0,
                extraction_timestamp=datetime.now(),
                preprocessing_applied=["error"]
            )
    
    def process_file(self, file_path: str) -> SignalOCRExtraction:
        """Process image file and extract trading signal"""
        try:
            with open(file_path, 'rb') as f:
                image_data = f.read()
            
            return self.process_image(image_data, source_name=Path(file_path).name)
            
        except Exception as e:
            self.logger.error(f"Error processing file '{file_path}': {e}")
            return SignalOCRExtraction(
                source_image="",
                extracted_texts=[],
                processed_signal=None,
                confidence_score=0.0,
                extraction_timestamp=datetime.now(),
                preprocessing_applied=["file_error"]
            )
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get OCR engine statistics"""
        return {
            **self.stats,
            "available_methods": {
                "easyocr": bool(self.easyocr_reader),
                "tesseract": TESSERACT_AVAILABLE
            },
            "supported_languages": self.supported_languages,
            "configuration": self.config
        }


# Example usage and testing
def main():
    """Example usage of OCR engine"""
    engine = OCREngine()
    
    # Test with a sample image (if available)
    test_image_path = "test_signal.png"
    if Path(test_image_path).exists():
        result = engine.process_file(test_image_path)
        print(f"OCR Result: {result.processed_signal}")
        print(f"Confidence: {result.confidence_score}")
        print(f"Extracted texts: {[r.text for r in result.extracted_texts]}")
    else:
        print("No test image found")
    
    # Show statistics
    stats = engine.get_statistics()
    print(f"OCR Engine Statistics: {json.dumps(stats, indent=2)}")


if __name__ == "__main__":
    main()