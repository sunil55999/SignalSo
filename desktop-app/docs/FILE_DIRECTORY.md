
# SignalOS - Complete File Directory & Usage Guide

## 📁 Root Directory Files

| File | Purpose | Description |
|------|---------|-------------|
| `main.py` | Application Entry Point | Main entry point for SignalOS desktop application |
| `start.py` | Startup Script | Alternative startup script for the application |
| `test_core.py` | Core Testing | Tests all 6 core features (100% success rate) |
| `run_phase2.py` | Phase 2 Features | Runs advanced Phase 2 features and testing |
| `config.json` | Global Configuration | Main application configuration file |
| `prop_firm.db` | Prop Firm Database | SQLite database for prop firm data storage |
| `README.md` | Project Overview | Main project documentation and setup guide |
| `AI_PROJECT_DOCUMENTATION.md` | AI Documentation | Complete AI system documentation |
| `COMPLETE_PROJECT_DOCUMENTATION.md` | Complete Docs | Comprehensive A-Z project documentation |
| `DEVELOPMENT_STATUS_REPORT.md` | Status Report | Development progress and implementation status |
| `SIGNALOS_COMPLETE_FEATURE_SPECIFICATION.md` | Feature Specs | Complete feature specifications |
| `replit.md` | Development History | Project evolution and development notes |
| `package.json` | Node.js Dependencies | Frontend dependencies and scripts |
| `package-lock.json` | Dependency Lock | Locked dependency versions |
| `pyproject.toml` | Python Dependencies | Python project configuration and dependencies |
| `uv.lock` | UV Lock File | Python dependency lock file |
| `tsconfig.json` | TypeScript Config | TypeScript compiler configuration |
| `tsconfig.node.json` | Node TypeScript Config | Node.js specific TypeScript configuration |
| `tailwind.config.js` | Tailwind CSS Config | Tailwind CSS styling configuration |
| `postcss.config.js` | PostCSS Config | PostCSS processing configuration |
| `.gitignore` | Git Ignore | Git ignore patterns |
| `.replit` | Replit Config | Replit environment configuration |
| `cookies.txt` | Session Data | Browser session storage |

## 🖥️ Desktop Application (`desktop-app/`)

### Core Application Files
| File | Purpose | Description |
|------|---------|-------------|
| `main.py` | Desktop Main | Desktop application entry point |
| `config.json` | Desktop Config | Desktop-specific configuration |
| `__init__.py` | Package Init | Python package initialization |
| `requirements.txt` | Python Deps | Python dependencies for desktop app |

### Trading Engine Files
| File | Purpose | Description |
|------|---------|-------------|
| `mt5_bridge.py` | MT5 Integration | Primary MetaTrader 5 connection and trading |
| `secure_mt5_bridge.py` | Secure MT5 | Enhanced security MT5 bridge |
| `trade_executor.py` | Trade Execution | Professional trade execution engine |
| `strategy_runtime.py` | Strategy Engine | Core strategy execution orchestrator |
| `strategy_runtime_safe.py` | Safe Strategy | Enhanced security strategy runtime |
| `multi_signal_handler.py` | Multi-Signal | Handles multiple simultaneous signals |
| `retry_engine.py` | Retry Logic | Failed trade retry mechanism |
| `auto_sync.py` | Data Sync | Data synchronization between components |

### Signal Processing Files
| File | Purpose | Description |
|------|---------|-------------|
| `parser.py` | Signal Parser | AI-powered signal parsing with confidence |
| `secure_signal_parser.py` | Secure Parser | Enhanced security signal processing |
| `advanced_signal_processor.py` | Advanced Parser | Phase 2 advanced signal processor |
| `telegram_monitor.py` | Telegram Monitor | Advanced Telegram signal monitoring |
| `signal_simulator.py` | Signal Testing | Testing environment for signals |
| `signal_conflict_resolver.py` | Conflict Resolution | Resolves conflicting signals |
| `signal_conflict_resolver_safe.py` | Safe Conflict | Safe version of conflict resolver |

