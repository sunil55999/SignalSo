
# SignalOS Project - Complete Connection Documentation

## 📋 Project Overview

SignalOS is a comprehensive **Forex Signal Trading Automation Platform** that bridges Telegram signals with MetaTrader 5 (MT5) execution. The system consists of three main components:

1. **Web Dashboard** (React + TypeScript) - User interface for monitoring and control
2. **Backend Server** (Node.js + Express) - API and WebSocket server
3. **Desktop Application** (Python) - MT5 bridge and signal processing

## 🏗️ System Architecture

```
┌─────────────────┐    WebSocket/HTTP     ┌─────────────────┐
│  Web Dashboard  │ ◄──────────────────► │ Backend Server  │
│   (React/TS)    │                      │  (Node.js/TS)   │
└─────────────────┘                      └─────────────────┘
                                                    │
                                             HTTP API/WebSocket
                                                    │
                                                    ▼
┌─────────────────┐    MetaTrader API     ┌─────────────────┐
│ Desktop Python  │ ◄──────────────────► │  MetaTrader 5   │
│      App        │                      │   Terminal      │
└─────────────────┘                      └─────────────────┘
```

## 🔗 Desktop App ↔ Dashboard Connection Flow

### 1. Authentication & Registration

#### Desktop App Initialization
```python
# desktop-app/auth.py
class AuthTokenManager:
    def get_auth_token(self) -> str
    def validate_token(self) -> bool
    def store_auth_token(self, token: str) -> bool
```

**Process:**
1. Desktop app reads JWT token from `~/.signalos/auth_token`
2. Validates token against server `/api/me` endpoint
3. Registers terminal with unique ID and metadata
4. Server approves/denies desktop app connection

#### API Client Setup
```python
# desktop-app/api_client.py
class APIClient:
    def register_terminal(self) -> Dict[str, Any]
    def validate_terminal_auth(self) -> bool
    def report_status(self, status_data: Dict) -> Dict
```

### 2. Real-Time Communication (WebSocket)

#### Server WebSocket Infrastructure
```typescript
// server/routes.ts - WebSocket Server
interface WebSocketClient extends WebSocket {
  userId?: number;
  isAlive?: boolean;
}

interface ConnectedClients {
  [userId: number]: WebSocketClient[];
}
```

#### Client WebSocket Connection
```typescript
// client/src/lib/websocket.ts
export function useWebSocket() {
  const [connectionState, setConnectionState] = useState<ConnectionState>('disconnected');
  const [isConnected, setIsConnected] = useState(false);
  
  // Exponential backoff reconnection
  // Message queuing for offline scenarios
  // Heartbeat monitoring
}
```

### 3. Message Flow & Event Broadcasting

#### Desktop → Server → Dashboard
```
Desktop App Status Update
        ↓
   HTTP POST /api/firebridge/sync-user
        ↓
   Server processes and validates
        ↓
   WebSocket broadcast to user's dashboard
        ↓
   Dashboard updates UI in real-time
```

#### Dashboard → Server → Desktop
```
User clicks "Emergency Stop"
        ↓
   HTTP POST /api/trading/emergency-stop
        ↓
   Server validates and processes
        ↓
   WebSocket message to desktop app
        ↓
   Desktop app executes MT5 command
```

## 📡 WebSocket Message Types

### Server → Dashboard Messages
```json
{
  "type": "mt5_status_update",
  "data": {
    "isConnected": true,
    "balance": 10000,
    "equity": 10250,
    "freeMargin": 8500
  }
}

{
  "type": "trade_update",
  "data": {
    "tradeId": 123,
    "symbol": "EURUSD",
    "pnl": 25.50,
    "status": "open"
  }
}

{
  "type": "signal_created",
  "data": {
    "symbol": "GBPUSD",
    "action": "BUY",
    "entry": 1.2650
  }
}
```

### Dashboard → Server Messages
```json
{
  "type": "emergency_stop_command",
  "data": {
    "timestamp": "2025-01-23T14:30:00Z"
  }
}

{
  "type": "close_trade_command",
  "data": {
    "tradeId": 123,
    "timestamp": "2025-01-23T14:30:00Z"
  }
}
```

## 🔄 Desktop App Sync Process

### Firebridge API Endpoints

#### 1. User Sync
```typescript
POST /api/firebridge/sync-user
{
  "userId": 1,
  "terminalId": "TERM_123",
  "status": {
    "isConnected": true,
    "modules": {
      "mt5": {
        "connected": true,
        "account_info": {
          "balance": 10000,
          "equity": 10250
        }
      }
    }
  }
}
```

#### 2. Strategy Pull
```typescript
GET /api/firebridge/pull-strategy/1
Response: {
  "strategy": {
    "id": 1,
    "name": "Conservative Strategy",
    "config": {
      "riskPercentage": 2,
      "maxDailyTrades": 5
    }
  }
}
```

#### 3. Trade Result Push
```typescript
POST /api/firebridge/push-trade-result
{
  "userId": 1,
  "signalId": 123,
  "tradeResult": {
    "success": true,
    "mt5Ticket": 67890,
    "entryPrice": 1.1050
  }
}
```

## 🎛️ Dashboard Control Features

