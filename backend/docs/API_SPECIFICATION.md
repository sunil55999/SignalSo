# SignalOS Backend API Specification

## Base URL
```
Production: https://api.signalos.com/v1
Development: http://localhost:8000/api/v1
```

## Authentication
All API endpoints require authentication via JWT Bearer tokens unless otherwise specified.

```http
Authorization: Bearer <your_jwt_token>
```

---

## 1. Authentication Endpoints

### 1.1 User Registration
```http
POST /auth/register
Content-Type: application/json

{
  "username": "string",
  "email": "string",
  "password": "string",
  "license_key": "string"
}
```

**Response:**
```json
{
  "id": "user_123",
  "username": "trader",
  "email": "trader@example.com",
  "license_type": "premium",
  "created_at": "2025-01-18T10:30:00Z"
}
```

### 1.2 User Login
```http
POST /auth/login
Content-Type: application/json

{
  "username": "string",
  "password": "string",
  "device_fingerprint": "string"
}
```

**Response:**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer",
  "expires_in": 3600,
  "refresh_token": "refresh_token_here",
  "user": {
    "id": "user_123",
    "username": "trader",
    "license_type": "premium"
  }
}
```

### 1.3 Token Refresh
```http
POST /auth/refresh
Content-Type: application/json

{
  "refresh_token": "string"
}
```

### 1.4 License Verification
```http
POST /auth/verify-license
Content-Type: application/json

{
  "license_key": "string",
  "device_fingerprint": "string"
}
```

---

## 2. Signal Processing Endpoints

### 2.1 Parse Signal
```http
POST /signals/parse
Content-Type: application/json

{
  "text": "BUY XAUUSD at 1950.00 TP: 1965.00 SL: 1940.00",
  "source": "telegram",
  "provider_id": "provider_123",
  "image_data": "base64_encoded_image_optional"
}
```

**Response:**
```json
{
  "success": true,
  "signal": {
    "id": "signal_456",
    "symbol": "XAUUSD",
    "action": "BUY",
    "entry_price": 1950.00,
    "take_profit": [1965.00],
    "stop_loss": 1940.00,
    "volume": 0.1,
    "confidence": 0.95,
    "parsed_method": "ai_llm",
    "parsed_at": "2025-01-18T10:30:00Z",
    "provider": {
      "id": "provider_123",
      "name": "Gold Signals Pro"
    }
  }
}
```

### 2.2 Import Signals
```http
POST /signals/import
Content-Type: application/json

{
  "signals": [
    {
      "text": "string",
      "source": "string",
      "provider_id": "string",
      "timestamp": "2025-01-18T10:30:00Z"
    }
  ]
}
```

### 2.3 Get Signal History
```http
GET /signals/history?limit=50&offset=0&provider_id=provider_123&symbol=XAUUSD
```

**Response:**
```json
{
  "signals": [
    {
      "id": "signal_456",
      "symbol": "XAUUSD",
      "action": "BUY",
      "entry_price": 1950.00,
      "status": "executed",
      "created_at": "2025-01-18T10:30:00Z"
    }
  ],
  "total": 150,
  "limit": 50,
  "offset": 0,
  "has_more": true
}
```

### 2.4 Manage Signal Providers
```http
GET /signals/providers
POST /signals/providers
PUT /signals/providers/{id}
DELETE /signals/providers/{id}
```

---

## 3. Trading Endpoints

### 3.1 Open Trade
```http
POST /trades/open
Content-Type: application/json

{
  "symbol": "XAUUSD",
  "type": "BUY",
  "volume": 0.1,
  "price": 1950.00,
  "sl": 1940.00,
  "tp": [1965.00, 1970.00],
  "comment": "Signal from provider_123"
}
```

**Response:**
```json
{
  "success": true,
  "ticket": 12345,
  "message": "Trade opened successfully for XAUUSD",
  "details": {
    "symbol": "XAUUSD",
    "type": "BUY",
    "volume": 0.1,
    "price": 1950.00,
    "sl": 1940.00,
    "tp": [1965.00, 1970.00],
    "spread": 0.5,
    "commission": 0.0
  }
}
```

### 3.2 Close Trade
```http
POST /trades/close
Content-Type: application/json