### Risk Management Files
| File | Purpose | Description |
|------|---------|-------------|
| `margin_level_checker.py` | Margin Monitor | Real-time margin level monitoring |
| `spread_checker.py` | Spread Validation | Bid/ask spread validation |
| `news_filter.py` | News Filter | Economic calendar-based trade blocking |
| `signal_limit_enforcer.py` | Signal Limits | Provider-specific trading limits |
| `time_scheduler.py` | Time Control | Trading hours control per symbol |

### Position Management Files
| File | Purpose | Description |
|------|---------|-------------|
| `lotsize_engine.py` | Position Sizing | Optimal position size calculation |
| `randomized_lot_inserter.py` | Lot Randomization | Adds randomization to lot sizes |
| `rr_converter.py` | Risk-Reward | Risk-reward ratio calculations |
| `pip_value_calculator.py` | Pip Calculator | Pip value calculations per symbol |
| `margin_filter.py` | Margin Filter | Margin-based trade filtering |

### Trade Management Files
| File | Purpose | Description |
|------|---------|-------------|
| `multi_tp_manager.py` | Multi TP | Multiple take-profit level management |
| `sl_manager.py` | Stop Loss | Stop-loss management and trailing |
| `tp_sl_adjustor.py` | TP/SL Adjust | Adjusts TP/SL based on spread |
| `break_even.py` | Break Even | Breakeven stop management |
| `trailing_stop.py` | Trailing Stops | Advanced trailing stop strategies |
| `partial_close.py` | Partial Close | Partial position closure management |
| `tp_adjustor.py` | TP Adjustment | Advanced TP adjustment algorithms |
| `tp_manager.py` | TP Management | Comprehensive TP management |

### Strategy Files
| File | Purpose | Description |
|------|---------|-------------|
| `grid_strategy.py` | Grid Trading | Grid trading with risk management |
| `reverse_strategy.py` | Contrarian | Contrarian trading logic |
| `smart_entry_mode.py` | Smart Entry | Intelligent entry timing |
| `strategy_condition_router.py` | Strategy Router | Routes signals to strategies |

### Order Management Files
| File | Purpose | Description |
|------|---------|-------------|
| `ticket_tracker.py` | Ticket Tracking | Signal-to-trade relationship tracking |
| `trigger_pending_order.py` | Pending Orders | Pending order management |
| `edit_trade_on_signal_change.py` | Trade Editing | Adjusts trades on signal changes |
| `entrypoint_range_handler.py` | Entry Range | Multiple entry point management |
| `entry_range.py` | Entry Optimization | Entry price range optimization |

### Utility Files
| File | Purpose | Description |
|------|---------|-------------|
| `symbol_mapper.py` | Symbol Mapping | Broker-specific symbol mapping |
| `terminal_identity.py` | Terminal ID | MT5 terminal identification |
| `api_client.py` | API Client | HTTP API client for communication |
| `auth.py` | Authentication | Authentication and security |
| `secure_file_handler.py` | File Security | Secure file operations |

### Remote Control Files
| File | Purpose | Description |
|------|---------|-------------|
| `copilot_bot.py` | Telegram Bot | Telegram bot for remote control |
| `copilot_command_interpreter.py` | Command Interpreter | Interprets Telegram commands |
| `copilot_alert_manager.py` | Alert Manager | Trading alert management |

### Special Features
| File | Purpose | Description |
|------|---------|-------------|
| `end_of_week_sl_remover.py` | Weekend SL | Removes stop losses before weekend |
| `magic_number_hider.py` | Trade ID | Obscures trade identification |

