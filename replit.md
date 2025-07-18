# SignalOS Desktop Application

## Overview

SignalOS is a comprehensive trading automation desktop application designed to outperform traditional Telegram signal copiers. It provides advanced AI-powered signal parsing, real-time trade execution, and sophisticated trading strategies with a focus on security, reliability, and performance.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Technology Stack
- **Frontend**: React/TypeScript with Tailwind CSS for modern UI
- **Backend**: Python-based trading engine with async/await patterns
- **Database**: SQLite for local data storage with JSON configuration files
- **Communication**: WebSocket and HTTP API for real-time updates
- **AI/ML**: Transformer models (Phi-3 Mini, Mistral) for signal parsing
- **Trading**: MT4/MT5 integration via socket bridge

### Architecture Pattern
The application follows a modular desktop architecture with clear separation of concerns:
- **Frontend Layer**: React-based UI with glassmorphism design
- **API Layer**: FastAPI/Flask for backend communication
- **Business Logic Layer**: Trading engines, signal processors, and strategy engines
- **Data Layer**: SQLite database with JSON configuration management
- **Integration Layer**: MT4/MT5 bridge, Telegram monitoring, and external APIs

## Key Components

### 1. Signal Processing Engine
- **AI Parser**: Hybrid LLM + regex engine for signal extraction
- **OCR Support**: EasyOCR integration for image-based signals
- **Multilingual Support**: Multiple language parsing capabilities
- **Confidence Scoring**: AI-based confidence assessment for parsed signals
- **Fallback Systems**: Regex-based fallback when AI parsing fails

### 2. Trading Execution System
- **MT5 Bridge**: Socket-based communication with MetaTrader 5
- **Trade Executor**: Async parallel execution engine
- **Risk Management**: Position sizing, margin checking, and spread validation
- **Multi-TP Support**: Multiple take profit levels with partial closure
- **Smart Entry**: Intelligent entry timing and price improvement

### 3. Strategy Engines
- **Grid Strategy**: Automated grid trading with dynamic level calculation
- **Reverse Strategy**: Contrarian trading logic with configurable conditions
- **Prop Firm Mode**: Stealth trading features for prop firm compliance
- **Break Even**: Automatic stop loss adjustment to entry price
- **Trailing Stop**: Dynamic stop loss management

### 4. Authentication & Security
- **JWT License System**: Token-based licensing with device fingerprinting
- **Telegram Auth**: OTP-based authentication via Telegram
- **Secure File Handler**: Directory traversal protection
- **Magic Number Obfuscation**: Randomized trade identifiers for stealth

### 5. Monitoring & Management
- **Telegram Monitor**: Multi-account channel monitoring
- **Signal Conflict Resolver**: Handling conflicting signals
- **Retry Engine**: Exponential backoff for failed operations
- **Auto-Updater**: Tauri-style automatic updates

## Data Flow

### Signal Processing Flow
1. **Input Reception**: Telegram messages or image signals received
2. **Pre-processing**: Text sanitization and image OCR extraction
3. **AI Parsing**: LLM-based signal extraction with confidence scoring
4. **Validation**: Signal validation and conflict resolution
5. **Strategy Routing**: Conditional routing based on market conditions
6. **Execution Planning**: Entry timing and risk calculation
7. **Trade Execution**: MT5 bridge communication and order placement
8. **Monitoring**: Real-time trade monitoring and management

### Configuration Management
- **JSON-based Config**: Centralized configuration in `config.json`
- **Module-specific Settings**: Individual config sections for each component
- **Runtime Updates**: Dynamic configuration updates without restart
- **Backup System**: Automatic configuration backup and recovery

### Error Handling
- **Graceful Degradation**: Fallback mechanisms for component failures
- **Retry Logic**: Exponential backoff with configurable limits
- **Logging System**: Comprehensive logging with multiple levels
- **Error Recovery**: Automatic recovery from common failure scenarios

## External Dependencies

### Core Libraries
- **aiohttp**: Async HTTP client/server
- **fastapi**: Modern web framework
- **transformers**: AI model integration
- **easyocr**: OCR processing
- **python-telegram-bot**: Telegram integration
- **sqlite3**: Database operations
- **jwt**: Token authentication

### Trading Integration
- **MetaTrader 5**: Via socket bridge and Expert Advisor
- **Socket Communication**: Real-time trade execution
- **Market Data**: Real-time price feeds and spread checking

### AI/ML Components
- **Phi-3 Mini**: Primary LLM for signal parsing
- **Mistral 7B**: Secondary parser for complex signals
- **spaCy**: NLP processing and entity recognition
- **scikit-learn**: Machine learning utilities

## Deployment Strategy

### Desktop Application
- **Standalone Executable**: Self-contained Python application
- **Auto-Update System**: Tauri-style update mechanism
- **Configuration Management**: Portable configuration files
- **Cross-Platform**: Windows, macOS, and Linux support

### Development Environment
- **Modular Structure**: Clear separation in `desktop-app/` directory
- **Hot Reload**: Development server with live updates
- **Testing Framework**: Pytest-based testing suite
- **Documentation**: Comprehensive inline documentation

### Production Deployment
- **License Validation**: JWT-based licensing system
- **Device Binding**: Hardware fingerprinting for security
- **Graceful Shutdown**: Proper cleanup on application exit
- **Log Management**: Rotating logs with configurable retention

### Integration Points
- **MT4/MT5 Terminal**: Socket-based bridge with Expert Advisor
- **Telegram API**: Multi-account monitoring and authentication
- **External APIs**: News feeds, market data, and update servers
- **File System**: Secure file operations with validation

The application is designed to be highly modular, secure, and performant, with extensive error handling and recovery mechanisms to ensure reliable trading automation.

## Recent Changes

### Backend Development (January 18, 2025)
- ✅ Created production-grade backend architecture in `/backend/`
- ✅ Implemented modular structure following guide requirements
- ✅ Built authentication system with JWT and licensing
- ✅ Developed AI-powered signal parsing engine with regex fallback
- ✅ Created trading execution engine with MT5 integration
- ✅ Implemented background task queue system
- ✅ Added comprehensive API endpoints (auth, signals, trading, admin)
- ✅ Created database models with SQLAlchemy
- ✅ Set up testing framework with pytest
- ✅ Added comprehensive documentation and OpenAPI specs
- ✅ Installed Python dependencies (FastAPI, Uvicorn, etc.)
- ✅ Configured environment settings and logging

### Backend Architecture
The backend follows a production-grade modular structure:
- **API Layer**: FastAPI endpoints with authentication middleware
- **Core Logic**: Authentication, licensing, and trading execution
- **Services**: AI parser with fallback mechanisms, MT5 bridge
- **Workers**: Background task processing with queue management
- **Database**: SQLAlchemy models for all entities
- **Tests**: Comprehensive unit tests for all modules
- **Documentation**: Complete API documentation and setup guides

The backend is designed as a standalone service that can integrate seamlessly with the desktop app and future web dashboard.