"""
Central Parse Controller for SignalOS Backend
Implements Part 2 Guide - Central controller for parsing flow
"""

import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from enum import Enum
from pydantic import BaseModel

from services.parser_ai import AISignalParser
from services.ocr import OCRService, get_ocr_service
from utils.logging_config import get_logger

logger = get_logger(__name__)


class ParseType(str, Enum):
    """Parse input type"""
    TEXT = "text"
    IMAGE = "image"
    MIXED = "mixed"


class ParseMethod(str, Enum):
    """Parse method used"""
    AI_PRIMARY = "ai_primary"
    AI_SECONDARY = "ai_secondary"
    REGEX_FALLBACK = "regex_fallback"
    OCR_AI = "ocr_ai"
    OCR_REGEX = "ocr_regex"


class ParseRequest(BaseModel):
    """Parse request model"""
    request_id: str
    text: Optional[str] = None
    image_data: Optional[str] = None  # base64 encoded
    image_file: Optional[str] = None  # file path
    parse_type: ParseType
    user_id: str
    device_id: str
    auto_execute: bool = False
    confidence_threshold: float = 0.7


class ParseResult(BaseModel):
    """Parse result model"""
    request_id: str
    success: bool
    parsed_signal: Optional[Dict[str, Any]] = None
    confidence: float
    method_used: ParseMethod
    ocr_result: Optional[Dict[str, Any]] = None
    processing_time: float
    error: Optional[str] = None
    feedback_id: Optional[str] = None


class ParseFeedback(BaseModel):
    """User feedback on parse result"""
    feedback_id: str
    request_id: str
    user_id: str
    is_correct: bool
    corrected_signal: Optional[Dict[str, Any]] = None
    feedback_text: Optional[str] = None
    created_at: datetime


