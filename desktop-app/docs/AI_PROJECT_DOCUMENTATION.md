
# SignalOS - Complete AI Documentation

## Project Overview

SignalOS is a Python-based desktop trading automation application that parses Telegram trading signals and executes trades on MetaTrader 5 (MT5). This is a simplified desktop-only version after removing web components.

## Core Architecture

### Main Entry Point
- **File**: `main.py`
- **Purpose**: Entry point that discovers and lists all available trading modules
- **Language**: Python 3.11+
- **Execution**: `python main.py` shows available modules

### Desktop Application Structure
```
desktop-app/
├── Core Trading Engines
├── Signal Processing
├── Risk Management
├── Trade Execution
├── Configuration Management
└── Logging System
```

## Key Components Breakdown

### 1. Signal Processing Pipeline
- **parser.py**: AI-powered signal parsing with confidence scoring
- **secure_signal_parser.py**: Enhanced security version of signal parser
- **signal_simulator.py**: Testing environment for signals
- **entrypoint_range_handler.py**: Manages multiple entry points for trades
- **entry_range.py**: Handles entry price ranges and optimization

### 2. MetaTrader 5 Integration
- **mt5_bridge.py**: Primary MT5 connection and trade execution
- **secure_mt5_bridge.py**: Enhanced security version with additional protections
- **symbol_mapper.py**: Maps broker-specific symbol names
- **terminal_identity.py**: Manages MT5 terminal identification

### 3. Risk Management Engines
- **margin_level_checker.py**: Monitors account margin levels
- **spread_checker.py**: Validates bid/ask spreads before trading
- **news_filter.py**: Blocks trading during high-impact news events
- **signal_limit_enforcer.py**: Enforces provider-specific trading limits
- **time_scheduler.py**: Controls trading hours per symbol/timezone

### 4. Trade Management Systems
- **multi_tp_manager.py**: Manages multiple take-profit levels
- **sl_manager.py**: Handles stop-loss management and trailing
- **tp_sl_adjustor.py**: Adjusts TP/SL based on spread conditions
- **break_even.py**: Moves stops to breakeven when profitable
- **trailing_stop.py**: Implements various trailing stop strategies
- **partial_close.py**: Manages partial position closures

### 5. Advanced Trading Strategies
- **strategy_runtime.py**: Core strategy execution engine
- **strategy_runtime_safe.py**: Enhanced security version
- **grid_strategy.py**: Implements grid trading with risk management
- **reverse_strategy.py**: Contrarian trading logic
- **smart_entry_mode.py**: Intelligent entry timing optimization
- **strategy_condition_router.py**: Routes signals to appropriate strategies

### 6. Signal & Order Management
- **multi_signal_handler.py**: Processes multiple simultaneous signals
- **signal_conflict_resolver.py**: Resolves conflicting signals
- **ticket_tracker.py**: Tracks signal-to-trade relationships
- **trigger_pending_order.py**: Manages pending order triggers
- **edit_trade_on_signal_change.py**: Adjusts trades when signals change

### 7. Risk & Position Sizing
- **lotsize_engine.py**: Calculates optimal position sizes
- **randomized_lot_inserter.py**: Adds randomization to lot sizes
- **rr_converter.py**: Risk-reward ratio calculations
- **pip_value_calculator.py**: Calculates pip values per symbol
- **margin_filter.py**: Filters trades based on margin requirements

### 8. Utility & Support Systems
- **retry_engine.py**: Handles failed trade retries
- **auto_sync.py**: Synchronizes data between components
- **copilot_bot.py**: Telegram bot for remote control
- **copilot_command_interpreter.py**: Interprets Telegram commands
- **copilot_alert_manager.py**: Manages trading alerts
- **api_client.py**: HTTP API client for external communication
- **auth.py**: Authentication and security
- **secure_file_handler.py**: Secure file operations

### 9. Special Features
- **end_of_week_sl_remover.py**: Removes stop losses before weekend
- **magic_number_hider.py**: Obscures trade identification numbers
- **tp_adjustor.py**: Advanced TP adjustment algorithms
- **tp_manager.py**: Comprehensive TP management

## Configuration System

### Main Configuration
- **File**: `desktop-app/config.json`
- **Contains**: All module configurations in JSON format
- **Structure**: Nested configuration for each trading engine

### Symbol Mapping
- **File**: `desktop-app/config/symbol_map.json`
- **Purpose**: Maps standard symbols to broker-specific names

### Global Settings
- **File**: `config.json` (root level)
- **Purpose**: Application-wide settings and entry point configuration

## Logging System

