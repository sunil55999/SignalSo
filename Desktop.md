
# SignalOS Desktop Application - Complete Feature Documentation

## 📋 Overview

The SignalOS Desktop Application is a comprehensive Python-based trading automation system that serves as the bridge between Telegram signals and MetaTrader 5 execution. It handles signal parsing, trade execution, risk management, and real-time synchronization with the web dashboard.

## 🏗️ Core Architecture

### Main Components
- **Signal Processing Engine**: AI-powered signal parsing with confidence scoring
- **MT5 Bridge**: Direct MetaTrader 5 integration for trade execution
- **Strategy Runtime**: Visual strategy execution engine with conditional logic
- **Sync Engine**: Real-time synchronization with web dashboard
- **Telegram Copilot**: Remote control and monitoring via Telegram bot
- **Risk Management**: Multi-layered risk protection and margin monitoring

## 🚀 Complete Feature Set

### 1. Signal Processing & Parsing
- **AI-Powered Parser** (`parser.py`): Advanced signal parsing with confidence scoring
- **Secure Signal Parser** (`secure_signal_parser.py`): Input sanitization and pattern detection
- **Multi-Format Support**: Standard, compact, and multi-TP signal formats
- **Conflict Resolution** (`signal_conflict_resolver.py`): Thread-safe signal processing
- **Signal Simulation** (`signal_simulator.py`): Test signals without real execution

### 2. MetaTrader 5 Integration
- **MT5 Bridge** (`mt5_bridge.py`): Direct MT5 API integration
- **Secure MT5 Bridge** (`secure_mt5_bridge.py`): Enhanced security with trading limits
- **Magic Number Management** (`magic_number_hider.py`): Hide/show trade identifiers
- **Symbol Mapping** (`symbol_mapper.py`): Automatic symbol conversion between platforms
- **Spread Checking** (`spread_checker.py`): Real-time spread monitoring and filtering

### 3. Advanced Order Management
- **Smart Entry Mode** (`smart_entry_mode.py`): Intelligent market entry timing
- **Trigger Pending Orders** (`trigger_pending_order.py`): Conditional order execution
- **Multi-TP Manager** (`multi_tp_manager.py`): Multiple take-profit level management
- **Partial Close** (`partial_close.py`): Gradual position closure
- **Entry Range Handler** (`entrypoint_range_handler.py`): Price range-based entries

### 4. Risk Management Systems
- **Margin Level Checker** (`margin_level_checker.py`): Real-time margin monitoring
- **Margin Filter Block** (`blocks/margin_filter.py`): Trade filtering based on margin
- **Signal Limit Enforcer** (`signal_limit_enforcer.py`): Daily/hourly signal limits
- **Risk/Reward Converter** (`rr_converter.py`): Automatic R:R ratio adjustments
- **Lot Size Engine** (`lotsize_engine.py`): Dynamic position sizing

### 5. Stop Loss & Take Profit Management
- **SL Manager** (`sl_manager.py`): Stop loss management and adjustment
- **TP Manager** (`tp_manager.py`): Take profit level management
- **TP/SL Adjustor** (`tp_sl_adjustor.py`): Dynamic SL/TP adjustments
- **Break Even** (`break_even.py`): Automatic break-even functionality
- **Trailing Stop** (`trailing_stop.py`): Dynamic trailing stop loss
- **End of Week SL Remover** (`end_of_week_sl_remover.py`): Weekend SL management

### 6. Advanced Trading Strategies
- **Strategy Runtime** (`strategy_runtime.py`): Visual strategy execution engine
- **Strategy Condition Router** (`strategy_condition_router.py`): Conditional strategy routing
- **Grid Strategy** (`grid_strategy.py`): Grid trading implementation
- **Reverse Strategy** (`reverse_strategy.py`): Contrarian trading logic
- **Multi-Signal Handler** (`multi_signal_handler.py`): Multiple signal coordination

### 7. News & Market Filters
- **News Filter** (`news_filter.py`): Economic news-based trade filtering
- **Time Scheduler** (`time_scheduler.py`): Time-based trading restrictions
- **Market Session Management**: Asian, European, American session handling

### 8. Position & Trade Management
- **Ticket Tracker** (`ticket_tracker.py`): Comprehensive trade tracking
- **Edit Trade on Signal Change** (`edit_trade_on_signal_change.py`): Dynamic trade modification
- **Lot Randomization** (`randomized_lot_inserter.py`): Position size randomization

### 9. Real-Time Communication
- **API Client** (`api_client.py`): Authenticated server communication
- **Auto Sync** (`auto_sync.py`): Automatic dashboard synchronization
- **WebSocket Integration**: Real-time status updates
- **Terminal Identity** (`terminal_identity.py`): Unique device fingerprinting

### 10. Telegram Copilot Bot
- **Copilot Bot** (`copilot_bot.py`): Remote control via Telegram
- **Command Interpreter** (`copilot_command_interpreter.py`): Command processing
- **Alert Manager** (`copilot_alert_manager.py`): Notification management

