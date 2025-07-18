# SignalOS Backend

A production-grade trading signal processing and execution backend service designed for professional traders.

## Overview

SignalOS Backend provides intelligent signal processing, real-time market monitoring, and advanced trading automation with a modern, API-first architecture.

## Features

### Core Capabilities
- **AI-Powered Signal Parsing**: Hybrid LLM + regex engine for accurate signal extraction
- **Real-time Trade Execution**: MT5/MT4 integration with advanced risk management  
- **Background Task Processing**: Async queue system for scalable operations
- **JWT Authentication**: Secure licensing and device-based authentication
- **RESTful API**: Comprehensive API with OpenAPI documentation

### Advanced Features
- **Multi-level Fallback**: AI parsing with regex fallback for reliability
- **Risk Management**: Position sizing, margin checking, and daily limits
- **Queue Management**: Priority-based task processing with retry logic
- **Monitoring & Logging**: Comprehensive logging and system monitoring
- **Admin Interface**: System administration and monitoring endpoints

## Architecture

```
backend/
├── api/             # FastAPI route handlers
├── core/            # Core business logic (auth, trading)
├── db/              # Database models and schema
├── services/        # External services (AI parser, MT5 bridge)
├── workers/         # Background task processing
├── utils/           # Shared utilities and logging
├── config/          # Configuration and settings
├── middleware/      # Authentication and error handling
├── tests/           # Unit and integration tests
├── docs/            # Documentation
├── logs/            # Application logs
└── main.py          # Application entry point
```

## Quick Start

### Prerequisites
- Python 3.8+
- MT5 Terminal (for trading functionality)
- Redis (optional, for production queue management)

### Installation

1. **Install Dependencies**
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

2. **Configuration**
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

3. **Run Development Server**
   ```bash
   python main.py
   ```

4. **Access API Documentation**
   - Swagger UI: http://localhost:8000/api/docs
   - ReDoc: http://localhost:8000/api/redoc

## API Endpoints

### Authentication
- `POST /api/v1/auth/login` - User login
- `POST /api/v1/auth/register` - User registration
- `GET /api/v1/auth/license-status` - License validation
- `POST /api/v1/auth/refresh-token` - Token refresh

### Signal Processing
- `POST /api/v1/signals/parse` - Parse signal (async)
- `POST /api/v1/signals/parse-sync` - Parse signal (sync)
- `POST /api/v1/signals/upload` - Upload signal image
- `GET /api/v1/signals/stats` - Processing statistics
- `GET /api/v1/signals/history` - Signal history

### Trading
- `POST /api/v1/trading/initialize` - Initialize trading engine
- `POST /api/v1/trading/execute` - Execute trading signal
- `POST /api/v1/trading/close` - Close trading order
- `GET /api/v1/trading/orders` - Active orders
- `GET /api/v1/trading/stats` - Trading statistics
- `GET /api/v1/trading/account` - Account information

### Administration
- `GET /api/v1/admin/system/status` - System status
- `GET /api/v1/admin/logs` - System logs
- `GET /api/v1/admin/queue/status` - Queue status
- `GET /api/v1/admin/users` - User management

## Configuration

### Environment Variables

```bash
# Application
ENVIRONMENT=development
DEBUG=true
HOST=0.0.0.0
PORT=8000

# Security
SECRET_KEY=your-secret-key-here
JWT_SECRET_KEY=your-jwt-secret-here
JWT_EXPIRATION_HOURS=24

# Database
DATABASE_URL=sqlite:///./signalos.db

# MT5 Trading
MT5_HOST=localhost
MT5_PORT=9999
MT5_TIMEOUT=30

# AI/ML
AI_CONFIDENCE_THRESHOLD=0.8
AI_MAX_TOKENS=1000

# Trading Limits
MAX_DAILY_TRADES=50
MAX_RISK_PER_TRADE=0.02
DEFAULT_LOT_SIZE=0.01
```

### Features Configuration

Each license can be configured with specific features:

```json
{
  "signal_parsing": true,
  "auto_trading": true,
  "advanced_strategies": true,
  "telegram_integration": true,
  "multi_account": false
}
```