{
  "ticket": 12345,
  "volume": 0.1,
  "reason": "Take profit hit"
}
```

### 3.3 Modify Trade
```http
POST /trades/modify
Content-Type: application/json

{
  "ticket": 12345,
  "sl": 1945.00,
  "tp": 1970.00
}
```

### 3.4 Get Trade Status
```http
GET /trades/status?symbol=XAUUSD&ticket=12345
```

**Response:**
```json
[
  {
    "ticket": 12345,
    "symbol": "XAUUSD",
    "type": "BUY",
    "volume": 0.1,
    "price_open": 1950.00,
    "price_current": 1955.00,
    "sl": 1940.00,
    "tp": 1965.00,
    "profit_loss": 50.00,
    "profit_loss_percentage": 0.26,
    "duration_seconds": 3600,
    "status": "open"
  }
]
```

### 3.5 Get Trade History
```http
GET /trades/history?limit=50&offset=0&symbol=XAUUSD&from=2025-01-01&to=2025-01-31
```

### 3.6 Bulk Close Trades
```http
POST /trades/bulk-close
Content-Type: application/json

{
  "symbol": "XAUUSD",
  "profit_threshold": 100.0,
  "loss_threshold": -50.0
}
```

### 3.7 Get Account Information
```http
GET /trades/account
```

**Response:**
```json
{
  "login": 12345,
  "balance": 10000.00,
  "equity": 10500.00,
  "margin": 500.00,
  "free_margin": 9500.00,
  "margin_level": 2100.00,
  "profit": 500.00,
  "currency": "USD",
  "leverage": 100,
  "server": "MetaQuotes-Demo"
}
```

### 3.8 Get Symbol Information
```http
GET /trades/symbols/{symbol}
```

---

## 4. Analytics Endpoints

### 4.1 Get Summary Analytics
```http
GET /analytics/summary?timeframe=1M&from=2025-01-01&to=2025-01-31
```

**Response:**
```json
{
  "total_trades": 150,
  "winning_trades": 90,
  "losing_trades": 60,
  "win_rate": 60.0,
  "total_pnl": 2500.75,
  "total_pnl_percentage": 12.5,
  "average_win": 125.50,
  "average_loss": -75.25,
  "profit_factor": 2.1,
  "max_drawdown": 8.3,
  "max_drawdown_percentage": 4.2,
  "sharpe_ratio": 1.8,
  "sortino_ratio": 2.3,
  "calmar_ratio": 3.0,
  "average_trade_duration": 3600,
  "best_trade": 500.00,
  "worst_trade": -200.00,
  "consecutive_wins": 5,
  "consecutive_losses": 3,
  "total_volume": 15.0,
  "average_latency_ms": 85.2
}
```

### 4.2 Get Provider Analytics
```http
GET /analytics/providers
GET /analytics/provider/{provider_id}
```

**Response:**
```json
{
  "provider_id": "provider_123",
  "provider_name": "Gold Signals Pro",
  "total_signals": 100,
  "executed_signals": 85,
  "execution_rate": 85.0,
  "win_rate": 65.0,
  "total_pnl": 1200.50,
  "average_signal_quality": 0.87,
  "performance_rating": "A",
  "last_signal_at": "2025-01-18T10:30:00Z"
}
```

### 4.3 Get Symbol Analytics
```http
GET /analytics/symbol/{symbol}?timeframe=1M
```

### 4.4 Get Performance Chart Data
```http
GET /analytics/chart?timeframe=1M&chart_type=cumulative_pnl
```

**Response:**
```json
{
  "labels": ["2025-01-01", "2025-01-02", "2025-01-03"],
  "datasets": [
    {
      "label": "Cumulative P&L",
      "data": [0, 150.25, 275.50],
      "type": "line"
    },
    {
      "label": "Daily P&L",
      "data": [0, 150.25, 125.25],
      "type": "bar"
    }
  ]
}
```

### 4.5 Generate PDF Report
```http
POST /analytics/report/pdf
Content-Type: application/json

