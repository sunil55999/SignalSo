#!/usr/bin/env python3
"""
Prompt-to-Config AI Assistant for SignalOS Desktop Application

Converts natural language prompts into strategy configuration JSON.
Uses AI to interpret user preferences and generate optimal strategy settings.
"""

import json
import logging
import requests
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path

# Local imports
from strategy.strategy_core import StrategyConfig, RiskParameters, BreakevenConfig, PartialCloseConfig

class PromptType(Enum):
    """Types of configuration prompts"""
    RISK_MANAGEMENT = "risk_management"
    STRATEGY_SETUP = "strategy_setup"
    BREAKEVEN_CONFIG = "breakeven_config"
    PARTIAL_CLOSE = "partial_close"
    PROP_FIRM_SETUP = "prop_firm_setup"
    GENERAL_CONFIG = "general_config"

@dataclass
class ConfigPrompt:
    """Natural language configuration prompt"""
    prompt_text: str
    prompt_type: PromptType
    user_id: Optional[str] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

@dataclass
class ConfigResponse:
    """Generated configuration response"""
    config_json: Dict[str, Any]
    confidence_score: float
    explanation: str
    warnings: List[str]
    suggestions: List[str]
    processing_time: float
    
    def __post_init__(self):
        if not hasattr(self, 'warnings') or self.warnings is None:
            self.warnings = []
        if not hasattr(self, 'suggestions') or self.suggestions is None:
            self.suggestions = []

