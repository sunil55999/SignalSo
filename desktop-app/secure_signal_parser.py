#!/usr/bin/env python3
"""
Secure Signal Parser - Main interface
"""

from parser.multilingual_parser import MultilingualSignalParser
from parser.ocr_engine import OCREngine

class SecureSignalParser:
    """Secure signal parser combining OCR and multilingual parsing"""
    
    def __init__(self, config_file: str = "config.json"):
        self.config_file = config_file
        self.multilingual_parser = MultilingualSignalParser(config_file)
        self.ocr_engine = OCREngine(config_file)
        
    def parse_text_signal(self, text: str):
        """Parse text signal"""
        return self.multilingual_parser.parse_signal(text)
        
    def parse_image_signal(self, image_data: bytes):
        """Parse image signal using OCR"""
        ocr_result = self.ocr_engine.process_image(image_data)
        if ocr_result.processed_signal:
            return ocr_result.processed_signal
        return None
        
    def get_statistics(self):
        """Get parser statistics"""
        return {
            "multilingual": self.multilingual_parser.get_statistics(),
            "ocr": self.ocr_engine.get_statistics()
        }