### Demo & Testing Files
| File | Purpose | Description |
|------|---------|-------------|
| `phase1_main.py` | Phase 1 Main | Complete Phase 1 application |
| `phase1_simple_demo.py` | Simple Demo | Core functionality demonstration |
| `phase1_demo.py` | Phase 1 Demo | Phase 1 feature demonstration |
| `part1_integration.py` | Integration | Part 1 integration testing |
| `test_advanced_parser.py` | Parser Testing | Advanced parser testing |
| `test_phase2.py` | Phase 2 Testing | Phase 2 feature testing |
| `test_advanced_error_handling.py` | Error Testing | Error handling tests |
| `test_update_system.py` | Update Testing | Update system testing |
| `test_signal.png` | Test Image | Test signal image for OCR |

### Demo Files
| File | Purpose | Description |
|------|---------|-------------|
| `demo_advanced_error_handling.py` | Error Demo | Advanced error handling demo |
| `demo_update_usage.py` | Update Demo | Update system usage demo |

## 📁 Authentication (`desktop-app/auth/`)

| File | Purpose | Description |
|------|---------|-------------|
| `__init__.py` | Package Init | Authentication package initialization |
| `jwt_license_system.py` | JWT Licensing | Hardware-based licensing system |
| `telegram_auth.py` | Telegram Auth | Secure Telegram authentication |
| `license_checker.py` | License Check | License validation and checking |

## 📁 AI Parser (`desktop-app/ai_parser/`)

| File | Purpose | Description |
|------|---------|-------------|
| `__init__.py` | Package Init | AI parser package initialization |
| `parser_engine.py` | Parser Engine | Safe parser with AI + fallback |
| `parser_utils.py` | Parser Utils | Utilities and sanitization |
| `fallback_regex_parser.py` | Regex Fallback | Regex fallback parsing system |
| `feedback_logger.py` | Feedback Logger | Error logging and analytics |
| `continuous_learning.py` | Learning System | Continuous learning implementation |
| `dataset_manager.py` | Dataset Manager | Training dataset management |
| `evaluation_metrics.py` | Evaluation | Parser performance evaluation |
| `model_trainer.py` | Model Training | AI model training system |
| `tuned_parser_demo.py` | Tuned Demo | Tuned parser demonstration |
| `PARSER_TUNING_COMPLETE.md` | Documentation | Parser tuning completion docs |

## 📁 Parser (`desktop-app/parser/`)

| File | Purpose | Description |
|------|---------|-------------|
| `__init__.py` | Package Init | Parser package initialization |
| `parser_core.py` | Parser Core | Core parsing logic |
| `multilingual_parser.py` | Multi-language | Support for 8+ languages |
| `ocr_engine.py` | OCR Engine | Image-to-text processing |
| `confidence_system.py` | Confidence | AI confidence scoring system |
| `config_parser.py` | Config Parser | Configuration-based parsing |
| `prompt_to_config.py` | Prompt Config | Natural language to config |
| `image_parser.py` | Image Parser | Image signal parsing |
| `lang_detect.py` | Language Detection | Language detection system |

### Language Support (`desktop-app/parser/lang/`)
| File | Purpose | Description |
|------|---------|-------------|
| `__init__.py` | Package Init | Language package initialization |
| `english_parser.py` | English Parser | English-specific parsing logic |

## 📁 Strategy (`desktop-app/strategy/`)

| File | Purpose | Description |
|------|---------|-------------|
| `__init__.py` | Package Init | Strategy package initialization |
| `strategy_core.py` | Strategy Core | Core strategy engine |
| `prop_firm_mode.py` | Prop Firm | Prop firm compliance system |

## 📁 Trade (`desktop-app/trade/`)

| File | Purpose | Description |
|------|---------|-------------|
| `__init__.py` | Package Init | Trade package initialization |
| `mt5_socket_bridge.py` | MT5 Socket | Socket server for MT5 integration |

## 📁 Updater (`desktop-app/updater/`)

