# SignalOS - Trading Automation Platform

SignalOS is a comprehensive trading automation platform that parses Telegram signals, executes trades on MT5, and provides real-time monitoring through a web dashboard.

## 🚀 Features

### Desktop App (Python)
- **Signal Parser**: AI-powered parsing of Telegram trading signals with confidence scoring
- **MT5 Integration**: Direct connection to MetaTrader 5 for trade execution
- **Smart Retry Engine**: Intelligent retry logic for failed trades with configurable parameters
- **Telegram Copilot Bot**: Remote control and monitoring via Telegram commands
- **Strategy Runtime**: Visual strategy builder with conditional logic and risk management
- **Auto Sync**: Automatic synchronization with server for real-time updates

### Server (Express + TypeScript)
- **Authentication**: JWT-based session management with role-based access
- **Firebridge APIs**: Advanced sync endpoints for desktop app integration
- **Signal Processing**: Real-time signal parsing and simulation capabilities
- **WebSocket Support**: Live updates and real-time communication
- **Database Integration**: PostgreSQL with Drizzle ORM for data persistence

### Web Dashboard (React + TypeScript)
- **Real-time Trading Dashboard**: Live P&L, active trades, and signal monitoring
- **Strategy Builder**: Visual drag-and-drop strategy creation interface
- **Admin Panel**: User and channel management with comprehensive controls
- **Signal Replay**: Re-execute signals with parameter modifications
- **MT5 Health Monitoring**: Real-time connection status and performance metrics

## 📋 Quick Start

### Prerequisites
- Node.js 20+
- Python 3.11+
- PostgreSQL 15+
- MetaTrader 5 terminal

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-username/signalos.git
   cd signalos
   ```

2. **Install dependencies**
   ```bash
   npm install
   ```

3. **Set up environment variables**
   ```bash
   cp deployment/.env.template .env
   # Edit .env with your configuration
   ```

4. **Initialize the database**
   ```bash
   npm run db:push
   ```

5. **Start the application**
   ```bash
   npm run dev
   ```

### Development Setup

The application runs on multiple components:

- **Web Server**: http://localhost:5000
- **Database**: PostgreSQL on port 5432
- **Desktop App**: Python modules for MT5 integration

## 🏗️ Architecture

```
signalos/
├── desktop-app/         # Python: MT5, Parser, Retry Engine, Copilot
├── server/              # Express + TypeScript: API, DB, Auth, Firebridge
├── client/              # React + TypeScript: Dashboard (User/Admin)
├── shared/              # Shared JSON/Zod schemas (used across modules)
├── logs/                # Execution, retry, sync logs
└── deployment/          # Docker, PM2 configs, .env.template
```

## 🔧 Configuration

### Environment Variables

Copy `deployment/.env.template` to `.env` and configure:

```env
# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/signalos

# MT5 Settings
MT5_SERVER=MetaQuotes-Demo
MT5_LOGIN=12345678
MT5_PASSWORD=your_password

# Telegram Bot
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# Trading Parameters
SIGNAL_CONFIDENCE_THRESHOLD=70
MAX_CONCURRENT_TRADES=5
DEFAULT_LOT_SIZE=0.01
```

### Strategy Configuration

Create custom trading strategies using the visual builder:

1. Navigate to Strategy Builder in the dashboard
2. Choose from predefined templates or create custom rules
3. Configure conditions (confidence, time filters, risk management)
4. Set actions (execute, skip, modify, scale lot size)
5. Test with signal simulation before deployment

## 📊 Signal Formats

SignalOS supports multiple signal formats:

### Standard Format
```
BUY EURUSD
Entry: 1.1000
SL: 1.0950
TP1: 1.1050
TP2: 1.1100
```

### Compact Format
```
BUY GBPUSD E:1.2500 SL:1.2450 TP:1.2600
```

### Multi-TP Format
```
SELL USDJPY
Entry: 110.50
SL: 111.00
TP1: 110.00
TP2: 109.50
TP3: 109.00
```

## 🔄 Telegram Bot Commands

Control SignalOS remotely via Telegram:

- `/status` - MT5 and system status
- `/trades` - Active trades overview
- `/signals` - Recent signals
- `/replay <signal_id>` - Replay a signal
- `/stealth` - Toggle stealth mode
- `/pause` - Pause trading
- `/resume` - Resume trading
- `/stats` - Trading statistics

## 🚀 Deployment

### Docker Deployment

1. **Build and run with Docker Compose**
   ```bash
   cd deployment
   docker-compose up -d
   ```

2. **Environment setup**
   ```bash
   cp .env.template .env
   # Configure your environment variables
   ```

### PM2 Deployment

1. **Install PM2**
   ```bash
   npm install -g pm2
   ```

2. **Start all processes**
   ```bash
   cd deployment
   pm2 start pm2.config.js
   ```

3. **Monitor processes**
   ```bash
   pm2 monit
   pm2 logs
   ```

## 🧪 Testing

Run the test suite:

```bash
# Desktop app tests
cd desktop-app
python -m pytest tests/ -v

# Server tests
npm test

# Integration tests
npm run test:integration
```

## 📈 Performance Monitoring

### Key Metrics
- Signal parsing success rate
- Trade execution latency
- MT5 connection stability
- Strategy performance analytics
- Risk management compliance

### Logging
- Execution logs: `logs/execution.log`
- Retry logs: `logs/retry_log.json`
- Sync logs: `logs/sync_log.json`
- Error alerts: Real-time via Telegram

## 🔐 Security

- JWT-based authentication
- Session management with PostgreSQL
- Environment variable encryption
- API rate limiting
- Input validation and sanitization
- SQL injection prevention

## 🆘 Troubleshooting

### Common Issues

**MT5 Connection Failed**
```bash
# Check MT5 terminal is running
# Verify login credentials in config.json
# Ensure MT5 allows automated trading
```

**Signal Parsing Errors**
```bash
# Check signal format compatibility
# Verify confidence threshold settings
# Review parser logs for detailed errors
```

**Database Connection Issues**
```bash
# Verify DATABASE_URL in .env
# Check PostgreSQL service status
# Run database migrations: npm run db:push
```

## 📝 API Documentation

### Authentication
```http
POST /api/login
POST /api/register
POST /api/logout
GET /api/user
```

### Signal Management
```http
GET /api/signals
POST /api/signals
POST /api/signals/:id/replay
POST /api/signals/parse
POST /api/signals/simulate
```

### Trading
```http
GET /api/trades
GET /api/trades/active
GET /api/dashboard/stats
```

### Firebridge (Desktop Integration)
```http
POST /api/firebridge/sync-user
POST /api/firebridge/error-alert
GET /api/firebridge/pull-strategy/:userId
POST /api/firebridge/push-trade-result
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes with comprehensive tests
4. Update documentation
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- MetaTrader 5 Python API
- Telegram Bot API
- React Query for state management
- Drizzle ORM for database operations
- shadcn/ui for component library

---

**Built for traders, by traders. Happy trading! 📈**