{
  "timeframe": "1M",
  "include_charts": true,
  "include_provider_analysis": true,
  "user_name": "John Trader"
}
```

**Response:**
```json
{
  "report_id": "report_123",
  "download_url": "/analytics/report/pdf/report_123",
  "file_size": 2048576,
  "generated_at": "2025-01-18T10:30:00Z"
}
```

### 4.6 Get Performance Metrics
```http
GET /analytics/performance-metrics?timeframe=1M
```

### 4.7 Get Risk Metrics
```http
GET /analytics/risk-metrics?timeframe=1M
```

---

## 5. System Health Endpoints

### 5.1 Basic Health Check
```http
GET /status/health
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-01-18T10:30:00Z"
}
```

### 5.2 Kubernetes Health Check
```http
GET /status/healthz
```

### 5.3 Readiness Check
```http
GET /status/ready
```

### 5.4 Detailed Health Check
```http
GET /status/health/detailed
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-01-18T10:30:00Z",
  "version": "1.0.0",
  "uptime": 86400,
  "components": {
    "database": {
      "status": "healthy",
      "response_time": 15
    },
    "mt5_bridge": {
      "status": "healthy",
      "response_time": 45
    },
    "auth_system": {
      "status": "healthy",
      "response_time": 8
    },
    "signal_parser": {
      "status": "healthy",
      "response_time": 120
    }
  },
  "metrics": {
    "cpu_usage": 25.5,
    "memory_usage": 45.2,
    "disk_usage": 12.8,
    "active_connections": 15,
    "requests_per_minute": 180
  }
}
```

### 5.5 System Metrics
```http
GET /status/metrics
```

### 5.6 Version Information
```http
GET /status/version
```

---

## 6. Administrative Endpoints

### 6.1 User Management
```http
GET /admin/users?limit=50&offset=0
POST /admin/users
PUT /admin/users/{id}
DELETE /admin/users/{id}
```

### 6.2 System Logs
```http
GET /admin/logs?level=error&limit=100&from=2025-01-01
```

### 6.3 Settings Management
```http
GET /admin/settings
PUT /admin/settings
```

---

## Error Responses

### Standard Error Format
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid input data",
    "details": {
      "field": "symbol",
      "issue": "Symbol not found"
    },
    "timestamp": "2025-01-18T10:30:00Z",
    "request_id": "req_123456"
  }
}
```

### HTTP Status Codes
- `200` - Success
- `201` - Created
- `400` - Bad Request
- `401` - Unauthorized
- `403` - Forbidden
- `404` - Not Found
- `422` - Validation Error
- `429` - Rate Limited
- `500` - Internal Server Error

### Rate Limiting
Headers returned when rate limited:
```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1642500000
Retry-After: 60
```

---

## WebSocket Endpoints

### Real-time Trade Updates
```
ws://localhost:8000/ws/trades
```

### Real-time Signal Updates
```
ws://localhost:8000/ws/signals
```

### System Status Updates
```
ws://localhost:8000/ws/status
```

---

## SDK Examples

### Python SDK
```python
import signalos

client = signalos.Client(
    base_url="http://localhost:8000/api/v1",
    token="your_jwt_token"
)

# Parse a signal
signal = client.signals.parse(
    text="BUY XAUUSD at 1950.00 TP: 1965.00 SL: 1940.00",
    source="telegram"
)

# Open a trade
trade = client.trades.open(
    symbol="XAUUSD",
    type="BUY",
    volume=0.1,
    price=1950.00,
    sl=1940.00,
    tp=[1965.00]
)

# Get analytics
analytics = client.analytics.summary(timeframe="1M")
```

### JavaScript SDK
```javascript
const SignalOS = require('signalos-js');

const client = new SignalOS({
  baseURL: 'http://localhost:8000/api/v1',
  token: 'your_jwt_token'
});

// Parse a signal
const signal = await client.signals.parse({
  text: 'BUY XAUUSD at 1950.00 TP: 1965.00 SL: 1940.00',
  source: 'telegram'
});

// Open a trade
const trade = await client.trades.open({
  symbol: 'XAUUSD',
  type: 'BUY',
  volume: 0.1,
  price: 1950.00,
  sl: 1940.00,
  tp: [1965.00]
});

// Get analytics
const analytics = await client.analytics.summary({ timeframe: '1M' });
```

---

## Testing

### Test Credentials
```
Username: test@signalos.com
Password: TestPassword123
API Key: test_api_key_123
```

### Test Data
Sample signals and trades are available in the test environment for integration testing.

---

*API Version: 1.0.0*
*Last Updated: January 18, 2025*