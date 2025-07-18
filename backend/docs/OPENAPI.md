# SignalOS Backend API Documentation

## OpenAPI Specification

The SignalOS Backend provides a comprehensive RESTful API for trading signal processing and execution. The API is automatically documented using OpenAPI 3.0 specification.

### Access Documentation

When running in development mode:
- **Swagger UI**: http://localhost:8000/api/docs
- **ReDoc**: http://localhost:8000/api/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

### Authentication

All API endpoints (except public ones) require JWT authentication:

```http
Authorization: Bearer <jwt_token>
```

### API Overview

#### Authentication Endpoints (`/api/v1/auth/`)
- `POST /login` - User authentication
- `POST /register` - User registration  
- `GET /license-status` - License validation
- `POST /refresh-token` - Token refresh
- `POST /logout` - User logout

#### Signal Processing (`/api/v1/signals/`)
- `POST /parse` - Parse signal (async)
- `POST /parse-sync` - Parse signal (sync)
- `POST /upload` - Upload image signal
- `POST /validate` - Validate signal data
- `GET /task/{task_id}` - Get task status
- `GET /stats` - Processing statistics
- `GET /history` - Signal history
- `DELETE /history/{signal_id}` - Delete signal

#### Trading Operations (`/api/v1/trading/`)
- `POST /initialize` - Initialize trading engine
- `POST /execute` - Execute trading signal
- `POST /close` - Close trading order
- `GET /orders` - List active orders
- `GET /orders/{order_id}` - Get order details
- `GET /stats` - Trading statistics
- `GET /account` - Account information
- `GET /symbols/{symbol}` - Symbol information
- `POST /test-connection` - Test MT5 connection
- `POST /shutdown` - Shutdown trading engine

#### Administration (`/api/v1/admin/`)
- `GET /system/status` - System status
- `GET /logs` - System logs
- `GET /queue/status` - Queue status
- `POST /queue/clear` - Clear queue
- `GET /users` - User management
- `GET /config` - System configuration
- `POST /config/update` - Update configuration
- `POST /maintenance/start` - Start maintenance
- `POST /maintenance/stop` - Stop maintenance

### Response Formats

#### Standard Success Response
```json
{
  "success": true,
  "data": {...},
  "message": "Operation completed successfully"
}
```

#### Standard Error Response
```json
{
  "error": "Error Type",
  "message": "Detailed error message",
  "status_code": 400,
  "error_id": "unique_error_id"
}
```

#### Signal Parse Response
```json
{
  "success": true,
  "parsed_signal": {
    "symbol": "EURUSD",
    "signal_type": "BUY",
    "entry_price": 1.1000,
    "stop_loss": 1.0950,
    "take_profit": [1.1050, 1.1100],
    "confidence": "HIGH",
    "parsing_method": "ai_primary",
    "timestamp": "2025-01-18T10:00:00Z"
  }
}
```

#### Trading Execution Response
```json
{
  "success": true,
  "order_id": "SIG_20250118_100000_123456",
  "order_data": {
    "symbol": "EURUSD",
    "order_type": 0,
    "volume": 0.01,
    "status": "EXECUTED",
    "ticket": 123456789,
    "executed_price": 1.1000,
    "executed_at": "2025-01-18T10:00:00Z"
  }
}
```

### Error Codes

| Code | Description |
|------|-------------|
| 200 | Success |
| 201 | Created |
| 400 | Bad Request |
| 401 | Unauthorized |
| 403 | Forbidden |
| 404 | Not Found |
| 422 | Validation Error |
| 500 | Internal Server Error |
| 503 | Service Unavailable |

### Rate Limiting

- **Default**: 100 requests per minute per user
- **Authentication**: 10 requests per minute
- **Signal Processing**: 50 requests per minute
- **Trading**: 20 requests per minute

### WebSocket Support

For real-time updates (future implementation):
- `ws://localhost:8000/ws/signals` - Signal processing updates
- `ws://localhost:8000/ws/trading` - Trading status updates
- `ws://localhost:8000/ws/system` - System notifications

### SDK Examples

#### Python SDK Example
```python
import httpx

class SignalOSClient:
    def __init__(self, base_url="http://localhost:8000", token=None):
        self.base_url = base_url
        self.token = token
        self.client = httpx.Client()
    
    def login(self, username, password, device_info):
        response = self.client.post(f"{self.base_url}/api/v1/auth/login", json={
            "username": username,
            "password": password,
            "device_info": device_info
        })
        if response.status_code == 200:
            self.token = response.json()["access_token"]
            self.client.headers["Authorization"] = f"Bearer {self.token}"
        return response.json()
    
    def parse_signal(self, text, auto_execute=False):
        return self.client.post(f"{self.base_url}/api/v1/signals/parse-sync", json={
            "text": text,
            "auto_execute": auto_execute
        }).json()
    
    def execute_signal(self, signal_data):
        return self.client.post(f"{self.base_url}/api/v1/trading/execute", json={
            "signal_data": signal_data
        }).json()
```

#### JavaScript SDK Example
```javascript
class SignalOSClient {
    constructor(baseUrl = "http://localhost:8000") {
        this.baseUrl = baseUrl;
        this.token = null;
    }
    
    async login(username, password, deviceInfo) {
        const response = await fetch(`${this.baseUrl}/api/v1/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                username,
                password,
                device_info: deviceInfo
            })
        });
        
        const data = await response.json();
        if (response.ok) {
            this.token = data.access_token;
        }
        return data;
    }
    
    async parseSignal(text, autoExecute = false) {
        return await this.request('/api/v1/signals/parse-sync', {
            text,
            auto_execute: autoExecute
        });
    }
    
    async request(endpoint, data) {
        const response = await fetch(`${this.baseUrl}${endpoint}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${this.token}`
            },
            body: JSON.stringify(data)
        });
        return await response.json();
    }
}
```

### Testing API

Use the following curl commands to test the API:

#### Authentication
```bash
# Login
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "test_user",
    "password": "test_password",
    "device_info": {"platform": "test"}
  }'

# Extract token and use in subsequent requests
TOKEN="<access_token_from_login>"
```

#### Signal Processing
```bash
# Parse signal
curl -X POST "http://localhost:8000/api/v1/signals/parse-sync" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "BUY EURUSD @ 1.1000 SL: 1.0950 TP: 1.1050"
  }'
```

#### Trading
```bash
# Execute signal
curl -X POST "http://localhost:8000/api/v1/trading/execute" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "signal_data": {
      "symbol": "EURUSD",
      "signal_type": "BUY",
      "entry_price": 1.1000,
      "stop_loss": 1.0950
    }
  }'
```

### Production Deployment

For production deployment, ensure:

1. **Security Headers**: Enable HTTPS and security headers
2. **Rate Limiting**: Configure appropriate rate limits
3. **Monitoring**: Set up health checks and monitoring
4. **Logging**: Configure structured logging
5. **Documentation**: Disable docs endpoints in production

```python
# Production settings
app = FastAPI(
    title="SignalOS Backend API",
    docs_url=None,  # Disable in production
    redoc_url=None  # Disable in production
)
```