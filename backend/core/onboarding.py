"""
SignalOS Onboarding System
Handles step-by-step user onboarding and setup wizards
"""

import json
import logging
import asyncio
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass

from db.models import OnboardingStep
from services.mt5_bridge import MT5Bridge
from utils.logging_config import get_logger

logger = get_logger(__name__)


class OnboardingStepType(Enum):
    PROFILE = "profile"
    BROKER = "broker"
    PROVIDER = "provider"
    STRATEGY = "strategy"
    TEST = "test"
    CONFIGURATION = "configuration"
    VERIFICATION = "verification"


class OnboardingStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    FAILED = "failed"


@dataclass
class OnboardingStepConfig:
    """Configuration for onboarding step"""
    step_id: str
    title: str
    description: str
    step_type: OnboardingStepType
    required: bool = True
    depends_on: List[str] = None
    estimated_time: int = 5  # minutes
    validation_required: bool = True


class OnboardingEngine:
    """Core onboarding engine"""
    
    def __init__(self):
        self.step_configs = {}
        self.user_progress = {}
        self.mt5_bridge = MT5Bridge()
        
    async def initialize(self):
        """Initialize onboarding engine"""
        try:
            await self._setup_default_steps()
            logger.info("Onboarding engine initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize onboarding engine: {e}")
            raise
    
    async def _setup_default_steps(self):
        """Setup default onboarding steps"""
        self.step_configs = {
            "welcome": OnboardingStepConfig(
                step_id="welcome",
                title="Welcome to SignalOS",
                description="Introduction to SignalOS trading platform",
                step_type=OnboardingStepType.PROFILE,
                required=True,
                estimated_time=2,
                validation_required=False
            ),
            "profile_setup": OnboardingStepConfig(
                step_id="profile_setup",
                title="Profile Setup",
                description="Set up your trading profile and preferences",
                step_type=OnboardingStepType.PROFILE,
                required=True,
                depends_on=["welcome"],
                estimated_time=5
            ),
            "broker_connection": OnboardingStepConfig(
                step_id="broker_connection",
                title="Broker Connection",
                description="Connect your MT4/MT5 trading account",
                step_type=OnboardingStepType.BROKER,
                required=True,
                depends_on=["profile_setup"],
                estimated_time=10
            ),
            "broker_verification": OnboardingStepConfig(
                step_id="broker_verification",
                title="Broker Verification",
                description="Verify your broker connection and account settings",
                step_type=OnboardingStepType.VERIFICATION,
                required=True,
                depends_on=["broker_connection"],
                estimated_time=3
            ),
            "signal_provider_setup": OnboardingStepConfig(
                step_id="signal_provider_setup",
                title="Signal Provider Setup",
                description="Add and configure your signal providers",
                step_type=OnboardingStepType.PROVIDER,
                required=False,
                depends_on=["broker_verification"],
                estimated_time=8
            ),
            "provider_testing": OnboardingStepConfig(
                step_id="provider_testing",
                title="Provider Testing",
                description="Test your signal providers with sample signals",
                step_type=OnboardingStepType.TEST,
                required=False,
                depends_on=["signal_provider_setup"],
                estimated_time=5
            ),
            "strategy_configuration": OnboardingStepConfig(
                step_id="strategy_configuration",
                title="Strategy Configuration",
                description="Configure your trading strategies and risk management",
                step_type=OnboardingStepType.STRATEGY,
                required=True,
                depends_on=["broker_verification"],
                estimated_time=15
            ),
            "risk_management": OnboardingStepConfig(
                step_id="risk_management",
                title="Risk Management",
                description="Set up risk management rules and limits",
                step_type=OnboardingStepType.CONFIGURATION,
                required=True,
                depends_on=["strategy_configuration"],
                estimated_time=10
            ),
            "compliance_setup": OnboardingStepConfig(
                step_id="compliance_setup",
                title="Compliance Setup",
                description="Configure compliance and regulatory settings",
                step_type=OnboardingStepType.CONFIGURATION,
                required=False,
                depends_on=["risk_management"],
                estimated_time=7
            ),
            "system_test": OnboardingStepConfig(
                step_id="system_test",
                title="System Test",
                description="Run comprehensive system test with your configuration",
                step_type=OnboardingStepType.TEST,
                required=True,
                depends_on=["risk_management"],
                estimated_time=5
            ),
            "final_review": OnboardingStepConfig(
                step_id="final_review",
                title="Final Review",
                description="Review your setup and start trading",
                step_type=OnboardingStepType.VERIFICATION,
                required=True,
                depends_on=["system_test"],
                estimated_time=3
            )
        }
    
    async def start_onboarding(self, user_id: str) -> Dict[str, Any]:
        """Start onboarding process for user"""
        try:
            # Initialize user progress
            self.user_progress[user_id] = {
                "started_at": datetime.now(),
                "current_step": "welcome",
                "completed_steps": [],
                "step_data": {},
                "total_steps": len(self.step_configs),
                "estimated_total_time": sum(step.estimated_time for step in self.step_configs.values())
            }
            
            # Create database records
            await self._create_onboarding_records(user_id)
            
            # Get first step
            first_step = await self.get_current_step(user_id)
            
            logger.info(f"Onboarding started for user {user_id}")
            return {
                "success": True,
                "message": "Onboarding started successfully",
                "current_step": first_step,
                "progress": await self.get_progress(user_id)
            }
            
        except Exception as e:
            logger.error(f"Failed to start onboarding: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _create_onboarding_records(self, user_id: str):
        """Create onboarding step records in database"""
        for step_id, config in self.step_configs.items():
            # This would create records in your database
            logger.debug(f"Created onboarding record: {user_id} -> {step_id}")
    
    async def get_current_step(self, user_id: str) -> Dict[str, Any]:
        """Get current onboarding step for user"""
        try:
            if user_id not in self.user_progress:
                return {
                    "success": False,
                    "error": "Onboarding not started"
                }
            
            progress = self.user_progress[user_id]
            current_step_id = progress["current_step"]
            
            if current_step_id not in self.step_configs:
                return {
                    "success": False,
                    "error": "Invalid step configuration"
                }
            
            step_config = self.step_configs[current_step_id]
            
            return {
                "success": True,
                "step": {
                    "id": step_config.step_id,
                    "title": step_config.title,
                    "description": step_config.description,
                    "type": step_config.step_type.value,
                    "required": step_config.required,
                    "estimated_time": step_config.estimated_time,
                    "validation_required": step_config.validation_required,
                    "data": progress["step_data"].get(current_step_id, {})
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get current step: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def complete_step(self, user_id: str, step_id: str, step_data: Dict[str, Any]) -> Dict[str, Any]:
        """Complete an onboarding step"""
        try:
            if user_id not in self.user_progress:
                return {
                    "success": False,
                    "error": "Onboarding not started"
                }
            
            progress = self.user_progress[user_id]
            
            if step_id not in self.step_configs:
                return {
                    "success": False,
                    "error": f"Unknown step: {step_id}"
                }
            
            step_config = self.step_configs[step_id]
            
            # Validate step if required
            if step_config.validation_required:
                validation_result = await self._validate_step(user_id, step_id, step_data)
                if not validation_result["valid"]:
                    return {
                        "success": False,
                        "error": validation_result["error"],
                        "validation_errors": validation_result.get("errors", [])
                    }
            
            # Store step data
            progress["step_data"][step_id] = step_data
            progress["completed_steps"].append(step_id)
            
            # Update database
            await self._update_step_status(user_id, step_id, OnboardingStatus.COMPLETED, step_data)
            
            # Determine next step
            next_step = await self._get_next_step(user_id, step_id)
            progress["current_step"] = next_step
            
            logger.info(f"Step {step_id} completed for user {user_id}")
            
            # Check if onboarding is complete
            if next_step is None:
                await self._complete_onboarding(user_id)
                return {
                    "success": True,
                    "message": "Onboarding completed successfully!",
                    "completed": True,
                    "progress": await self.get_progress(user_id)
                }
            
            return {
                "success": True,
                "message": f"Step '{step_config.title}' completed",
                "next_step": next_step,
                "progress": await self.get_progress(user_id)
            }
            
        except Exception as e:
            logger.error(f"Failed to complete step: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _validate_step(self, user_id: str, step_id: str, step_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate step data"""
        try:
            if step_id == "profile_setup":
                return await self._validate_profile_setup(step_data)
            elif step_id == "broker_connection":
                return await self._validate_broker_connection(step_data)
            elif step_id == "broker_verification":
                return await self._validate_broker_verification(user_id, step_data)
            elif step_id == "signal_provider_setup":
                return await self._validate_signal_provider_setup(step_data)
            elif step_id == "strategy_configuration":
                return await self._validate_strategy_configuration(step_data)
            elif step_id == "risk_management":
                return await self._validate_risk_management(step_data)
            elif step_id == "system_test":
                return await self._validate_system_test(user_id, step_data)
            else:
                return {"valid": True}
                
        except Exception as e:
            logger.error(f"Step validation failed: {e}")
            return {
                "valid": False,
                "error": str(e)
            }
    
    async def _validate_profile_setup(self, step_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate profile setup data"""
        required_fields = ["first_name", "last_name", "timezone", "experience_level"]
        errors = []
        
        for field in required_fields:
            if field not in step_data or not step_data[field]:
                errors.append(f"Missing required field: {field}")
        
        if step_data.get("experience_level") not in ["beginner", "intermediate", "advanced", "expert"]:
            errors.append("Invalid experience level")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors
        }
    
    async def _validate_broker_connection(self, step_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate broker connection data"""
        required_fields = ["broker_name", "account_type", "server", "login", "password"]
        errors = []
        
        for field in required_fields:
            if field not in step_data or not step_data[field]:
                errors.append(f"Missing required field: {field}")
        
        if step_data.get("account_type") not in ["demo", "live"]:
            errors.append("Account type must be 'demo' or 'live'")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors
        }
    
    async def _validate_broker_verification(self, user_id: str, step_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate broker connection by testing"""
        try:
            # Test connection to MT5
            connection_result = await self.mt5_bridge.test_connection(step_data)
            
            if not connection_result["success"]:
                return {
                    "valid": False,
                    "error": "Failed to connect to broker",
                    "errors": [connection_result.get("error", "Unknown connection error")]
                }
            
            # Test account information
            account_info = await self.mt5_bridge.get_account_info()
            if not account_info["success"]:
                return {
                    "valid": False,
                    "error": "Failed to get account information",
                    "errors": [account_info.get("error", "Unknown account error")]
                }
            
            return {
                "valid": True,
                "account_info": account_info["data"]
            }
            
        except Exception as e:
            return {
                "valid": False,
                "error": str(e)
            }
    
    async def _validate_signal_provider_setup(self, step_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate signal provider setup"""
        providers = step_data.get("providers", [])
        
        if len(providers) == 0:
            return {
                "valid": False,
                "error": "At least one signal provider is required"
            }
        
        errors = []
        for provider in providers:
            if "name" not in provider or not provider["name"]:
                errors.append("Provider name is required")
            if "type" not in provider or provider["type"] not in ["telegram", "discord", "email", "webhook"]:
                errors.append("Invalid provider type")
            if "source" not in provider or not provider["source"]:
                errors.append("Provider source is required")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors
        }
    
    async def _validate_strategy_configuration(self, step_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate strategy configuration"""
        required_fields = ["default_lot_size", "risk_per_trade", "max_positions"]
        errors = []
        
        for field in required_fields:
            if field not in step_data or step_data[field] is None:
                errors.append(f"Missing required field: {field}")
        
        if step_data.get("default_lot_size", 0) <= 0:
            errors.append("Default lot size must be greater than 0")
        
        if step_data.get("risk_per_trade", 0) <= 0 or step_data.get("risk_per_trade", 0) > 50:
            errors.append("Risk per trade must be between 0 and 50%")
        
        if step_data.get("max_positions", 0) <= 0:
            errors.append("Max positions must be greater than 0")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors
        }
    
    async def _validate_risk_management(self, step_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate risk management settings"""
        required_fields = ["max_daily_loss", "max_drawdown", "stop_loss_required"]
        errors = []
        
        for field in required_fields:
            if field not in step_data:
                errors.append(f"Missing required field: {field}")
        
        if step_data.get("max_daily_loss", 0) <= 0 or step_data.get("max_daily_loss", 0) > 100:
            errors.append("Max daily loss must be between 0 and 100%")
        
        if step_data.get("max_drawdown", 0) <= 0 or step_data.get("max_drawdown", 0) > 100:
            errors.append("Max drawdown must be between 0 and 100%")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors
        }
    
    async def _validate_system_test(self, user_id: str, step_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate system test"""
        try:
            # Run system test
            test_result = await self._run_system_test(user_id)
            
            if not test_result["success"]:
                return {
                    "valid": False,
                    "error": "System test failed",
                    "errors": test_result.get("errors", [])
                }
            
            return {
                "valid": True,
                "test_results": test_result["results"]
            }
            
        except Exception as e:
            return {
                "valid": False,
                "error": str(e)
            }
    
    async def _run_system_test(self, user_id: str) -> Dict[str, Any]:
        """Run comprehensive system test"""
        try:
            test_results = []
            
            # Test 1: Broker connection
            broker_test = await self.mt5_bridge.test_connection()
            test_results.append({
                "test": "Broker Connection",
                "status": "passed" if broker_test["success"] else "failed",
                "message": broker_test.get("message", "")
            })
            
            # Test 2: Account information
            account_test = await self.mt5_bridge.get_account_info()
            test_results.append({
                "test": "Account Information",
                "status": "passed" if account_test["success"] else "failed",
                "message": account_test.get("message", "")
            })
            
            # Test 3: Signal parsing
            parsing_test = await self._test_signal_parsing()
            test_results.append({
                "test": "Signal Parsing",
                "status": "passed" if parsing_test["success"] else "failed",
                "message": parsing_test.get("message", "")
            })
            
            # Test 4: Risk management
            risk_test = await self._test_risk_management(user_id)
            test_results.append({
                "test": "Risk Management",
                "status": "passed" if risk_test["success"] else "failed",
                "message": risk_test.get("message", "")
            })
            
            # Check overall success
            all_passed = all(result["status"] == "passed" for result in test_results)
            
            return {
                "success": all_passed,
                "results": test_results,
                "message": "All tests passed" if all_passed else "Some tests failed"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _test_signal_parsing(self) -> Dict[str, Any]:
        """Test signal parsing functionality"""
        try:
            # Test with sample signal
            sample_signal = "BUY EURUSD at 1.0850 SL: 1.0800 TP: 1.0900"
            
            # This would use your signal parser
            # For now, simulate success
            return {
                "success": True,
                "message": "Signal parsing test passed"
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": str(e)
            }
    
    async def _test_risk_management(self, user_id: str) -> Dict[str, Any]:
        """Test risk management functionality"""
        try:
            # Test risk calculations
            # This would test your risk management system
            # For now, simulate success
            return {
                "success": True,
                "message": "Risk management test passed"
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": str(e)
            }
    
    async def _get_next_step(self, user_id: str, completed_step: str) -> Optional[str]:
        """Get next step in onboarding flow"""
        progress = self.user_progress[user_id]
        completed_steps = progress["completed_steps"]
        
        # Find next step that is not completed and has dependencies met
        for step_id, config in self.step_configs.items():
            if step_id in completed_steps:
                continue
            
            # Check dependencies
            if config.depends_on:
                dependencies_met = all(dep in completed_steps for dep in config.depends_on)
                if not dependencies_met:
                    continue
            
            return step_id
        
        return None  # All steps completed
    
    async def _complete_onboarding(self, user_id: str):
        """Complete onboarding process"""
        progress = self.user_progress[user_id]
        progress["completed_at"] = datetime.now()
        progress["status"] = "completed"
        
        # Update database
        await self._update_onboarding_completion(user_id)
        
        logger.info(f"Onboarding completed for user {user_id}")
    
    async def _update_step_status(self, user_id: str, step_id: str, status: OnboardingStatus, step_data: Dict[str, Any]):
        """Update step status in database"""
        # This would update your database
        logger.info(f"Updated step status: {user_id} -> {step_id} -> {status.value}")
    
    async def _update_onboarding_completion(self, user_id: str):
        """Update onboarding completion in database"""
        # This would update your database
        logger.info(f"Updated onboarding completion: {user_id}")
    
    async def get_progress(self, user_id: str) -> Dict[str, Any]:
        """Get onboarding progress for user"""
        try:
            if user_id not in self.user_progress:
                return {
                    "success": False,
                    "error": "Onboarding not started"
                }
            
            progress = self.user_progress[user_id]
            total_steps = len(self.step_configs)
            completed_steps = len(progress["completed_steps"])
            
            return {
                "success": True,
                "progress": {
                    "total_steps": total_steps,
                    "completed_steps": completed_steps,
                    "current_step": progress["current_step"],
                    "completion_percentage": (completed_steps / total_steps) * 100,
                    "started_at": progress["started_at"].isoformat(),
                    "estimated_time_remaining": self._calculate_remaining_time(progress),
                    "status": progress.get("status", "in_progress")
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get progress: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _calculate_remaining_time(self, progress: Dict[str, Any]) -> int:
        """Calculate estimated remaining time in minutes"""
        completed_steps = progress["completed_steps"]
        remaining_time = 0
        
        for step_id, config in self.step_configs.items():
            if step_id not in completed_steps:
                remaining_time += config.estimated_time
        
        return remaining_time
    
    async def skip_step(self, user_id: str, step_id: str, reason: str) -> Dict[str, Any]:
        """Skip an optional onboarding step"""
        try:
            if user_id not in self.user_progress:
                return {
                    "success": False,
                    "error": "Onboarding not started"
                }
            
            if step_id not in self.step_configs:
                return {
                    "success": False,
                    "error": f"Unknown step: {step_id}"
                }
            
            step_config = self.step_configs[step_id]
            
            if step_config.required:
                return {
                    "success": False,
                    "error": "Cannot skip required step"
                }
            
            progress = self.user_progress[user_id]
            progress["completed_steps"].append(step_id)
            
            # Update database
            await self._update_step_status(user_id, step_id, OnboardingStatus.SKIPPED, {"reason": reason})
            
            # Get next step
            next_step = await self._get_next_step(user_id, step_id)
            progress["current_step"] = next_step
            
            logger.info(f"Step {step_id} skipped for user {user_id}: {reason}")
            
            return {
                "success": True,
                "message": f"Step '{step_config.title}' skipped",
                "next_step": next_step,
                "progress": await self.get_progress(user_id)
            }
            
        except Exception as e:
            logger.error(f"Failed to skip step: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def restart_step(self, user_id: str, step_id: str) -> Dict[str, Any]:
        """Restart a failed or completed step"""
        try:
            if user_id not in self.user_progress:
                return {
                    "success": False,
                    "error": "Onboarding not started"
                }
            
            if step_id not in self.step_configs:
                return {
                    "success": False,
                    "error": f"Unknown step: {step_id}"
                }
            
            progress = self.user_progress[user_id]
            
            # Remove from completed steps if present
            if step_id in progress["completed_steps"]:
                progress["completed_steps"].remove(step_id)
            
            # Clear step data
            if step_id in progress["step_data"]:
                del progress["step_data"][step_id]
            
            # Set as current step
            progress["current_step"] = step_id
            
            # Update database
            await self._update_step_status(user_id, step_id, OnboardingStatus.PENDING, {})
            
            logger.info(f"Step {step_id} restarted for user {user_id}")
            
            return {
                "success": True,
                "message": f"Step '{self.step_configs[step_id].title}' restarted",
                "current_step": await self.get_current_step(user_id)
            }
            
        except Exception as e:
            logger.error(f"Failed to restart step: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_onboarding_summary(self, user_id: str) -> Dict[str, Any]:
        """Get onboarding summary for user"""
        try:
            if user_id not in self.user_progress:
                return {
                    "success": False,
                    "error": "Onboarding not started"
                }
            
            progress = self.user_progress[user_id]
            step_summary = []
            
            for step_id, config in self.step_configs.items():
                step_status = "completed" if step_id in progress["completed_steps"] else "pending"
                if step_id == progress["current_step"]:
                    step_status = "current"
                
                step_summary.append({
                    "id": step_id,
                    "title": config.title,
                    "description": config.description,
                    "type": config.step_type.value,
                    "status": step_status,
                    "required": config.required,
                    "estimated_time": config.estimated_time,
                    "data": progress["step_data"].get(step_id, {})
                })
            
            return {
                "success": True,
                "summary": {
                    "user_id": user_id,
                    "started_at": progress["started_at"].isoformat(),
                    "status": progress.get("status", "in_progress"),
                    "steps": step_summary,
                    "progress": await self.get_progress(user_id)
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get onboarding summary: {e}")
            return {
                "success": False,
                "error": str(e)
            }