### 11. Security & File Management
- **Secure File Handler** (`secure_file_handler.py`): Path traversal protection
- **Authentication** (`auth.py`): JWT token management
- **Encryption**: Sensitive data protection

### 12. Error Handling & Recovery
- **Retry Engine** (`retry_engine.py`): Intelligent retry logic for failed operations
- **Comprehensive Logging**: Detailed operation logs for debugging
- **Fallback Mechanisms**: Graceful degradation on errors

## 🔧 Core Functions & Methods

### Signal Processing Functions
```python
# parser.py
class SignalParser:
    def parse_signal(text: str) -> dict
    def calculate_confidence(signal: dict) -> float
    def validate_signal_format(signal: dict) -> bool
    def extract_metadata(text: str) -> dict

# secure_signal_parser.py
class SecureSignalParser:
    def sanitize_input(input_text: str) -> str
    def detect_malicious_patterns(text: str) -> bool
    def validate_signal_structure(signal: dict) -> bool
```

### MT5 Integration Functions
```python
# mt5_bridge.py
class MT5Bridge:
    def connect_mt5() -> bool
    def execute_trade(signal: dict) -> dict
    def close_position(ticket: int) -> bool
    def modify_position(ticket: int, sl: float, tp: float) -> bool
    def get_account_info() -> dict
    def get_positions() -> list
    def get_orders() -> list

# secure_mt5_bridge.py
class SecureMT5Bridge:
    def validate_trade_limits(signal: dict) -> bool
    def check_margin_requirements(volume: float) -> bool
    def enforce_position_limits() -> bool
```

### Strategy Management Functions
```python
# strategy_runtime.py
class StrategyRuntime:
    def execute_strategy(strategy_config: dict, signal: dict) -> dict
    def evaluate_conditions(conditions: list) -> bool
    def route_signal(signal: dict, routing_rules: list) -> str
    def apply_filters(signal: dict, filters: list) -> bool

# strategy_condition_router.py
class StrategyConditionRouter:
    def check_market_conditions() -> dict
    def route_based_on_volatility(volatility: float) -> str
    def apply_session_routing(current_time: datetime) -> str
```

### Risk Management Functions
```python
# margin_level_checker.py
class MarginLevelChecker:
    def check_margin_level() -> float
    def calculate_risk_exposure() -> dict
    def trigger_margin_alerts(level: float) -> bool
    def emergency_close_positions() -> bool

# signal_limit_enforcer.py
class SignalLimitEnforcer:
    def check_hourly_limits(provider: str, symbol: str) -> bool
    def check_daily_limits(provider: str, symbol: str) -> bool
    def update_signal_count(provider: str, symbol: str) -> None
```

### Order Management Functions
```python
# smart_entry_mode.py
class SmartEntryMode:
    def calculate_optimal_entry(signal: dict) -> float
    def wait_for_better_price(target_price: float, tolerance: float) -> bool
    def execute_when_conditions_met(conditions: dict) -> dict

# multi_tp_manager.py
class MultiTPManager:
    def setup_multiple_tp_levels(tp_levels: list) -> bool
    def monitor_tp_execution() -> None
    def adjust_sl_on_tp_hit(ticket: int, new_sl: float) -> bool
```

### Communication Functions
```python
# api_client.py
class APIClient:
    def register_terminal() -> dict
    def get_terminal_config() -> dict
    def report_status(status_data: dict) -> dict
    def validate_terminal_auth() -> bool
    def update_terminal_metadata(metadata: dict) -> dict

# auto_sync.py
class AutoSync:
    def sync_trades_with_server() -> bool
    def sync_account_status() -> bool
    def sync_strategy_config() -> bool
```

### Utility Functions
```python
# spread_checker.py
class SpreadChecker:
    def check_spread(symbol: str) -> float
    def is_spread_acceptable(symbol: str, max_spread: float) -> bool
    def get_symbol_spread_limit(symbol: str) -> float

# symbol_mapper.py
class SymbolMapper:
    def map_symbol(source_symbol: str, target_broker: str) -> str
    def get_symbol_info(symbol: str) -> dict
    def validate_symbol_exists(symbol: str) -> bool

# pip_value_calculator.py
class PipValueCalculator:
    def calculate_pip_value(symbol: str, volume: float) -> float
    def convert_currency(amount: float, from_currency: str, to_currency: str) -> float
```

## 🔧 Configuration System

### Main Configuration (`config.json`)
- **Ticket Tracker**: Trade tracking and cleanup settings
- **Smart Entry**: Intelligent entry timing configuration
- **Trigger Pending Order**: Conditional order settings
- **TP/SL Adjustor**: Dynamic adjustment parameters
- **Multi-TP Manager**: Multiple take-profit configuration
- **News Filter**: Economic news filtering settings
- **Signal Limit Enforcer**: Daily/hourly limits
- **Margin Level Checker**: Margin monitoring thresholds
- **Strategy Modules**: Individual strategy configurations