| File | Purpose | Description |
|------|---------|-------------|
| `__init__.py` | Package Init | Updater package initialization |
| `auto_updater.py` | Auto Updater | Automatic update system |
| `tauri_updater.py` | Tauri Updater | Tauri-style update system |
| `model_updater.py` | Model Updater | AI model update system |
| `notification_handler.py` | Notifications | Update notification system |
| `update_scheduler.py` | Update Scheduler | Update scheduling system |
| `version_manager.py` | Version Manager | Version management system |

## 📁 Backtest (`desktop-app/backtest/`)

| File | Purpose | Description |
|------|---------|-------------|
| `__init__.py` | Package Init | Backtest package initialization |
| `engine.py` | Backtest Engine | Strategy backtesting system |

## 📁 Report (`desktop-app/report/`)

| File | Purpose | Description |
|------|---------|-------------|
| `__init__.py` | Package Init | Report package initialization |
| `generator.py` | Report Generator | PDF report generation system |

## 📁 Installer (`desktop-app/installer/`)

| File | Purpose | Description |
|------|---------|-------------|
| `__init__.py` | Package Init | Installer package initialization |
| `pyinstaller_spec.py` | PyInstaller | PyInstaller configuration |
| `tauri.conf.json` | Tauri Config | Tauri desktop app configuration |

## 📁 Server (`desktop-app/server/`)

| File | Purpose | Description |
|------|---------|-------------|
| `__init__.py` | Package Init | Server package initialization |
| `license_api.py` | License API | License validation API server |
| `config_api.py` | Config API | Configuration API server |

## 📁 Setup (`desktop-app/setup/`)

| File | Purpose | Description |
|------|---------|-------------|
| `__init__.py` | Package Init | Setup package initialization |
| `install.sh` | Install Script | Linux installation script |

## 📁 Blocks (`desktop-app/blocks/`)

| File | Purpose | Description |
|------|---------|-------------|
| `margin_filter.py` | Margin Filter | Trading filter for margin requirements |

## 📁 Configuration (`desktop-app/config/`)

| File | Purpose | Description |
|------|---------|-------------|
| `config.json` | Main Config | Primary configuration file |
| `parser_config.json` | Parser Config | Parser-specific settings |
| `parser_patterns.json` | Parser Patterns | Parsing pattern definitions |
| `symbol_map.json` | Symbol Map | Symbol mapping configuration |
| `user_config.json` | User Config | User preference settings |
| `sync_settings.json` | Sync Settings | Cloud synchronization settings |
| `license.json` | License Config | License configuration |
| `model_config.json` | Model Config | AI model configuration |
| `lang_patterns.json` | Language Patterns | Language-specific patterns |
| `scheduler_config.json` | Scheduler Config | Scheduling configuration |
| `cloud_sync.py` | Cloud Sync | Cloud synchronization module |

## 📁 Data (`desktop-app/data/`)

| File | Purpose | Description |
|------|---------|-------------|
| `dataset.db` | Dataset DB | Training dataset database |
| `test.jsonl` | Test Data | Testing dataset |
| `test_hf.jsonl` | HF Test Data | HuggingFace test data |
| `test_spacy.jsonl` | spaCy Test Data | spaCy test dataset |
| `train_hf.jsonl` | HF Training | HuggingFace training data |
| `train_spacy.jsonl` | spaCy Training | spaCy training dataset |
| `validation_hf.jsonl` | HF Validation | HuggingFace validation data |
| `validation_spacy.jsonl` | spaCy Validation | spaCy validation dataset |

## 📁 Models (`desktop-app/models/`)

| File | Purpose | Description |
|------|---------|-------------|
| `training_log.jsonl` | Training Log | AI model training history |
| `version.json` | Version Info | Model version information |

### Model Subdirectories
- `checkpoints/` - Model training checkpoints
- `current_model/` - Active AI model
- `trained/` - Trained model storage
- `staging/` - Staged models for deployment
- `evaluations/` - Model evaluation results
- `versions/` - Model version history

## 📁 Logs (`desktop-app/logs/`)