class CentralParseController:
    """Central controller for all parsing operations"""
    
    def __init__(self):
        self.ai_parser = AISignalParser()
        self.ocr_service = get_ocr_service()
        self.parse_history: Dict[str, ParseResult] = {}  # In production, use database
        self.feedback_history: Dict[str, ParseFeedback] = {}  # In production, use database
        self.performance_stats = {
            "total_requests": 0,
            "successful_parses": 0,
            "ai_primary_success": 0,
            "ai_secondary_success": 0,
            "regex_fallback_used": 0,
            "ocr_requests": 0,
            "average_confidence": 0.0,
            "average_processing_time": 0.0
        }
    
    def parse_signal(self, request: ParseRequest) -> ParseResult:
        """Main parsing method - implements Part 2 parsing flow"""
        start_time = datetime.utcnow()
        request_id = request.request_id or str(uuid.uuid4())
        
        try:
            logger.info(f"Starting parse request {request_id}, type: {request.parse_type}")
            
            # Step 1: Handle different input types
            if request.parse_type == ParseType.TEXT:
                result = self._parse_text_signal(request, request_id)
            elif request.parse_type == ParseType.IMAGE:
                result = self._parse_image_signal(request, request_id)
            elif request.parse_type == ParseType.MIXED:
                result = self._parse_mixed_signal(request, request_id)
            else:
                raise ValueError(f"Unknown parse type: {request.parse_type}")
            
            # Calculate processing time
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            result.processing_time = processing_time
            
            # Store result
            self.parse_history[request_id] = result
            
            # Update stats
            self._update_stats(result)
            
            logger.info(f"Parse request {request_id} completed: {result.success}, "
                       f"confidence: {result.confidence:.2f}, time: {processing_time:.2f}s")
            
            return result
            
        except Exception as e:
            logger.error(f"Parse request {request_id} failed: {e}")
            
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            
            error_result = ParseResult(
                request_id=request_id,
                success=False,
                confidence=0.0,
                method_used=ParseMethod.REGEX_FALLBACK,
                processing_time=processing_time,
                error=str(e)
            )
            
            self.parse_history[request_id] = error_result
            return error_result
    
    def _parse_text_signal(self, request: ParseRequest, request_id: str) -> ParseResult:
        """Parse text-based signal"""
        if not request.text:
            raise ValueError("Text is required for text parsing")
        
        # Step 1: Try AI primary parser
        ai_result = self.ai_parser.parse_signal_advanced(request.text)
        
        if ai_result["success"] and ai_result["confidence"] >= request.confidence_threshold:
            return ParseResult(
                request_id=request_id,
                success=True,
                parsed_signal=ai_result["parsed_signal"],
                confidence=ai_result["confidence"],
                method_used=ParseMethod.AI_PRIMARY,
                processing_time=0.0  # Will be set by caller
            )
        
        # Step 2: Try AI secondary parser (different model/approach)
        ai_secondary = self.ai_parser.parse_with_fallback(request.text)
        
        if ai_secondary["success"] and ai_secondary["confidence"] >= request.confidence_threshold:
            return ParseResult(
                request_id=request_id,
                success=True,
                parsed_signal=ai_secondary["parsed_signal"],
                confidence=ai_secondary["confidence"],
                method_used=ParseMethod.AI_SECONDARY,
                processing_time=0.0
            )
        
        # Step 3: Regex fallback
        regex_result = self.ai_parser.parse_with_regex(request.text)
        
        return ParseResult(
            request_id=request_id,
            success=regex_result["success"],
            parsed_signal=regex_result.get("parsed_signal"),
            confidence=regex_result.get("confidence", 0.5),
            method_used=ParseMethod.REGEX_FALLBACK,
            processing_time=0.0
        )
    
    def _parse_image_signal(self, request: ParseRequest, request_id: str) -> ParseResult:
        """Parse image-based signal"""
        # Step 1: OCR extraction
        if request.image_data:
            ocr_result = self.ocr_service.extract_from_base64(request.image_data)
        elif request.image_file:
            ocr_result = self.ocr_service.extract_from_file(request.image_file)
        else:
            raise ValueError("Image data or file path is required for image parsing")
        
        if not ocr_result["text"] or ocr_result["confidence"] < 0.3:
            return ParseResult(
                request_id=request_id,
                success=False,
                confidence=ocr_result["confidence"],
                method_used=ParseMethod.OCR_REGEX,
                ocr_result=ocr_result,
                error="OCR extraction failed or low confidence",
                processing_time=0.0
            )
        
        # Step 2: Parse OCR text with AI
        ai_result = self.ai_parser.parse_signal_advanced(ocr_result["text"])
        
        if ai_result["success"] and ai_result["confidence"] >= request.confidence_threshold:
            return ParseResult(
                request_id=request_id,
                success=True,
                parsed_signal=ai_result["parsed_signal"],
                confidence=min(ai_result["confidence"], ocr_result["confidence"]),
                method_used=ParseMethod.OCR_AI,
                ocr_result=ocr_result,
                processing_time=0.0
            )
        
        # Step 3: Parse OCR text with regex
        regex_result = self.ai_parser.parse_with_regex(ocr_result["text"])
        
        return ParseResult(
            request_id=request_id,
            success=regex_result["success"],
            parsed_signal=regex_result.get("parsed_signal"),
            confidence=min(regex_result.get("confidence", 0.5), ocr_result["confidence"]),
            method_used=ParseMethod.OCR_REGEX,
            ocr_result=ocr_result,
            processing_time=0.0
        )
    
    def _parse_mixed_signal(self, request: ParseRequest, request_id: str) -> ParseResult:
        """Parse mixed text and image signal"""
        results = []
        
        # Parse text if provided
        if request.text:
            text_request = ParseRequest(
                request_id=f"{request_id}_text",
                text=request.text,
                parse_type=ParseType.TEXT,
                user_id=request.user_id,
                device_id=request.device_id,
                confidence_threshold=request.confidence_threshold
            )
            text_result = self._parse_text_signal(text_request, f"{request_id}_text")
            results.append(text_result)
        
        # Parse image if provided
        if request.image_data or request.image_file:
            image_request = ParseRequest(
                request_id=f"{request_id}_image",
                image_data=request.image_data,
                image_file=request.image_file,
                parse_type=ParseType.IMAGE,
                user_id=request.user_id,
                device_id=request.device_id,
                confidence_threshold=request.confidence_threshold
            )
            image_result = self._parse_image_signal(image_request, f"{request_id}_image")
            results.append(image_result)
        
        if not results:
            raise ValueError("No valid input provided for mixed parsing")
        
        # Choose best result
        successful_results = [r for r in results if r.success]
        
        if successful_results:
            best_result = max(successful_results, key=lambda x: x.confidence)
            best_result.request_id = request_id
            return best_result
        else:
            # Return the result with highest confidence even if failed
            best_result = max(results, key=lambda x: x.confidence)
            best_result.request_id = request_id
            return best_result
    
    def submit_feedback(self, feedback: ParseFeedback) -> bool:
        """Submit user feedback for training"""
        try:
            feedback_id = feedback.feedback_id or str(uuid.uuid4())
            feedback.feedback_id = feedback_id
            
            # Store feedback
            self.feedback_history[feedback_id] = feedback
            
            # Update AI parser with feedback (for training)
            if feedback.is_correct:
                self.ai_parser.record_successful_parse(
                    request_id=feedback.request_id,
                    feedback=feedback.feedback_text
                )
            else:
                self.ai_parser.record_failed_parse(
                    request_id=feedback.request_id,
                    corrected_signal=feedback.corrected_signal,
                    feedback=feedback.feedback_text
                )
            
            logger.info(f"Feedback submitted: {feedback_id}, correct: {feedback.is_correct}")
            return True
            
        except Exception as e:
            logger.error(f"Feedback submission failed: {e}")
            return False
    
    def get_parse_result(self, request_id: str) -> Optional[ParseResult]:
        """Get parse result by request ID"""
        return self.parse_history.get(request_id)
    
    def get_user_parse_history(self, user_id: str, limit: int = 50) -> List[ParseResult]:
        """Get parse history for user"""
        user_results = [
            result for result in self.parse_history.values()
            if hasattr(result, 'user_id') and result.user_id == user_id  # Note: Need to add user_id to ParseResult
        ]
        return sorted(user_results, key=lambda x: x.request_id, reverse=True)[:limit]
    
    def get_feedback_history(self, user_id: str) -> List[ParseFeedback]:
        """Get feedback history for user"""
        return [
            feedback for feedback in self.feedback_history.values()
            if feedback.user_id == user_id
        ]
    
    def _update_stats(self, result: ParseResult):
        """Update performance statistics"""
        self.performance_stats["total_requests"] += 1
        
        if result.success:
            self.performance_stats["successful_parses"] += 1
            
            if result.method_used == ParseMethod.AI_PRIMARY:
                self.performance_stats["ai_primary_success"] += 1
            elif result.method_used == ParseMethod.AI_SECONDARY:
                self.performance_stats["ai_secondary_success"] += 1
            elif result.method_used in [ParseMethod.REGEX_FALLBACK, ParseMethod.OCR_REGEX]:
                self.performance_stats["regex_fallback_used"] += 1
        
        if result.ocr_result:
            self.performance_stats["ocr_requests"] += 1
        
        # Update rolling averages
        total = self.performance_stats["total_requests"]
        self.performance_stats["average_confidence"] = (
            (self.performance_stats["average_confidence"] * (total - 1) + result.confidence) / total
        )
        self.performance_stats["average_processing_time"] = (
            (self.performance_stats["average_processing_time"] * (total - 1) + result.processing_time) / total
        )
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        total = self.performance_stats["total_requests"]
        if total == 0:
            return self.performance_stats
        
        stats = self.performance_stats.copy()
        stats["success_rate"] = stats["successful_parses"] / total
        stats["ai_primary_rate"] = stats["ai_primary_success"] / total
        stats["ai_secondary_rate"] = stats["ai_secondary_success"] / total
        stats["regex_fallback_rate"] = stats["regex_fallback_used"] / total
        stats["ocr_usage_rate"] = stats["ocr_requests"] / total if total > 0 else 0
        
        return stats
    
    def cleanup_old_results(self, days: int = 30):
        """Clean up old parse results"""
        # In production, implement database cleanup
        logger.info(f"Would clean up parse results older than {days} days")


# Global parse controller instance
parse_controller = CentralParseController()


def get_parse_controller() -> CentralParseController:
    """Get parse controller instance"""
    return parse_controller