class PromptToConfigConverter:
    """AI assistant for converting natural language to strategy configuration"""
    
    def __init__(self, config_file: str = "config.json", log_file: str = "logs/prompt_converter.log"):
        self.config_file = config_file
        self.log_file = log_file
        self.config = self._load_config()
        self._setup_logging()
        
        # AI model configuration
        self.ai_config = self.config.get('ai_model', {
            'model_name': 'phi3',
            'base_url': 'http://localhost:11434',
            'timeout': 30,
            'temperature': 0.2,
            'max_tokens': 2000
        })
        
        # Configuration templates
        self.config_templates = self._load_config_templates()
        
        # Prompt examples for training
        self.prompt_examples = self._load_prompt_examples()
        
        # Statistics
        self.stats = {
            "total_prompts": 0,
            "successful_generations": 0,
            "failed_generations": 0,
            "average_confidence": 0.0,
            "prompt_types": {}
        }
        
        self.logger.info("Prompt-to-Config converter initialized")
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration"""
        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)
                return config.get('prompt_converter', {})
        except Exception as e:
            logging.warning(f"Failed to load config: {e}")
            return {}
    
    def _setup_logging(self):
        """Setup logging"""
        self.logger = logging.getLogger('PromptConverter')
        self.logger.setLevel(logging.INFO)
        
        if not self.logger.handlers:
            Path(self.log_file).parent.mkdir(parents=True, exist_ok=True)
            
            handler = logging.FileHandler(self.log_file)
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
    
    def _load_config_templates(self) -> Dict[str, Dict[str, Any]]:
        """Load configuration templates"""
        return {
            "conservative": {
                "risk_params": {
                    "account_risk_percent": 1.0,
                    "max_daily_risk_percent": 5.0,
                    "max_drawdown_percent": 10.0,
                    "max_total_positions": 5
                },
                "breakeven_config": {
                    "enabled": True,
                    "trigger_percentage": 30.0,
                    "buffer_pips": 3.0
                },
                "partial_close_config": {
                    "enabled": True,
                    "tp1_close_percent": 70.0,
                    "tp2_close_percent": 25.0,
                    "tp3_close_percent": 5.0
                }
            },
            "balanced": {
                "risk_params": {
                    "account_risk_percent": 2.0,
                    "max_daily_risk_percent": 10.0,
                    "max_drawdown_percent": 20.0,
                    "max_total_positions": 10
                },
                "breakeven_config": {
                    "enabled": True,
                    "trigger_percentage": 50.0,
                    "buffer_pips": 2.0
                },
                "partial_close_config": {
                    "enabled": True,
                    "tp1_close_percent": 50.0,
                    "tp2_close_percent": 30.0,
                    "tp3_close_percent": 20.0
                }
            },
            "aggressive": {
                "risk_params": {
                    "account_risk_percent": 3.0,
                    "max_daily_risk_percent": 15.0,
                    "max_drawdown_percent": 30.0,
                    "max_total_positions": 15
                },
                "breakeven_config": {
                    "enabled": True,
                    "trigger_percentage": 60.0,
                    "buffer_pips": 1.0
                },
                "partial_close_config": {
                    "enabled": True,
                    "tp1_close_percent": 30.0,
                    "tp2_close_percent": 30.0,
                    "tp3_close_percent": 40.0
                }
            }
        }
    
    def _load_prompt_examples(self) -> List[Dict[str, str]]:
        """Load example prompts for training"""
        return [
            {
                "prompt": "I want to risk 2% per trade with conservative position sizing",
                "type": "risk_management",
                "config": json.dumps({"risk_params": {"account_risk_percent": 2.0}})
            },
            {
                "prompt": "Set up breakeven when price moves 50% to first target",
                "type": "breakeven_config",
                "config": json.dumps({"breakeven_config": {"enabled": True, "trigger_percentage": 50.0}})
            },
            {
                "prompt": "Close 60% at TP1, 30% at TP2, keep 10% running",
                "type": "partial_close",
                "config": json.dumps({"partial_close_config": {"tp1_close_percent": 60.0, "tp2_close_percent": 30.0, "tp3_close_percent": 10.0}})
            },
            {
                "prompt": "Use aggressive strategy with 5% risk per trade",
                "type": "strategy_setup",
                "config": json.dumps({"strategy_type": "aggressive", "risk_params": {"account_risk_percent": 5.0}})
            }
        ]
    
    async def convert_prompt(self, prompt: ConfigPrompt) -> ConfigResponse:
        """
        Convert natural language prompt to configuration
        
        Args:
            prompt: ConfigPrompt object with natural language request
            
        Returns:
            ConfigResponse with generated configuration
        """
        start_time = datetime.now()
        self.stats["total_prompts"] += 1
        
        # Track prompt type
        prompt_type_key = prompt.prompt_type.value
        self.stats["prompt_types"][prompt_type_key] = self.stats["prompt_types"].get(prompt_type_key, 0) + 1
        
        try:
            # Generate configuration using AI
            ai_response = await self._generate_config_with_ai(prompt)
            
            if ai_response:
                # Validate and enhance the configuration
                validated_config = self._validate_and_enhance_config(ai_response, prompt.prompt_type)
                
                # Calculate confidence score
                confidence_score = self._calculate_confidence_score(validated_config, prompt)
                
                # Generate explanation and suggestions
                explanation = self._generate_explanation(validated_config, prompt.prompt_text)
                warnings = self._generate_warnings(validated_config)
                suggestions = self._generate_suggestions(validated_config)
                
                processing_time = (datetime.now() - start_time).total_seconds()
                
                response = ConfigResponse(
                    config_json=validated_config,
                    confidence_score=confidence_score,
                    explanation=explanation,
                    warnings=warnings,
                    suggestions=suggestions,
                    processing_time=processing_time
                )
                
                self.stats["successful_generations"] += 1
                self.stats["average_confidence"] = (
                    (self.stats["average_confidence"] * (self.stats["successful_generations"] - 1) + confidence_score) /
                    self.stats["successful_generations"]
                )
                
                self.logger.info(f"Successfully generated config with confidence: {confidence_score:.2f}")
                return response
            
            else:
                # Fallback to template-based generation
                return self._generate_fallback_config(prompt)
                
        except Exception as e:
            self.stats["failed_generations"] += 1
            self.logger.error(f"Failed to convert prompt: {e}")
            return self._generate_error_response(prompt, str(e))
    
    async def _generate_config_with_ai(self, prompt: ConfigPrompt) -> Optional[Dict[str, Any]]:
        """Generate configuration using AI model"""
        try:
            # Prepare system prompt
            system_prompt = self._create_system_prompt(prompt.prompt_type)
            
            # Prepare user prompt with examples
            user_prompt = self._create_user_prompt(prompt.prompt_text, prompt.prompt_type)
            
            # Make API request
            payload = {
                "model": self.ai_config['model_name'],
                "prompt": f"{system_prompt}\n\n{user_prompt}",
                "stream": False,
                "options": {
                    "temperature": self.ai_config['temperature'],
                    "num_predict": self.ai_config['max_tokens']
                }
            }
            
            response = requests.post(
                f"{self.ai_config['base_url']}/api/generate",
                json=payload,
                timeout=self.ai_config['timeout']
            )
            
            if response.status_code == 200:
                ai_response = response.json()
                ai_output = ai_response.get('response', '')
                
                # Parse JSON from AI response
                return self._parse_ai_json_response(ai_output)
            
            else:
                self.logger.warning(f"AI API request failed: {response.status_code}")
                return None
                
        except Exception as e:
            self.logger.error(f"AI generation error: {e}")
            return None
    
    def _create_system_prompt(self, prompt_type: PromptType) -> str:
        """Create system prompt for AI model"""
        base_prompt = """You are a professional trading strategy configuration assistant. 
        Your job is to convert natural language requests into valid JSON configuration for trading strategies.
        
        Always respond with valid JSON only. Do not include explanations or markdown formatting.
        
        Available configuration sections:
        - risk_params: account_risk_percent, max_daily_risk_percent, max_drawdown_percent, max_total_positions
        - breakeven_config: enabled, trigger_percentage, buffer_pips, min_profit_pips
        - partial_close_config: enabled, tp1_close_percent, tp2_close_percent, tp3_close_percent
        - strategy_type: conservative, balanced, aggressive
        - prop_firm_mode: boolean for prop firm trading rules
        """
        
        type_specific_prompts = {
            PromptType.RISK_MANAGEMENT: "Focus on risk_params section. Set appropriate risk percentages and position limits.",
            PromptType.BREAKEVEN_CONFIG: "Focus on breakeven_config section. Configure breakeven trigger and buffer settings.",
            PromptType.PARTIAL_CLOSE: "Focus on partial_close_config section. Set appropriate close percentages for each TP level.",
            PromptType.STRATEGY_SETUP: "Configure overall strategy type and main parameters.",
            PromptType.PROP_FIRM_SETUP: "Configure prop firm specific settings with conservative risk management."
        }
        
        return f"{base_prompt}\n\n{type_specific_prompts.get(prompt_type, 'Configure general trading strategy settings.')}"
    
    def _create_user_prompt(self, prompt_text: str, prompt_type: PromptType) -> str:
        """Create user prompt with examples"""
        examples = [ex for ex in self.prompt_examples if ex['type'] == prompt_type.value]
        
        example_text = ""
        if examples:
            example_text = "Examples:\n"
            for ex in examples[:2]:  # Show max 2 examples
                example_text += f"Input: {ex['prompt']}\nOutput: {ex['config']}\n\n"
        
        return f"{example_text}Input: {prompt_text}\nOutput:"
    
    def _parse_ai_json_response(self, ai_output: str) -> Optional[Dict[str, Any]]:
        """Parse JSON from AI response"""
        try:
            # Clean AI response
            cleaned_output = ai_output.strip()
            
            # Find JSON boundaries
            json_start = cleaned_output.find('{')
            json_end = cleaned_output.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = cleaned_output[json_start:json_end]
                return json.loads(json_str)
            
            return None
            
        except json.JSONDecodeError as e:
            self.logger.warning(f"Failed to parse AI JSON response: {e}")
            return None
    
    def _validate_and_enhance_config(self, config: Dict[str, Any], prompt_type: PromptType) -> Dict[str, Any]:
        """Validate and enhance generated configuration"""
        validated_config = config.copy()
        
        # Apply validation rules based on prompt type
        if prompt_type == PromptType.RISK_MANAGEMENT:
            if 'risk_params' in validated_config:
                risk_params = validated_config['risk_params']
                
                # Ensure risk percentages are within reasonable bounds
                if 'account_risk_percent' in risk_params:
                    risk_params['account_risk_percent'] = max(0.1, min(risk_params['account_risk_percent'], 10.0))
                
                if 'max_daily_risk_percent' in risk_params:
                    risk_params['max_daily_risk_percent'] = max(1.0, min(risk_params['max_daily_risk_percent'], 50.0))
                
                if 'max_drawdown_percent' in risk_params:
                    risk_params['max_drawdown_percent'] = max(5.0, min(risk_params['max_drawdown_percent'], 80.0))
        
        elif prompt_type == PromptType.BREAKEVEN_CONFIG:
            if 'breakeven_config' in validated_config:
                breakeven_config = validated_config['breakeven_config']
                
                # Ensure trigger percentage is reasonable
                if 'trigger_percentage' in breakeven_config:
                    breakeven_config['trigger_percentage'] = max(10.0, min(breakeven_config['trigger_percentage'], 100.0))
                
                # Ensure buffer pips are positive
                if 'buffer_pips' in breakeven_config:
                    breakeven_config['buffer_pips'] = max(0.0, breakeven_config['buffer_pips'])
        
        elif prompt_type == PromptType.PARTIAL_CLOSE:
            if 'partial_close_config' in validated_config:
                partial_config = validated_config['partial_close_config']
                
                # Ensure close percentages add up to 100% or less
                total_percent = 0
                for key in ['tp1_close_percent', 'tp2_close_percent', 'tp3_close_percent']:
                    if key in partial_config:
                        partial_config[key] = max(0.0, min(partial_config[key], 100.0))
                        total_percent += partial_config[key]
                
                # Adjust if total exceeds 100%
                if total_percent > 100.0:
                    adjustment_factor = 100.0 / total_percent
                    for key in ['tp1_close_percent', 'tp2_close_percent', 'tp3_close_percent']:
                        if key in partial_config:
                            partial_config[key] *= adjustment_factor
        
        return validated_config
    
    def _calculate_confidence_score(self, config: Dict[str, Any], prompt: ConfigPrompt) -> float:
        """Calculate confidence score for generated configuration"""
        score = 0.0
        max_score = 0.0
        
        # Check completeness
        if config:
            score += 0.3
        max_score += 0.3
        
        # Check for relevant configuration sections
        relevant_sections = self._get_relevant_sections(prompt.prompt_type)
        for section in relevant_sections:
            if section in config:
                score += 0.4
            max_score += 0.4
        
        # Check for valid values
        if self._has_valid_values(config):
            score += 0.3
        max_score += 0.3
        
        return score / max_score if max_score > 0 else 0.0
    
    def _get_relevant_sections(self, prompt_type: PromptType) -> List[str]:
        """Get relevant configuration sections for prompt type"""
        section_map = {
            PromptType.RISK_MANAGEMENT: ['risk_params'],
            PromptType.BREAKEVEN_CONFIG: ['breakeven_config'],
            PromptType.PARTIAL_CLOSE: ['partial_close_config'],
            PromptType.STRATEGY_SETUP: ['strategy_type', 'risk_params'],
            PromptType.PROP_FIRM_SETUP: ['prop_firm_mode', 'risk_params']
        }
        
        return section_map.get(prompt_type, [])
    
    def _has_valid_values(self, config: Dict[str, Any]) -> bool:
        """Check if configuration has valid values"""
        try:
            # Check for common invalid values
            config_str = json.dumps(config)
            invalid_indicators = ['null', 'undefined', 'NaN', '""', '[]', '{}']
            
            return not any(indicator in config_str for indicator in invalid_indicators)
        except:
            return False
    
    def _generate_explanation(self, config: Dict[str, Any], prompt_text: str) -> str:
        """Generate explanation for the generated configuration"""
        explanations = []
        
        if 'risk_params' in config:
            risk_params = config['risk_params']
            if 'account_risk_percent' in risk_params:
                explanations.append(f"Risk per trade set to {risk_params['account_risk_percent']:.1f}%")
        
        if 'breakeven_config' in config:
            breakeven_config = config['breakeven_config']
            if breakeven_config.get('enabled'):
                trigger = breakeven_config.get('trigger_percentage', 50)
                explanations.append(f"Breakeven triggers at {trigger}% to first target")
        
        if 'partial_close_config' in config:
            partial_config = config['partial_close_config']
            if partial_config.get('enabled'):
                tp1 = partial_config.get('tp1_close_percent', 50)
                explanations.append(f"Partial close: {tp1}% at TP1")
        
        if not explanations:
            explanations.append("Configuration generated based on your request")
        
        return ". ".join(explanations) + "."
    
    def _generate_warnings(self, config: Dict[str, Any]) -> List[str]:
        """Generate warnings for the configuration"""
        warnings = []
        
        if 'risk_params' in config:
            risk_params = config['risk_params']
            if risk_params.get('account_risk_percent', 0) > 5.0:
                warnings.append("High risk per trade (>5%) - consider reducing for better risk management")
            
            if risk_params.get('max_daily_risk_percent', 0) > 20.0:
                warnings.append("High daily risk limit (>20%) - consider prop firm requirements")
        
        return warnings
    
    def _generate_suggestions(self, config: Dict[str, Any]) -> List[str]:
        """Generate suggestions for the configuration"""
        suggestions = []
        
        if 'breakeven_config' in config and not config['breakeven_config'].get('enabled', False):
            suggestions.append("Consider enabling breakeven to protect profits")
        
        if 'partial_close_config' in config and not config['partial_close_config'].get('enabled', False):
            suggestions.append("Consider enabling partial closes to lock in profits")
        
        return suggestions
    
    def _generate_fallback_config(self, prompt: ConfigPrompt) -> ConfigResponse:
        """Generate fallback configuration when AI fails"""
        # Use template-based approach
        if "conservative" in prompt.prompt_text.lower():
            template = "conservative"
        elif "aggressive" in prompt.prompt_text.lower():
            template = "aggressive"
        else:
            template = "balanced"
        
        config = self.config_templates[template].copy()
        
        return ConfigResponse(
            config_json=config,
            confidence_score=0.6,
            explanation=f"Generated {template} configuration based on template",
            warnings=["AI generation failed - using template configuration"],
            suggestions=["Customize the configuration based on your specific needs"],
            processing_time=0.1
        )
    
    def _generate_error_response(self, prompt: ConfigPrompt, error: str) -> ConfigResponse:
        """Generate error response when configuration fails"""
        return ConfigResponse(
            config_json={},
            confidence_score=0.0,
            explanation="Failed to generate configuration",
            warnings=[f"Configuration generation failed: {error}"],
            suggestions=["Please rephrase your request or use manual configuration"],
            processing_time=0.0
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """Get converter statistics"""
        return self.stats.copy()

# Example usage
if __name__ == "__main__":
    import asyncio
    
    async def main():
        converter = PromptToConfigConverter()
        
        # Test prompts
        test_prompts = [
            ConfigPrompt("I want to risk 2% per trade with breakeven at 50%", PromptType.RISK_MANAGEMENT),
            ConfigPrompt("Set up aggressive strategy with 5% risk", PromptType.STRATEGY_SETUP),
            ConfigPrompt("Close 60% at TP1, 30% at TP2, keep 10% running", PromptType.PARTIAL_CLOSE)
        ]
        
        for prompt in test_prompts:
            response = await converter.convert_prompt(prompt)
            print(f"Prompt: {prompt.prompt_text}")
            print(f"Config: {json.dumps(response.config_json, indent=2)}")
            print(f"Confidence: {response.confidence_score:.2f}")
            print(f"Explanation: {response.explanation}")
            print("---")
    
    asyncio.run(main())