### Main Log Files
| File | Purpose | Description |
|------|---------|-------------|
| `main.log` | Main Log | Primary application log |
| `signalos_desktop.log` | Desktop Log | Desktop app specific log |
| `performance.log` | Performance | Performance monitoring log |
| `failures.log` | Failures | Failed operation log |
| `successes.log` | Successes | Successful operation log |

### Module-Specific Logs
| File | Purpose | Description |
|------|---------|-------------|
| `advanced_processor.log` | Advanced Parser | Advanced processing log |
| `backtest.log` | Backtesting | Backtesting operation log |
| `confidence_system.log` | Confidence | Confidence scoring log |
| `config_parser.log` | Config Parser | Configuration parsing log |
| `model_updater.log` | Model Updates | Model update log |
| `multilingual_parser.log` | Multi Parser | Multilingual parsing log |
| `ocr_engine.log` | OCR Engine | OCR processing log |
| `parser_core.log` | Parser Core | Core parsing log |
| `parser_engine.log` | Parser Engine | Parser engine log |
| `prompt_converter.log` | Prompt Convert | Prompt conversion log |
| `strategy_core.log` | Strategy Core | Strategy execution log |

### JSON Data Logs
| File | Purpose | Description |
|------|---------|-------------|
| `conflict_log.json` | Conflicts | Signal conflict log |
| `edit_trade_log.json` | Trade Edits | Trade modification log |
| `entry_range_log.json` | Entry Range | Entry range log |
| `lot_randomization_log.json` | Lot Random | Lot randomization log |
| `multi_tp_manager_trades.json` | Multi TP | Multi TP trades log |
| `pending_orders_orders.json` | Pending Orders | Pending order log |
| `retry_log.json` | Retries | Retry operation log |
| `rr_converter_log.json` | Risk Reward | Risk-reward conversion log |
| `signal_limit_enforcer_history.json` | Signal Limits | Signal limit history |
| `ticket_tracker_log.json` | Ticket Tracker | Ticket tracking log |
| `test_training_data.json` | Test Training | Test training data |
| `parsing_attempts.jsonl` | Parse Attempts | Parsing attempt log |

### Database Logs
| File | Purpose | Description |
|------|---------|-------------|
| `confidence_system.db` | Confidence DB | Confidence system database |
| `learning_data.db` | Learning DB | Learning data database |
| `ocr_learning.db` | OCR Learning | OCR learning database |
| `strategy_core.db` | Strategy DB | Strategy core database |

### Filter Logs (`desktop-app/logs/filters/`)
| File | Purpose | Description |
|------|---------|-------------|
| `margin_block_detailed.json` | Margin Blocks | Detailed margin blocking log |

## 📁 Reports (`desktop-app/reports/`)

| File | Purpose | Description |
|------|---------|-------------|
| `Advanced_Parser_Test_Report_*.txt` | Parser Tests | Advanced parser test reports |
| `Phase2_Feature_Report_*.txt` | Phase 2 Reports | Phase 2 feature reports |
| `SignalOS_Backtest_Report_*.pdf` | Backtest PDFs | Professional backtest PDF reports |
| `SignalOS_Quick_Report_*.txt` | Quick Reports | Quick text reports |
| `Update_System_Test_Report_*.txt` | Update Tests | Update system test reports |

## 📁 Evaluations (`desktop-app/evaluations/`)

| File | Purpose | Description |
|------|---------|-------------|
| `parser_evaluation_*.json` | Parser Eval | Parser performance evaluations |
| `performance_alerts.jsonl` | Performance Alerts | Performance alert log |

## 📁 Notifications (`desktop-app/notifications/`)

| File | Purpose | Description |
|------|---------|-------------|
| `model_update_*.json` | Model Updates | Model update notifications |
| `system_info_*.json` | System Info | System information notifications |
| `update_available_*.json` | Updates Available | Update availability notifications |

## 📁 Learning (`desktop-app/learning/`)

