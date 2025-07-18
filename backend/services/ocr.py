"""
OCR Service for SignalOS Backend
Implements image-based signal extraction using EasyOCR/Tesseract
Part 2 Guide - OCR Module
"""

import io
import base64
from typing import Dict, List, Optional, Any
from PIL import Image, ImageEnhance, ImageFilter
import numpy as np
from utils.logging_config import get_logger

logger = get_logger(__name__)


class OCRResult:
    """OCR extraction result"""
    def __init__(self, text: str, confidence: float, bbox: List[int] = None):
        self.text = text
        self.confidence = confidence
        self.bbox = bbox or []


class OCRService:
    """OCR service for signal image processing"""
    
    def __init__(self):
        self.min_confidence = 0.5
        self.supported_formats = ['jpg', 'jpeg', 'png', 'bmp', 'tiff']
        self._ocr_engine = None
        
    def _get_ocr_engine(self):
        """Initialize OCR engine (lazy loading)"""
        if self._ocr_engine is None:
            try:
                # Try EasyOCR first (recommended)
                import easyocr
                self._ocr_engine = easyocr.Reader(['en'], gpu=False)
                logger.info("EasyOCR engine initialized")
            except ImportError:
                try:
                    # Fallback to Tesseract
                    import pytesseract
                    self._ocr_engine = "tesseract"
                    logger.info("Tesseract OCR engine initialized")
                except ImportError:
                    logger.warning("No OCR engine available - install easyocr or pytesseract")
                    self._ocr_engine = "mock"
        
        return self._ocr_engine
    
    def preprocess_image(self, image: Image.Image) -> Image.Image:
        """Preprocess image for better OCR accuracy"""
        try:
            # Convert to RGB if needed
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Resize if too small or too large
            width, height = image.size
            if width < 300 or height < 300:
                # Upscale small images
                scale_factor = max(300 / width, 300 / height)
                new_size = (int(width * scale_factor), int(height * scale_factor))
                image = image.resize(new_size, Image.Resampling.LANCZOS)
            elif width > 2000 or height > 2000:
                # Downscale large images
                scale_factor = min(2000 / width, 2000 / height)
                new_size = (int(width * scale_factor), int(height * scale_factor))
                image = image.resize(new_size, Image.Resampling.LANCZOS)
            
            # Enhance contrast and sharpness
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(1.5)
            
            enhancer = ImageEnhance.Sharpness(image)
            image = enhancer.enhance(1.2)
            
            # Apply slight gaussian blur to reduce noise
            image = image.filter(ImageFilter.GaussianBlur(radius=0.5))
            
            logger.debug("Image preprocessed successfully")
            return image
            
        except Exception as e:
            logger.error(f"Image preprocessing error: {e}")
            return image
    
    def extract_text_easyocr(self, image: Image.Image) -> List[OCRResult]:
        """Extract text using EasyOCR"""
        try:
            # Convert PIL image to numpy array
            img_array = np.array(image)
            
            # Run OCR
            results = self._ocr_engine.readtext(img_array)
            
            ocr_results = []
            for bbox, text, confidence in results:
                if confidence >= self.min_confidence:
                    # Convert bbox to flat list
                    bbox_flat = [int(coord) for point in bbox for coord in point]
                    ocr_results.append(OCRResult(text.strip(), confidence, bbox_flat))
            
            logger.info(f"EasyOCR extracted {len(ocr_results)} text regions")
            return ocr_results
            
        except Exception as e:
            logger.error(f"EasyOCR extraction error: {e}")
            return []
    
    def extract_text_tesseract(self, image: Image.Image) -> List[OCRResult]:
        """Extract text using Tesseract"""
        try:
            import pytesseract
            
            # Configure Tesseract for better accuracy
            config = '--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz./@:,-+$ '
            
            # Extract text with confidence
            data = pytesseract.image_to_data(image, config=config, output_type=pytesseract.Output.DICT)
            
            ocr_results = []
            for i in range(len(data['text'])):
                text = data['text'][i].strip()
                confidence = float(data['conf'][i]) / 100.0  # Convert to 0-1 range
                
                if text and confidence >= self.min_confidence:
                    bbox = [data['left'][i], data['top'][i], 
                           data['left'][i] + data['width'][i], 
                           data['top'][i] + data['height'][i]]
                    ocr_results.append(OCRResult(text, confidence, bbox))
            
            logger.info(f"Tesseract extracted {len(ocr_results)} text regions")
            return ocr_results
            
        except Exception as e:
            logger.error(f"Tesseract extraction error: {e}")
            return []
    
    def extract_text_mock(self, image: Image.Image) -> List[OCRResult]:
        """Mock OCR for testing when no engine is available"""
        logger.warning("Using mock OCR - install easyocr or pytesseract for real functionality")
        
        # Return mock signal data for testing
        mock_text = "BUY EURUSD @ 1.1000 SL: 1.0950 TP: 1.1050"
        return [OCRResult(mock_text, 0.95, [0, 0, 100, 50])]
    
    def extract_text_from_image(self, image: Image.Image) -> Dict[str, Any]:
        """Main method to extract text from image"""
        try:
            # Preprocess image
            processed_image = self.preprocess_image(image)
            
            # Get OCR engine and extract text
            engine = self._get_ocr_engine()
            
            if engine == "mock":
                ocr_results = self.extract_text_mock(processed_image)
            elif engine == "tesseract":
                ocr_results = self.extract_text_tesseract(processed_image)
            else:
                ocr_results = self.extract_text_easyocr(processed_image)
            
            # Combine all text
            full_text = " ".join([result.text for result in ocr_results])
            
            # Calculate average confidence
            if ocr_results:
                avg_confidence = sum(result.confidence for result in ocr_results) / len(ocr_results)
            else:
                avg_confidence = 0.0
            
            result = {
                "text": full_text,
                "confidence": avg_confidence,
                "regions": [
                    {
                        "text": r.text,
                        "confidence": r.confidence,
                        "bbox": r.bbox
                    } for r in ocr_results
                ],
                "total_regions": len(ocr_results),
                "engine_used": "easyocr" if hasattr(engine, 'readtext') else ("tesseract" if engine == "tesseract" else "mock")
            }
            
            logger.info(f"OCR extraction completed: {len(full_text)} chars, {avg_confidence:.2f} confidence")
            return result
            
        except Exception as e:
            logger.error(f"OCR extraction failed: {e}")
            return {
                "text": "",
                "confidence": 0.0,
                "regions": [],
                "total_regions": 0,
                "engine_used": "error",
                "error": str(e)
            }
    
    def extract_from_base64(self, base64_data: str) -> Dict[str, Any]:
        """Extract text from base64 encoded image"""
        try:
            # Remove data URL prefix if present
            if base64_data.startswith('data:image/'):
                base64_data = base64_data.split(',')[1]
            
            # Decode base64
            image_data = base64.b64decode(base64_data)
            
            # Open image
            image = Image.open(io.BytesIO(image_data))
            
            return self.extract_text_from_image(image)
            
        except Exception as e:
            logger.error(f"Base64 image processing error: {e}")
            return {
                "text": "",
                "confidence": 0.0,
                "regions": [],
                "total_regions": 0,
                "engine_used": "error",
                "error": str(e)
            }
    
    def extract_from_file(self, file_path: str) -> Dict[str, Any]:
        """Extract text from image file"""
        try:
            # Validate file format
            file_ext = file_path.lower().split('.')[-1]
            if file_ext not in self.supported_formats:
                raise ValueError(f"Unsupported format: {file_ext}")
            
            # Open image
            image = Image.open(file_path)
            
            return self.extract_text_from_image(image)
            
        except Exception as e:
            logger.error(f"File image processing error: {e}")
            return {
                "text": "",
                "confidence": 0.0,
                "regions": [],
                "total_regions": 0,
                "engine_used": "error",
                "error": str(e)
            }
    
    def validate_image(self, image_data: bytes) -> Dict[str, Any]:
        """Validate image format and size"""
        try:
            image = Image.open(io.BytesIO(image_data))
            
            return {
                "valid": True,
                "format": image.format,
                "size": image.size,
                "mode": image.mode,
                "file_size": len(image_data)
            }
            
        except Exception as e:
            logger.warning(f"Image validation failed: {e}")
            return {
                "valid": False,
                "error": str(e)
            }
    
    def set_confidence_threshold(self, threshold: float):
        """Set minimum confidence threshold for OCR results"""
        if 0.0 <= threshold <= 1.0:
            self.min_confidence = threshold
            logger.info(f"OCR confidence threshold set to {threshold}")
        else:
            logger.warning(f"Invalid confidence threshold: {threshold}")


# Global OCR service instance
ocr_service = OCRService()


def get_ocr_service() -> OCRService:
    """Get OCR service instance"""
    return ocr_service