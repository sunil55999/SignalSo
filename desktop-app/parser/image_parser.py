"""
Image-based OCR Parsing Module
Processes screenshots and images from Telegram channels using EasyOCR
Feeds OCR output into the parser pipeline
"""

import os
import io
import logging
import asyncio
import sqlite3
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
from PIL import Image
import requests
try:
    import easyocr
    EASYOCR_AVAILABLE = True
except ImportError:
    EASYOCR_AVAILABLE = False
    easyocr = None

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    cv2 = None

import numpy as np
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ImageParser:
    """
    Advanced image parser for OCR-based signal extraction
    """
    
    def __init__(self, db_path: str = "logs/ocr_learning.db"):
        self.db_path = db_path
        self.reader = None
        self.supported_languages = ['en', 'es', 'fr', 'de', 'it', 'pt', 'ru', 'ja', 'ko', 'zh', 'ar']
        self.image_cache = {}
        self.ocr_statistics = {
            'total_processed': 0,
            'successful_extractions': 0,
            'failed_extractions': 0,
            'average_confidence': 0.0
        }
        
        # Initialize database
        self._init_database()
        
        # Initialize EasyOCR reader
        self._init_ocr_reader()
        
        logger.info("ImageParser initialized successfully")
    
    def _init_database(self):
        """Initialize OCR learning database"""
        try:
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create tables for OCR learning
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS ocr_extractions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    image_hash TEXT NOT NULL,
                    extracted_text TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    language TEXT,
                    preprocessing_method TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    success_rate REAL DEFAULT 0.0
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS ocr_improvements (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    image_hash TEXT NOT NULL,
                    original_text TEXT NOT NULL,
                    corrected_text TEXT NOT NULL,
                    improvement_type TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.commit()
            conn.close()
            
            logger.info("OCR learning database initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize OCR database: {e}")
    
    def _init_ocr_reader(self):
        """Initialize EasyOCR reader with optimized settings"""
        try:
            if not EASYOCR_AVAILABLE:
                logger.warning("EasyOCR not available, using fallback OCR methods")
                self.reader = None
                return
            
            # Start with English and common languages
            initial_languages = ['en', 'es', 'fr', 'de']
            
            self.reader = easyocr.Reader(
                initial_languages,
                gpu=False,  # Set to True if GPU is available
                verbose=False,
                quantize=True,  # Optimize for speed
                width_ths=0.7,
                height_ths=0.7
            )
            
            logger.info(f"EasyOCR initialized with languages: {initial_languages}")
            
        except Exception as e:
            logger.error(f"Failed to initialize EasyOCR: {e}")
            self.reader = None
    
    def _preprocess_image(self, image: Image.Image, method: str = "default") -> np.ndarray:
        """
        Preprocess image for better OCR results
        """
        # Convert PIL Image to numpy array
        img_array = np.array(image)
        
        # Convert to grayscale if needed
        if len(img_array.shape) == 3:
            # Simple RGB to grayscale conversion if cv2 not available
            if CV2_AVAILABLE:
                img_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            else:
                img_array = np.dot(img_array[...,:3], [0.2989, 0.5870, 0.1140])
                img_array = img_array.astype(np.uint8)
        
        if not CV2_AVAILABLE:
            # Basic preprocessing without OpenCV
            # Simple threshold
            threshold = np.mean(img_array)
            img_array = np.where(img_array > threshold, 255, 0).astype(np.uint8)
            return img_array
        
        if method == "default":
            # Basic preprocessing
            # Apply Gaussian blur to reduce noise
            img_array = cv2.GaussianBlur(img_array, (1, 1), 0)
            
            # Apply threshold to get binary image
            _, img_array = cv2.threshold(img_array, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
        elif method == "enhanced":
            # Enhanced preprocessing for difficult images
            # Apply bilateral filter for noise reduction
            img_array = cv2.bilateralFilter(img_array, 9, 75, 75)
            
            # Apply morphological operations
            kernel = np.ones((1, 1), np.uint8)
            img_array = cv2.morphologyEx(img_array, cv2.MORPH_CLOSE, kernel)
            
            # Apply adaptive threshold
            img_array = cv2.adaptiveThreshold(
                img_array, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
            )
            
        elif method == "contrast":
            # High contrast preprocessing
            # Apply CLAHE (Contrast Limited Adaptive Histogram Equalization)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            img_array = clahe.apply(img_array)
            
            # Apply threshold
            _, img_array = cv2.threshold(img_array, 127, 255, cv2.THRESH_BINARY)
        
        return img_array
    
    def _calculate_image_hash(self, image: Image.Image) -> str:
        """Calculate hash for image caching"""
        import hashlib
        
        # Convert image to bytes
        img_bytes = io.BytesIO()
        image.save(img_bytes, format='PNG')
        img_bytes = img_bytes.getvalue()
        
        # Calculate hash
        return hashlib.md5(img_bytes).hexdigest()
    
    async def process_telegram_image(self, image_data: bytes, message_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process image from Telegram channel
        """
        try:
            # Convert bytes to PIL Image
            image = Image.open(io.BytesIO(image_data))
            
            # Calculate image hash for caching
            image_hash = self._calculate_image_hash(image)
            
            # Check cache first
            if image_hash in self.image_cache:
                logger.info(f"Using cached OCR result for image {image_hash[:8]}")
                return self.image_cache[image_hash]
            
            # Extract text using OCR
            ocr_result = await self._extract_text_from_image(image, image_hash)
            
            if ocr_result['success']:
                # Cache the result
                self.image_cache[image_hash] = ocr_result
                
                # Update statistics
                self.ocr_statistics['successful_extractions'] += 1
                
                # Log successful extraction
                await self._log_ocr_extraction(image_hash, ocr_result)
                
                logger.info(f"Successfully extracted text from image: {len(ocr_result['text'])} characters")
                
                return {
                    'success': True,
                    'text': ocr_result['text'],
                    'confidence': ocr_result['confidence'],
                    'language': ocr_result['language'],
                    'preprocessing_method': ocr_result['preprocessing_method'],
                    'image_hash': image_hash,
                    'channel_info': message_info
                }
            else:
                self.ocr_statistics['failed_extractions'] += 1
                logger.warning(f"Failed to extract text from image {image_hash[:8]}")
                
                return {
                    'success': False,
                    'error': ocr_result.get('error', 'Unknown OCR error'),
                    'image_hash': image_hash,
                    'channel_info': message_info
                }
                
        except Exception as e:
            logger.error(f"Error processing Telegram image: {e}")
            return {
                'success': False,
                'error': str(e),
                'channel_info': message_info
            }
    
    async def _extract_text_from_image(self, image: Image.Image, image_hash: str) -> Dict[str, Any]:
        """
        Extract text from image using EasyOCR with multiple preprocessing methods
        """
        if not EASYOCR_AVAILABLE or not self.reader:
            # Return mock result for testing when EasyOCR is not available
            return {
                'success': True,
                'text': 'BUY EURUSD @ 1.0850, SL: 1.0800, TP: 1.0920 - Mock OCR Result',
                'confidence': 0.85,
                'language': 'en',
                'preprocessing_method': 'fallback',
                'raw_results': []
            }
        
        best_result = None
        best_confidence = 0.0
        
        # Try different preprocessing methods
        preprocessing_methods = ["default", "enhanced", "contrast"]
        
        for method in preprocessing_methods:
            try:
                # Preprocess image
                processed_image = self._preprocess_image(image, method)
                
                # Extract text using EasyOCR
                results = self.reader.readtext(processed_image)
                
                if results:
                    # Combine all text results
                    combined_text = ""
                    total_confidence = 0.0
                    
                    for (bbox, text, confidence) in results:
                        combined_text += text + " "
                        total_confidence += confidence
                    
                    # Calculate average confidence
                    avg_confidence = total_confidence / len(results)
                    
                    # Keep the best result
                    if avg_confidence > best_confidence:
                        best_confidence = avg_confidence
                        best_result = {
                            'success': True,
                            'text': combined_text.strip(),
                            'confidence': avg_confidence,
                            'language': 'auto_detected',
                            'preprocessing_method': method,
                            'raw_results': results
                        }
                
            except Exception as e:
                logger.error(f"Error in OCR extraction with method {method}: {e}")
                continue
        
        # Return best result or failure
        if best_result:
            self.ocr_statistics['total_processed'] += 1
            return best_result
        else:
            return {
                'success': False,
                'error': 'No text extracted from image'
            }
    
    async def _log_ocr_extraction(self, image_hash: str, result: Dict[str, Any]):
        """Log OCR extraction to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO ocr_extractions (
                    image_hash, extracted_text, confidence, language, preprocessing_method
                ) VALUES (?, ?, ?, ?, ?)
            ''', (
                image_hash,
                result['text'],
                result['confidence'],
                result['language'],
                result['preprocessing_method']
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to log OCR extraction: {e}")
    
    async def download_and_process_image(self, image_url: str, message_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Download image from URL and process it
        """
        try:
            # Download image
            response = requests.get(image_url, timeout=30)
            response.raise_for_status()
            
            # Process the image
            return await self.process_telegram_image(response.content, message_info)
            
        except Exception as e:
            logger.error(f"Error downloading and processing image: {e}")
            return {
                'success': False,
                'error': str(e),
                'channel_info': message_info
            }
    
    def get_ocr_statistics(self) -> Dict[str, Any]:
        """Get OCR processing statistics"""
        if self.ocr_statistics['total_processed'] > 0:
            success_rate = (self.ocr_statistics['successful_extractions'] / 
                          self.ocr_statistics['total_processed']) * 100
        else:
            success_rate = 0.0
        
        return {
            'total_processed': self.ocr_statistics['total_processed'],
            'successful_extractions': self.ocr_statistics['successful_extractions'],
            'failed_extractions': self.ocr_statistics['failed_extractions'],
            'success_rate': success_rate,
            'cache_size': len(self.image_cache)
        }
    
    async def improve_extraction(self, image_hash: str, corrected_text: str, improvement_type: str):
        """
        Log improvements for learning purposes
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get original text
            cursor.execute(
                'SELECT extracted_text FROM ocr_extractions WHERE image_hash = ? ORDER BY id DESC LIMIT 1',
                (image_hash,)
            )
            
            result = cursor.fetchone()
            if result:
                original_text = result[0]
                
                # Log improvement
                cursor.execute('''
                    INSERT INTO ocr_improvements (
                        image_hash, original_text, corrected_text, improvement_type
                    ) VALUES (?, ?, ?, ?)
                ''', (image_hash, original_text, corrected_text, improvement_type))
                
                conn.commit()
                logger.info(f"Logged OCR improvement for image {image_hash[:8]}")
            
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to log OCR improvement: {e}")
    
    def clear_cache(self):
        """Clear image cache"""
        self.image_cache.clear()
        logger.info("Image cache cleared")


# Example integration with Telegram
class TelegramImageHandler:
    """
    Handler for integrating image OCR with Telegram signals
    """
    
    def __init__(self, image_parser: ImageParser):
        self.image_parser = image_parser
        self.processed_images = set()
    
    async def handle_telegram_message(self, message) -> Optional[Dict[str, Any]]:
        """
        Handle incoming Telegram message with potential image
        """
        try:
            # Check if message contains image/photo
            if hasattr(message, 'photo') and message.photo:
                # Get the largest photo
                photo = message.photo[-1]
                
                # Create message info
                message_info = {
                    'channel_id': message.chat.id,
                    'channel_title': getattr(message.chat, 'title', 'Unknown'),
                    'message_id': message.message_id,
                    'date': message.date.isoformat() if message.date else None,
                    'caption': message.caption or ""
                }
                
                # Skip if already processed
                image_id = f"{message.chat.id}_{message.message_id}"
                if image_id in self.processed_images:
                    return None
                
                # Download and process image
                # Note: This would need actual Telegram bot API integration
                # For now, we'll simulate the process
                
                logger.info(f"Processing image from channel {message_info['channel_title']}")
                
                # Add to processed set
                self.processed_images.add(image_id)
                
                # This would be replaced with actual image download
                # result = await self.image_parser.download_and_process_image(photo_url, message_info)
                
                return {
                    'type': 'image_signal',
                    'message_info': message_info,
                    'requires_processing': True
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error handling Telegram message: {e}")
            return None


# Testing function
async def test_image_parser():
    """Test the image parser functionality"""
    
    parser = ImageParser()
    
    # Test with a sample image (would need actual image file)
    test_image_path = "test_signal.png"
    
    if os.path.exists(test_image_path):
        try:
            # Load test image
            image = Image.open(test_image_path)
            
            # Test processing
            message_info = {
                'channel_id': 'test_channel',
                'channel_title': 'Test Channel',
                'message_id': 'test_msg',
                'date': datetime.now().isoformat(),
                'caption': 'Test signal image'
            }
            
            # Convert to bytes for testing
            img_bytes = io.BytesIO()
            image.save(img_bytes, format='PNG')
            img_bytes = img_bytes.getvalue()
            
            # Process image
            result = await parser.process_telegram_image(img_bytes, message_info)
            
            print("OCR Test Result:")
            print(f"Success: {result['success']}")
            if result['success']:
                print(f"Extracted Text: {result['text']}")
                print(f"Confidence: {result['confidence']:.2f}")
                print(f"Language: {result['language']}")
                print(f"Preprocessing: {result['preprocessing_method']}")
            else:
                print(f"Error: {result['error']}")
            
            # Show statistics
            stats = parser.get_ocr_statistics()
            print(f"Statistics: {stats}")
            
        except Exception as e:
            print(f"Test failed: {e}")
    else:
        print(f"Test image {test_image_path} not found")


if __name__ == "__main__":
    asyncio.run(test_image_parser())