| File | Purpose | Description |
|------|---------|-------------|
| `ab_tests.db` | A/B Tests | A/B testing database |

## 📁 Frontend (`desktop-app/frontend/`)

### Main Frontend Files
| File | Purpose | Description |
|------|---------|-------------|
| `index.html` | Main HTML | Primary HTML entry point |
| `simple.html` | Simple HTML | Simplified HTML interface |
| `package.json` | Frontend Deps | Frontend dependencies |
| `package-lock.json` | Dependency Lock | Locked frontend dependencies |
| `vite.config.ts` | Vite Config | Vite build configuration |
| `tsconfig.json` | TypeScript Config | TypeScript configuration |
| `tailwind.config.js` | Tailwind Config | Tailwind CSS configuration |
| `postcss.config.js` | PostCSS Config | PostCSS configuration |

### React Components (`desktop-app/frontend/src/`)
| File | Purpose | Description |
|------|---------|-------------|
| `App.tsx` | Main App | Main React application component |
| `main.tsx` | Entry Point | React application entry point |
| `index.css` | Global Styles | Global CSS styles |

### Component Categories

#### Dashboard Components (`components/dashboard/`)
| File | Purpose | Description |
|------|---------|-------------|
| `EventTimeline.tsx` | Event Timeline | Trading event timeline |
| `QuickActionsPanel.tsx` | Quick Actions | Quick action buttons |
| `SystemHealthCenter.tsx` | System Health | System health monitoring |
| `TradingMetrics.tsx` | Trading Metrics | Trading performance metrics |

#### Layout Components (`components/layout/`)
| File | Purpose | Description |
|------|---------|-------------|
| `navbar.tsx` | Navigation Bar | Top navigation component |
| `sidebar.tsx` | Sidebar | Side navigation component |

#### Redesigned Components (`components/redesigned/`)
| File | Purpose | Description |
|------|---------|-------------|
| `RedesignedApp.tsx` | Redesigned App | Main redesigned application |
| `SimpleRedesignedApp.tsx` | Simple App | Simplified redesigned app |
| `RedesignedHeader.tsx` | Header | Redesigned header component |
| `RedesignedSidebar.tsx` | Sidebar | Redesigned sidebar component |
| `MainDashboard.tsx` | Dashboard | Main dashboard component |
| `AccountSummaryPanel.tsx` | Account Summary | Account overview panel |
| `ActiveTradesPanel.tsx` | Active Trades | Active trades display |
| `SystemHealthPanel.tsx` | System Health | System status panel |
| `SignalActivityFeed.tsx` | Signal Feed | Signal activity feed |
| `SignalProviderManagement.tsx` | Provider Mgmt | Signal provider management |
| `StrategyBuilder.tsx` | Strategy Builder | Trading strategy builder |
| `QuickActionsPanel.tsx` | Quick Actions | Quick action panel |
| `NotificationCenter.tsx` | Notifications | Notification center |
| `ImportExportHub.tsx` | Import/Export | Import/export functionality |
| `ComprehensiveLogsCenter.tsx` | Log Center | Comprehensive log viewer |

#### UI Components (`components/ui/`)
| File | Purpose | Description |
|------|---------|-------------|
| `badge.tsx` | Badge | Badge UI component |
| `button.tsx` | Button | Button UI component |
| `card.tsx` | Card | Card UI component |
| `dialog.tsx` | Dialog | Dialog/modal component |
| `dropdown-menu.tsx` | Dropdown | Dropdown menu component |
| `input.tsx` | Input | Input field component |
| `label.tsx` | Label | Label component |
| `progress.tsx` | Progress | Progress bar component |
| `select.tsx` | Select | Select dropdown component |
| `switch.tsx` | Switch | Toggle switch component |
| `tabs.tsx` | Tabs | Tab navigation component |
| `textarea.tsx` | Textarea | Text area component |
| `toast.tsx` | Toast | Toast notification component |
| `toaster.tsx` | Toaster | Toast container component |