## Usage Examples

### 1. Authentication

```python
import httpx

# Login
response = httpx.post("http://localhost:8000/api/v1/auth/login", json={
    "username": "trader1",
    "password": "secure_password",
    "device_info": {
        "platform": "Windows",
        "processor": "Intel i7",
        "memory": "16GB"
    }
})

token = response.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}
```

### 2. Parse Trading Signal

```python
# Parse text signal
response = httpx.post(
    "http://localhost:8000/api/v1/signals/parse-sync",
    headers=headers,
    json={
        "text": "BUY EURUSD @ 1.1000 SL: 1.0950 TP: 1.1050",
        "auto_execute": false
    }
)

parsed_signal = response.json()["parsed_signal"]
```

### 3. Execute Trade

```python
# Execute parsed signal
response = httpx.post(
    "http://localhost:8000/api/v1/trading/execute",
    headers=headers,
    json={
        "signal_data": parsed_signal,
        "auto_execute": true
    }
)

order_id = response.json()["order_id"]
```

## Testing

### Run Tests
```bash
cd backend
pytest tests/ -v
```

### Test Coverage
```bash
pytest tests/ --cov=. --cov-report=html
```

### Integration Tests
```bash
# Test with real MT5 connection
pytest tests/integration/ -v --mt5-live
```

## Deployment

### Production Configuration

1. **Environment Setup**
   ```bash
   export ENVIRONMENT=production
   export DEBUG=false
   export SECRET_KEY=production-secret-key
   ```

2. **Database Setup**
   ```bash
   # Use PostgreSQL for production
   export DATABASE_URL=postgresql://user:pass@localhost/signalos
   ```

3. **Run with Gunicorn**
   ```bash
   gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker
   ```

### Docker Deployment

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["python", "main.py"]
```

## Monitoring

### Health Checks
- `GET /health` - Basic health check
- `GET /api/v1/admin/system/status` - Detailed system status

### Logging
- Application logs: `./logs/signalos.log`
- Access logs: Uvicorn default
- Error tracking: Structured logging with correlation IDs

### Metrics
- Processing statistics via `/api/v1/signals/stats`
- Trading performance via `/api/v1/trading/stats`
- System metrics via `/api/v1/admin/system/status`

## Security

### Authentication
- JWT-based authentication with device fingerprinting
- License-based feature access control
- Session management with token refresh

### Data Protection
- Password hashing with bcrypt
- Input validation and sanitization
- SQL injection protection via SQLAlchemy ORM

### API Security
- CORS configuration
- Rate limiting (configurable)
- Request/response validation with Pydantic

## Troubleshooting

### Common Issues

1. **MT5 Connection Failed**
   ```bash
   # Check MT5 bridge is running
   # Verify MT5_HOST and MT5_PORT settings
   # Ensure MT5 Expert Advisor is loaded
   ```

2. **Signal Parsing Failed**
   ```bash
   # Check AI model availability
   # Verify signal format
   # Review parsing confidence threshold
   ```

3. **Authentication Errors**
   ```bash
   # Check JWT_SECRET_KEY configuration
   # Verify token expiration settings
   # Review license validation
   ```

### Debug Mode

```bash
export DEBUG=true
export LOG_LEVEL=DEBUG
python main.py
```

## Development

### Code Style
- Black formatting
- isort import sorting
- Type hints required
- Docstring documentation

### Contributing
1. Fork the repository
2. Create feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit pull request

### Development Tools
```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Format code
black .
isort .

# Type checking
mypy .

# Linting
flake8 .
```

## Support

### Documentation
- API Docs: `/api/docs`
- This README: Core setup and usage
- Code Comments: Inline documentation

### Logging
All operations are logged with appropriate levels:
- `DEBUG`: Detailed execution flow
- `INFO`: General operations
- `WARNING`: Potential issues
- `ERROR`: Operation failures
- `CRITICAL`: System failures

For additional support, review the logs in `./logs/` directory and check the admin endpoints for system status.