### Log Directory Structure
```
desktop-app/logs/
├── filters/
│   └── margin_block_detailed.json
├── conflict_log.json
├── edit_trade_log.json
├── entry_range_log.json
├── lot_randomization_log.json
├── multi_tp_manager_trades.json
├── pending_orders_orders.json
├── retry_log.json
├── rr_converter_log.json
├── signal_limit_enforcer_history.json
└── ticket_tracker_log.json
```

### Logging Features
- **JSON Format**: All logs in structured JSON for parsing
- **Module-Specific**: Each engine maintains its own log file
- **Real-time**: Live logging of all trading activities
- **Audit Trail**: Complete history of all trading decisions

## Data Flow Architecture

### 1. Signal Ingestion
```
Telegram Signal → parser.py → Confidence Scoring → Validation
```

### 2. Risk Assessment
```
Parsed Signal → Risk Filters → Margin Check → Time Validation → Spread Check
```

### 3. Strategy Evaluation
```
Validated Signal → strategy_runtime.py → Condition Router → Strategy Selection
```

### 4. Trade Execution
```
Strategy Decision → mt5_bridge.py → MT5 Platform → Trade Confirmation
```

### 5. Trade Management
```
Active Trade → SL/TP Management → Trailing Stops → Partial Closes → Final Exit
```

## Module Interaction Patterns

### Core Dependencies
- **mt5_bridge.py**: Central dependency for all trading operations
- **parser.py**: Required for signal processing
- **strategy_runtime.py**: Orchestrates trading logic
- **config.json**: Universal configuration source

### Optional Enhancements
- Risk management modules can be enabled/disabled
- Trading strategies are modular and configurable
- Logging and monitoring are optional but recommended

## Configuration Examples

### Entry Range Configuration
```json
{
  "entrypoint_range": {
    "default_mode": "best",
    "max_entries": 5,
    "precision_digits": 5,
    "fallback_to_first": true,
    "min_confidence_threshold": 0.7,
    "price_tolerance_pips": 2.0,
    "enable_logging": true
  }
}
```

### Time Scheduler Rules
```json
{
  "time_scheduler": {
    "enabled": true,
    "rules": {
      "GOLD": {
        "start": "08:30",
        "end": "15:00",
        "timezone": "UTC",
        "weekdays": [0, 1, 2, 3, 4]
      }
    }
  }
}
```

### Reverse Strategy Settings
```json
{
  "reverse_strategy": {
    "enabled": true,
    "default_reversal_mode": "full_reverse",
    "reversal_confidence_threshold": 0.7,
    "market_volatility_threshold": 2.0
  }
}
```

## Development Environment

### Platform
- **Environment**: Replit with Python 3.11+ support
- **OS**: Linux (Nix-based)
- **Dependencies**: Managed via pyproject.toml

### Key Dependencies
- **requests**: HTTP client for API communication
- **MetaTrader5**: MT5 Python library (when available)
- **asyncio**: Asynchronous operation support

### Execution Methods
1. **Direct Module**: `python desktop-app/module_name.py`
2. **Main Entry**: `python main.py` (discovery mode)
3. **Specific Function**: Import and call module functions

## Security Features

### File Security
- **secure_file_handler.py**: Encrypted file operations
- **secure_mt5_bridge.py**: Enhanced MT5 security
- **secure_signal_parser.py**: Secure signal processing

### Authentication
- **auth.py**: User authentication and session management
- **api_client.py**: Secure API communication

## AI Integration Points

### Signal Processing
- AI-powered confidence scoring in parser.py
- Machine learning for entry point optimization
- Predictive analysis for risk assessment

### Strategy Enhancement
- Dynamic strategy selection based on market conditions
- Adaptive risk management parameters
- Learning from trade outcomes

## Common Usage Patterns

### Basic Trading Setup
1. Configure MT5 connection in config.json
2. Set up signal parsing parameters
3. Enable desired risk management modules
4. Configure trading strategies
5. Start main application

### Advanced Configuration
1. Customize symbol mappings
2. Set up multiple TP levels
3. Configure grid trading parameters
4. Enable news filtering
5. Set up Telegram bot integration

### Monitoring & Maintenance
1. Review log files regularly
2. Monitor margin levels
3. Check connection status
4. Update configurations as needed
5. Backup important data

## File Dependencies Map

### Critical Files
- **main.py**: Application entry point
- **desktop-app/config.json**: Master configuration
- **desktop-app/mt5_bridge.py**: Trading interface
- **desktop-app/parser.py**: Signal processing
- **desktop-app/strategy_runtime.py**: Strategy engine

### Support Files
- All other modules enhance core functionality
- Logs provide audit trails and debugging
- Configuration files enable customization

This documentation provides complete AI understanding of the SignalOS project structure, functionality, and usage patterns.