### Symbol-Specific Settings
- **Pip Values**: Currency pair pip value mappings
- **Spread Limits**: Maximum allowed spreads per symbol
- **Risk Multipliers**: Symbol-specific risk adjustments

## 🔄 Real-Time Synchronization

### Dashboard Integration
- **Live Status Updates**: Real-time MT5 connection status
- **Trade Synchronization**: Automatic trade data sync
- **Performance Metrics**: Live statistics and analytics
- **Remote Control**: Dashboard-initiated commands

### WebSocket Communication
- **Bidirectional Communication**: Real-time data exchange
- **Status Broadcasting**: System status updates
- **Trade Notifications**: Instant trade execution alerts

## 📊 Analytics & Monitoring

### Performance Tracking
- **Win Rate Calculation**: Success rate analytics
- **Profit/Loss Tracking**: Comprehensive P&L monitoring
- **Provider Performance**: Signal source evaluation
- **Risk Metrics**: Real-time risk assessment

### Logging System
- **Execution Logs**: Detailed trade execution records
- **Retry Logs**: Failed operation tracking
- **Conflict Logs**: Signal conflict resolution history
- **Filter Logs**: Trade filtering decisions

## 🛡️ Security Features

### Enterprise-Grade Security
- **Input Validation**: Comprehensive data sanitization
- **Path Traversal Protection**: Secure file operations
- **Authentication**: JWT-based authentication
- **Encryption**: AES-256-GCM for sensitive data
- **Rate Limiting**: API request throttling

### Trading Security
- **Position Limits**: Maximum position size enforcement
- **Margin Protection**: Automatic margin call prevention
- **Emergency Stop**: Instant trade halt capability
- **Stealth Mode**: Hidden SL/TP from MT5 interface

## 🎯 Testing & Quality Assurance

### Comprehensive Test Suite
- **Unit Tests**: Individual component testing
- **Integration Tests**: End-to-end workflow testing
- **Strategy Testing**: Strategy logic validation
- **API Testing**: Server communication testing

### Test Coverage
- All core modules have dedicated test files
- Mock data for realistic testing scenarios
- Automated test execution capabilities

## 🚀 Deployment & Operations

### Process Management
- **PM2 Integration**: Production process management
- **Auto-restart**: Automatic recovery from crashes
- **Resource Monitoring**: Memory and CPU usage tracking
- **Log Rotation**: Automated log file management

### Environment Management
- **Configuration Validation**: Startup configuration checks
- **Environment Variables**: Secure credential management
- **Health Checks**: System health monitoring
- **Graceful Shutdown**: Clean process termination

## 📁 File Structure & Organization

### Core Modules
```
desktop-app/
├── api_client.py              # Server communication
├── auth.py                    # Authentication management
├── auto_sync.py               # Dashboard synchronization
├── mt5_bridge.py              # MetaTrader 5 integration
├── parser.py                  # Signal parsing engine
├── strategy_runtime.py        # Strategy execution
├── config.json                # Main configuration
└── logs/                      # Application logs
```

### Strategy Components
```
├── grid_strategy.py           # Grid trading
├── reverse_strategy.py        # Contrarian trading
├── multi_signal_handler.py    # Multi-signal processing
├── strategy_condition_router.py # Conditional routing
└── blocks/                    # Strategy building blocks
    └── margin_filter.py       # Margin-based filtering
```

### Risk Management
```
├── margin_level_checker.py    # Margin monitoring
├── signal_limit_enforcer.py   # Signal limits
├── rr_converter.py           # Risk/reward management
├── lotsize_engine.py         # Position sizing
└── spread_checker.py         # Spread validation
```

### Order Management
```
├── smart_entry_mode.py        # Intelligent entries
├── multi_tp_manager.py        # Multiple take-profits
├── trigger_pending_order.py   # Conditional orders
├── partial_close.py          # Partial position closure
└── entrypoint_range_handler.py # Range-based entries
```

### Telegram Integration
```
├── copilot_bot.py            # Telegram bot
├── copilot_command_interpreter.py # Command processing
└── copilot_alert_manager.py   # Alert management
```

## 🔧 Installation & Setup

### Prerequisites
- Python 3.8+
- MetaTrader 5 terminal
- Valid MT5 trading account
- SignalOS web dashboard access

### Installation Steps
1. Extract desktop application files
2. Install Python dependencies
3. Configure MT5 connection settings
4. Set up authentication token
5. Configure strategy parameters
6. Start the application

### Configuration
- Edit `config.json` for strategy settings
- Set MT5 login credentials
- Configure risk management parameters
- Set up Telegram bot (optional)
- Configure symbol mappings

This comprehensive documentation covers all features, functions, and capabilities of the SignalOS Desktop Application, providing developers and users with complete understanding of the system's architecture and functionality.