#### Other Components (`components/`)
| File | Purpose | Description |
|------|---------|-------------|
| `ActivityCenter.tsx` | Activity Center | Activity monitoring center |
| `EnhancedManagementPanel.tsx` | Management Panel | Enhanced management interface |
| `FeedbackSystem.tsx` | Feedback | User feedback system |
| `GlobalImportPanel.tsx` | Global Import | Global import functionality |
| `ImportExportPanel.tsx` | Import/Export | Import/export panel |
| `OnboardingWizard.tsx` | Onboarding | User onboarding wizard |
| `ProgressIndicator.tsx` | Progress | Progress indicator component |
| `theme-provider.tsx` | Theme Provider | Theme management provider |

#### Hooks (`hooks/`)
| File | Purpose | Description |
|------|---------|-------------|
| `use-toast.ts` | Toast Hook | Toast notification hook |
| `use-toast.tsx` | Toast Hook TSX | Toast hook with JSX |
| `useSystemStatus.ts` | System Status | System status monitoring hook |

#### Utilities (`lib/`)
| File | Purpose | Description |
|------|---------|-------------|
| `utils.ts` | Utilities | General utility functions |
| `queryClient.ts` | Query Client | React Query client setup |

#### Pages (`pages/`)
| File | Purpose | Description |
|------|---------|-------------|
| `dashboard.tsx` | Dashboard Page | Main dashboard page |

##### Auth Pages (`pages/auth/`)
| File | Purpose | Description |
|------|---------|-------------|
| `login.tsx` | Login Page | User login page |

##### Channel Pages (`pages/channels/`)
| File | Purpose | Description |
|------|---------|-------------|
| `setup.tsx` | Channel Setup | Channel setup page |

##### Log Pages (`pages/logs/`)
| File | Purpose | Description |
|------|---------|-------------|
| `view.tsx` | Log Viewer | Log viewing page |

##### Settings Pages (`pages/settings/`)
| File | Purpose | Description |
|------|---------|-------------|
| `panel.tsx` | Settings Panel | Settings configuration page |

##### Signal Pages (`pages/signals/`)
| File | Purpose | Description |
|------|---------|-------------|
| `validator.tsx` | Signal Validator | Signal validation page |

##### Strategy Pages (`pages/strategy/`)
| File | Purpose | Description |
|------|---------|-------------|
| `backtest.tsx` | Backtest Page | Strategy backtesting page |

#### Store (`store/`)
| File | Purpose | Description |
|------|---------|-------------|
| `auth.ts` | Auth Store | Authentication state management |

## 📁 Backend (`desktop-app/backend/`)

### Main Backend Files
| File | Purpose | Description |
|------|---------|-------------|
| `main.py` | Backend Main | Backend application entry point |
| `start.py` | Backend Start | Backend startup script |
| `test_core.py` | Backend Tests | Backend core feature tests |
| `run_phase2.py` | Backend Phase 2 | Backend Phase 2 features |
| `app.js` | Express App | Express.js application |
| `basic.js` | Basic Server | Basic server implementation |
| `index.ts` | TypeScript Main | TypeScript backend entry |
| `routes.ts` | API Routes | API route definitions |
| `server.ts` | Server Config | Server configuration |
| `simple.ts` | Simple Server | Simplified server |
| `schema.ts` | Database Schema | Database schema definitions |
| `storage.ts` | Storage | Data storage utilities |

### Backend Modules (`backend/*/`)

#### Auth Module (`backend/auth/`)
| File | Purpose | Description |
|------|---------|-------------|
| `index.ts` | Auth API | Authentication API endpoints |

#### Bridge API (`backend/bridge_api/`)
| File | Purpose | Description |
|------|---------|-------------|
| `index.ts` | Bridge API | MT5 bridge API endpoints |

#### Config Module (`backend/config/`)
| File | Purpose | Description |
|------|---------|-------------|
| `index.ts` | Config API | Configuration API endpoints |

