
# SignalOS Desktop Application - Complete Technical Documentation

## Table of Contents
1. [Architecture Overview](#architecture-overview)
2. [Core Components](#core-components)
3. [Trading Engines](#trading-engines)
4. [Risk Management Systems](#risk-management-systems)
5. [Communication & Control](#communication--control)
6. [Configuration Management](#configuration-management)
7. [Testing Framework](#testing-framework)
8. [Installation & Setup](#installation--setup)
9. [API Integration](#api-integration)
10. [File Structure](#file-structure)

---

## Architecture Overview

### Technology Stack
- **Language**: Python 3.11+
- **Core Libraries**: 
  - `MetaTrader5` - Direct MT5 platform integration
  - `asyncio` - Asynchronous programming for concurrent operations
  - `telegram` - Telegram Bot API integration
  - `requests` - HTTP client for server communication
  - `json` - Configuration and data serialization

### Design Philosophy
- **Modular Architecture**: Each trading component is a separate, testable module
- **Asynchronous Processing**: Non-blocking operations for real-time trading
- **Event-Driven**: React to market conditions and signal changes
- **Fail-Safe**: Comprehensive error handling and fallback mechanisms
- **Configurable**: JSON-based configuration for all parameters

### Application Flow
```
Signal Input → Parser → Strategy Runtime → Risk Filters → MT5 Execution → Monitoring → Sync
```

---

## Core Components

### 1. Signal Processing Pipeline

#### **Signal Parser** (`signal_parser.py`)
- **Purpose**: Convert raw Telegram signals into structured trade data
- **AI Integration**: Confidence scoring and pattern recognition
- **Input Formats**: Free-text, structured templates, multi-language support
- **Output**: Validated signal objects with metadata

```python
# Example signal parsing
signal = {
    "symbol": "EURUSD",
    "action": "BUY",
    "entry": 1.1000,
    "sl": 1.0950,
    "tp": [1.1050, 1.1100],
    "confidence": 0.85,
    "provider": "premium_signals",
    "timestamp": "2025-01-20T15:30:00Z"
}
```

#### **Strategy Runtime** (`strategy_runtime.py`)
- **Visual Strategy Builder**: Drag-and-drop strategy creation
- **Conditional Logic**: IF/THEN/ELSE strategy execution
- **Block-Based System**: Modular strategy components
- **Real-Time Evaluation**: Dynamic strategy assessment
- **Performance Tracking**: Strategy effectiveness monitoring

### 2. MT5 Integration Layer

#### **Connection Management**
- **Auto-Connect**: Automatic MT5 platform connection
- **Health Monitoring**: Real-time connection status tracking
- **Reconnection Logic**: Automatic recovery from disconnections
- **Multiple Accounts**: Support for multiple MT5 accounts

#### **Trade Execution**
- **Market Orders**: Instant execution at current prices
- **Pending Orders**: Limit and stop order placement
- **Position Management**: Open, modify, close operations
- **Bulk Operations**: Batch trade processing

---

## Trading Engines

### 1. Smart Entry System (`smart_entry_mode.py`)

#### **Intelligent Entry Execution**
- **Price Improvement**: Wait for better entry prices within tolerance
- **Spread Optimization**: Execute when spreads are favorable
- **Market Timing**: Entry based on market conditions
- **Fallback Logic**: Immediate execution if optimal conditions not met

#### **Configuration Options**
```json
{
    "smart_entry": {
        "enabled": true,
        "default_mode": "smart_wait",
        "default_wait_seconds": 300,
        "default_price_tolerance_pips": 2.0,
        "symbol_specific_settings": {
            "EURUSD": {
                "price_tolerance_pips": 1.5,
                "max_wait_seconds": 180
            }
        }
    }
}
```

### 2. Multi TP Manager (`multi_tp_manager.py`)

#### **Advanced Take Profit System**
- **Multiple TP Levels**: Up to 100 take profit levels per trade
- **Partial Closures**: Percentage-based position closing
- **Dynamic SL Shifting**: Automatic stop loss adjustments
- **Volume Distribution**: Configurable lot allocation per TP level

#### **Features**
- Break-even triggers after first TP hit
- Trailing stop integration
- Real-time monitoring with background processing
- Symbol-specific minimum volumes and slippage settings

### 3. Grid Strategy (`grid_strategy.py`)

#### **Grid Trading Implementation**
- **Dynamic Grid Levels**: Volatility-based spacing calculation
- **Bidirectional Grids**: Buy and sell grid combinations
- **Risk Management**: Maximum grid levels and exposure limits
- **Recovery Mechanisms**: Martingale and profit-taking strategies

#### **Grid Configuration**
```json
{
    "grid_strategy": {
        "enabled": true,
        "max_active_grids": 5,
        "symbol_configs": {
            "EURUSD": {
                "grid_spacing_pips": 8.0,
                "max_levels": 15,
                "base_volume": 0.01,
                "profit_target_pips": 15.0
            }
        }
    }
}
```

### 4. Reverse Strategy (`reverse_strategy.py`)

#### **Contrarian Trading Logic**
- **Full Reversals**: Complete signal direction reversal
- **Partial Reversals**: Modified lot sizes and targets
- **Market Condition Analysis**: Volatility and sentiment evaluation
- **Provider-Specific Rules**: Reverse specific signal providers

---

## Risk Management Systems

### 1. Margin Level Checker (`margin_level_checker.py`)

#### **Account Protection**
- **Real-Time Monitoring**: Continuous margin level surveillance
- **Threshold Alerts**: Warning and critical level notifications
- **Trade Blocking**: Prevent new trades at dangerous margin levels
- **Emergency Closure**: Automatic position closure for margin protection

#### **Margin Thresholds**
```json
{
    "margin_thresholds": {
        "safe_level": 300.0,
        "warning_level": 200.0,
        "critical_level": 150.0,
        "emergency_close_level": 110.0
    }
}
```

### 2. Signal Limit Enforcer (`signal_limit_enforcer.py`)

#### **Trade Frequency Control**
- **Symbol Limits**: Maximum trades per symbol per time period
- **Provider Limits**: Control trades from specific providers
- **Global Limits**: Overall trading frequency caps
- **Cooldown Periods**: Mandatory waiting periods between trades

### 3. News Filter (`news_filter.py`)

#### **Economic Event Filtering**
- **Impact-Based Filtering**: Filter by news impact level (High, Medium, Low)
- **Time Buffers**: Block trading before/after major news events
- **Multiple Sources**: ForexFactory, Investing.com integration
- **Manual Override**: Emergency trading during news periods

### 4. Spread Checker (`spread_checker.py`)

#### **Market Condition Validation**
- **Spread Thresholds**: Block trades during high spread periods
- **Symbol-Specific Rules**: Different spread limits per asset
- **Real-Time Monitoring**: Continuous spread surveillance
- **Historical Analysis**: Spread pattern tracking

---

## Communication & Control

### 1. Telegram Copilot Bot (`copilot_bot.py`)

#### **Remote Control Features**
- **Status Monitoring**: Real-time account and trade status
- **Trade Management**: View, modify, and close positions remotely
- **Signal Control**: Pause/resume signal processing
- **Emergency Controls**: Stealth mode and emergency stops

#### **Available Commands**
```
/status - MT5 and system status
/trades - Active trades overview
/signals - Recent signals
/replay <id> - Replay a signal
/stealth - Toggle stealth mode
/pause - Pause trading
/resume - Resume trading
/stats - Trading statistics
/tp status - TP management
/sl status - SL management
/close 50% - Partial position closure
```

#### **Advanced Commands**
- **TP Management**: `/tp hit 12345 1` - Manually trigger TP levels
- **SL Management**: `/sl move 12345 1.2020` - Move stop loss
- **Range Orders**: `/range 1.2000-1.2020 AVERAGE` - Entry range orders

### 2. Auto Sync (`auto_sync.py`)

#### **Server Synchronization**
- **Real-Time Updates**: Continuous data sync with web server
- **Trade History**: Complete trade record synchronization
- **Status Updates**: MT5 connection and system health
- **Configuration Sync**: Strategy and setting updates

### 3. Command Interpreter (`copilot_command_interpreter.py`)

#### **Natural Language Processing**
- **Command Parsing**: Convert natural language to system commands
- **User Authorization**: Role-based command access
- **Command History**: Track and replay previous commands
- **Parameter Extraction**: Intelligent parameter recognition

---

## Configuration Management

### 1. Main Configuration (`config.json`)

#### **Comprehensive Settings**
The configuration file contains over 15 major sections:

```json
{
    "ticket_tracker": { "enable_tracking": true },
    "smart_entry": { "enabled": true },
    "trigger_pending_order": { "enabled": true },
    "tp_sl_adjustor": { "enabled": true },
    "multi_tp_manager": { "enabled": true },
    "news_filter": { "enabled": true },
    "signal_limit_enforcer": { "enabled": true },
    "margin_level_checker": { "enabled": true },
    "reverse_strategy": { "enabled": true },
    "grid_strategy": { "enabled": true },
    "multi_signal_handler": { "enabled": true },
    "strategy_condition_router": { "enabled": true },
    "margin_filter": { "enabled": true },
    "copilot_command_interpreter": { "enabled": true },
    "copilot_alert_manager": { "enabled": true }
}
```

#### **Symbol-Specific Settings**
Each trading component supports symbol-specific configurations:

```json
{
    "symbol_specific_settings": {
        "EURUSD": {
            "price_tolerance_pips": 1.5,
            "max_wait_seconds": 180
        },
        "XAUUSD": {
            "price_tolerance_pips": 5.0,
            "max_wait_seconds": 600
        }
    }
}
```

---

## Testing Framework

### 1. Comprehensive Test Suite (`/tests/`)

#### **Test Coverage**
- **27 Test Files**: Complete coverage of all components
- **Unit Tests**: Individual component testing
- **Integration Tests**: Cross-component functionality
- **Mock Data**: Consistent test data for reliable results
- **Edge Cases**: Error conditions and boundary testing

#### **Key Test Files**
```
test_copilot_bot.py - Telegram bot functionality
test_multi_tp_manager.py - TP management system
test_margin_level_checker.py - Risk management
test_strategy_runtime.py - Strategy execution
test_smart_entry_mode.py - Entry optimization
```

### 2. Test Data Management

#### **Mock Objects**
- MT5 connection simulation
- Market data generation
- Signal data templates
- Error condition simulation

---

## Installation & Setup

### 1. Prerequisites

#### **System Requirements**
- Python 3.11 or higher
- MetaTrader 5 platform installed
- Active MT5 trading account
- Telegram Bot Token (for copilot features)
- PostgreSQL database access

### 2. Installation Steps

#### **Environment Setup**
```bash
# Install Python dependencies
pip install MetaTrader5 python-telegram-bot requests asyncio

# Configure MT5 connection
# Set up Telegram bot token
# Configure database connection
```

#### **Configuration**
1. Copy `config.json.template` to `config.json`
2. Update MT5 credentials
3. Set Telegram bot token
4. Configure server endpoints
5. Adjust trading parameters

### 3. First Run

#### **Initialization Process**
1. MT5 connection validation
2. Database schema setup
3. Telegram bot registration
4. Strategy validation
5. Risk parameter verification

---

## API Integration

### 1. Server Communication

#### **HTTP Endpoints**
```python
# Status endpoints
GET /api/mt5-status
GET /api/dashboard/stats

# Trade management
GET /api/trades/active
POST /api/trades/partial-close
POST /api/signals/{id}/replay

# TP/SL management
GET /api/trades/tp-status
POST /api/trades/tp-hit
POST /api/trades/sl-move
```

#### **WebSocket Integration**
- Real-time updates
- Live trade notifications
- Status change broadcasts
- Error alerts

### 2. External APIs

#### **News Sources**
- ForexFactory calendar integration
- Economic event filtering
- Impact level assessment

#### **Market Data**
- MT5 price feeds
- Spread monitoring
- Volatility calculations

---

## File Structure

### 1. Core Trading Files
```
copilot_bot.py - Telegram control interface
strategy_runtime.py - Strategy execution engine
smart_entry_mode.py - Entry optimization
multi_tp_manager.py - Take profit management
margin_level_checker.py - Risk management
signal_limit_enforcer.py - Trade frequency control
```

### 2. Support Files
```
auto_sync.py - Server synchronization
config.json - Main configuration
retry_engine.py - Failed trade recovery
ticket_tracker.py - Trade correlation tracking
```

### 3. Specialized Features
```
randomized_lot_inserter.py - Prop firm stealth features
end_of_week_sl_remover.py - Weekly SL management
news_filter.py - Economic event filtering
spread_checker.py - Market condition validation
```

### 4. Log Files
```
logs/multi_tp_manager_trades.json - TP execution history
logs/retry_log.json - Failed trade attempts
logs/signal_limit_enforcer_history.json - Rate limiting
logs/ticket_tracker_log.json - Trade correlations
```

---

## Key Features Summary

### **Trading Automation**
- ✅ AI-powered signal parsing with confidence scoring
- ✅ Multiple trading strategies (Grid, Reverse, Multi-signal)
- ✅ Smart entry optimization for better fill prices
- ✅ Advanced TP/SL management with up to 100 levels
- ✅ Real-time trade monitoring and modification

### **Risk Management**
- ✅ Margin level monitoring with emergency protection
- ✅ Signal frequency limiting and cooldown periods
- ✅ News event filtering and trading suspension
- ✅ Spread checking for market condition validation
- ✅ Symbol-specific risk parameters

### **Remote Control**
- ✅ Telegram bot with 15+ command types
- ✅ Natural language command interpretation
- ✅ Real-time status monitoring and alerts
- ✅ Emergency controls and stealth mode
- ✅ Comprehensive trade management commands

### **Integration & Sync**
- ✅ Real-time server synchronization
- ✅ WebSocket communication for live updates
- ✅ MT5 platform integration with health monitoring
- ✅ Multi-account support and management
- ✅ Comprehensive logging and audit trails

### **Prop Firm Features**
- ✅ Randomized lot sizing to avoid detection
- ✅ End-of-week SL removal for drawdown management
- ✅ Stealth mode for invisible TP/SL levels
- ✅ Pattern avoidance and statistical normalization

This desktop application represents a complete trading automation solution with enterprise-level features, comprehensive risk management, and advanced remote control capabilities.