### Quick Actions Implementation
```typescript
// client/src/components/dashboard/quick-actions.tsx
const emergencyStopMutation = useMutation({
  mutationFn: () => fetch('/api/trading/emergency-stop', { method: 'POST' }),
  onSuccess: () => toast({ title: "Emergency Stop Activated" })
});

const pauseTradingMutation = useMutation({
  mutationFn: () => fetch('/api/trading/pause', { method: 'POST' }),
  onSuccess: () => toast({ title: "Trading Paused" })
});
```

### Trade Management
```typescript
// Close Trade
POST /api/trades/:id/close

// Partial Close
POST /api/trades/:id/partial-close
{ "percentage": 50 }

// Modify SL/TP
PUT /api/trades/:id/modify
{
  "stopLoss": 1.0950,
  "takeProfit": 1.1100
}
```

## 🔒 Security & Authentication

### JWT Token Flow
1. User logs in through web dashboard
2. Server issues JWT token
3. Token stored in desktop app via manual entry or QR code
4. Desktop app includes token in all API requests
5. Server validates token and user permissions

### File Security
```python
# desktop-app/secure_file_handler.py
class SecureFileHandler:
    def validate_path(self, file_path: str) -> bool
    def safe_read(self, file_path: str) -> str
    def safe_write(self, file_path: str, content: str) -> bool
```

## 📊 Data Flow Diagram

```
┌─────────────────┐
│   Telegram      │
│   Signals       │
└─────────┬───────┘
          │
          ▼
┌─────────────────┐    Parse & Validate    ┌─────────────────┐
│ Desktop Parser  │ ────────────────────► │   Database      │
│    Module       │                       │   Storage       │
└─────────┬───────┘                       └─────────────────┘
          │                                         │
          ▼                                         │
┌─────────────────┐                                 │
│  MT5 Bridge     │                                 │
│   Execution     │                                 │
└─────────┬───────┘                                 │
          │                                         │
          ▼                                         ▼
┌─────────────────┐    WebSocket Updates   ┌─────────────────┐
│   Trade Data    │ ────────────────────► │  Web Dashboard  │
│    Results      │                       │   Real-time     │
└─────────────────┘                       └─────────────────┘
```

## 🧩 Key Components

### Desktop App Modules
- **Parser**: Extracts trading signals from Telegram messages
- **MT5 Bridge**: Executes trades on MetaTrader 5
- **Strategy Engine**: Applies risk management and filters
- **API Client**: Communicates with backend server
- **Auth Manager**: Handles authentication and tokens

### Backend Server Features
- **RESTful API**: CRUD operations for signals, trades, strategies
- **WebSocket Server**: Real-time bidirectional communication
- **Authentication**: JWT-based secure access
- **Database**: SQLite with Drizzle ORM
- **Validation**: Comprehensive input sanitization

### Frontend Dashboard
- **Real-time Updates**: Live trade monitoring via WebSocket
- **Control Panel**: Emergency stop, pause/resume trading
- **Analytics**: Performance charts and statistics
- **Strategy Builder**: Visual strategy configuration
- **Provider Management**: Signal source configuration

## 🔧 Configuration Files

### Desktop App Config
```json
// desktop-app/config.json
{
  "server_url": "http://localhost:5000",
  "mt5_settings": {
    "magic_number": 12345,
    "slippage": 3
  },
  "strategy": {
    "risk_percentage": 2,
    "max_daily_trades": 10
  }
}
```

### Environment Variables
```bash
# Server
SESSION_SECRET=your-secret-key
DATABASE_URL=sqlite:///data.db
NODE_ENV=development

# Desktop App  
SIGNALOS_SERVER_URL=http://localhost:5000
MT5_LOGIN=12345678
MT5_PASSWORD=password123
```

## 🚀 Deployment Architecture

### Development (Replit)
- Frontend: Vite dev server on port 5173
- Backend: Express server on port 5000
- Database: SQLite file
- WebSocket: Same port as backend (/ws)

### Production
- Frontend: Built static files served by Express
- Backend: PM2 process manager
- Database: SQLite with automated backups
- SSL: Automatic HTTPS certificates

## 🔍 Monitoring & Logging

### Desktop App Logs
```python
# Logs stored in desktop-app/logs/
- retry_log.json          # Failed API requests
- rr_converter_log.json   # Risk/Reward adjustments
- conflict_log.json       # Signal conflicts
```

### Server Logs
```typescript
// Real-time logging via WebSocket
{
  "type": "error_alert",
  "data": {
    "error": "MT5 connection lost",
    "severity": "high",
    "timestamp": "2025-01-23T14:30:00Z"
  }
}
```

## 🎯 Future Enhancements

1. **Multi-Broker Support**: Extend beyond MT5 to other platforms
2. **AI Signal Analysis**: Machine learning for signal quality assessment
3. **Mobile App**: React Native companion app
4. **Cloud Deployment**: Scalable cloud infrastructure
5. **Advanced Analytics**: Detailed performance metrics

## 🏁 Getting Started

1. **Clone Repository**: `git clone <repo-url>`
2. **Install Dependencies**: `npm install`
3. **Setup Database**: `npm run db:migrate`
4. **Configure Desktop App**: Add JWT token to auth file
5. **Start Development**: `npm run dev`
6. **Access Dashboard**: Open browser to `http://localhost:5000`

This documentation provides a complete A-Z understanding of how SignalOS connects its desktop application with the user dashboard through secure authentication, real-time WebSocket communication, and comprehensive API integration.