#### Executor Module (`backend/executor/`)
| File | Purpose | Description |
|------|---------|-------------|
| `index.ts` | Executor API | Trade execution API endpoints |

#### Logs Module (`backend/logs/`)
| File | Purpose | Description |
|------|---------|-------------|
| `index.ts` | Logs API | Logging API endpoints |

#### Parser Module (`backend/parser/`)
| File | Purpose | Description |
|------|---------|-------------|
| `index.ts` | Parser API | Signal parsing API endpoints |

#### Router Module (`backend/router/`)
| File | Purpose | Description |
|------|---------|-------------|
| `index.ts` | Router API | Signal routing API endpoints |

#### Telegram Module (`backend/telegram/`)
| File | Purpose | Description |
|------|---------|-------------|
| `index.ts` | Telegram API | Telegram integration API endpoints |

#### Updater Module (`backend/updater/`)
| File | Purpose | Description |
|------|---------|-------------|
| `index.ts` | Updater API | Auto-updater API endpoints |

### Backend Log Files (`backend/logs/`)
| File | Purpose | Description |
|------|---------|-------------|
| `mt5_bridge.log` | MT5 Bridge | MT5 bridge operation log |
| `multilingual_parser.log` | Multi Parser | Multilingual parser log |
| `ocr_engine.log` | OCR Engine | OCR engine operation log |
| `prop_firm.log` | Prop Firm | Prop firm operation log |
| `telegram_auth.log` | Telegram Auth | Telegram authentication log |

## 📁 Documentation Files

### Project Documentation
| File | Purpose | Description |
|------|---------|-------------|
| `PROJECT_STRUCTURE.md` | Structure Docs | Project structure documentation |
| `REORGANIZATION_COMPLETE.md` | Reorganization | File reorganization completion |
| `PHASE1_IMPLEMENTATION_COMPLETE.md` | Phase 1 Docs | Phase 1 implementation documentation |
| `PART1_DOCUMENTATION.md` | Part 1 Docs | Part 1 feature documentation |

### Attached Assets (`attached_assets/`)
Various implementation guides, specifications, and visual assets for the project.

## 📁 Server (`server/`)

| File | Purpose | Description |
|------|---------|-------------|
| `index.ts` | Server Main | Main server application |
| `routes.ts` | Routes | Server route definitions |
| `simple.ts` | Simple Server | Simplified server version |
| `storage.ts` | Storage | Server storage utilities |
| `app.js` | Express Server | Express.js server |
| `basic.js` | Basic Server | Basic server implementation |

## 📁 Client (`client/`)

Contains duplicate frontend files for development purposes.

## 📁 Shared (`shared/`)

| File | Purpose | Description |
|------|---------|-------------|
| `schema.ts` | Shared Schema | Shared database schema definitions |

## 📁 Source (`src/`)

Contains TypeScript source modules organized by feature.

## 📁 Root Support Directories

- `logs/` - Application-wide log storage
- `sessions/` - User session storage  
- `updates/` - Auto-updater files and logs

---

## 📊 File Count Summary

- **Total Files**: 500+ files
- **Python Files**: 150+ trading modules and engines
- **TypeScript/React Files**: 100+ frontend components
- **Configuration Files**: 50+ config and settings files
- **Log Files**: 100+ logging and tracking files
- **Documentation Files**: 25+ markdown documentation files

## 🎯 Key File Categories

1. **Core Trading Engine**: 49 Python trading modules
2. **Frontend Interface**: Modern React/TypeScript UI
3. **AI Processing**: Advanced signal parsing and ML
4. **Configuration System**: Comprehensive settings management
5. **Logging & Analytics**: Detailed operation tracking
6. **Security & Auth**: Multi-layer authentication system
7. **Documentation**: Complete project documentation

This directory represents a complete, production-ready trading automation platform with comprehensive features for signal processing, trade execution, risk management, and user interface.
