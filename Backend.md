
# SignalOS Backend - Complete Architecture Documentation

## 📋 Overview

The SignalOS Backend is a robust Node.js/Express server built with TypeScript that serves as the central communication hub between the web dashboard and desktop application. It provides RESTful APIs, WebSocket communication, authentication, and data persistence for the entire trading automation platform.

## 🏗️ Backend Architecture

### Technology Stack
- **Runtime**: Node.js with TypeScript
- **Framework**: Express.js with middleware stack
- **Database**: PostgreSQL with Drizzle ORM
- **WebSocket**: Native WebSocket server for real-time communication
- **Authentication**: Passport.js with session-based auth
- **Validation**: Zod schemas for type-safe data validation
- **Security**: Comprehensive input sanitization and CORS protection

### Core Components
```
server/
├── index.ts                 # Main server entry point
├── routes.ts               # API routing and WebSocket setup
├── auth.ts                 # Authentication middleware
├── storage.ts              # Database operations
├── db.ts                   # Database connection
├── vite.ts                 # Development server integration
├── api-versioning.ts       # API version management
├── encryption.ts           # Data encryption utilities
├── backup-recovery.ts      # Automated backup system
├── query-optimizer.ts      # Database performance optimization
└── dependency-audit.ts     # Security vulnerability scanning
```

## 🔄 Connection Architecture

### 1. Web Dashboard ↔ Backend Connection

#### HTTP/HTTPS API Communication
```typescript
// RESTful API endpoints for CRUD operations
GET    /api/dashboard/stats     # Dashboard metrics
GET    /api/signals            # Signal data
GET    /api/trades/live        # Active trades
POST   /api/trading/pause      # Trading controls
PUT    /api/trades/:id/modify  # Trade modifications
```

#### WebSocket Real-time Communication
```typescript
// WebSocket connection on /ws endpoint
const wsUrl = `${protocol}//${window.location.host}/ws`;

// Message types from server to dashboard
{
  type: 'signal_created',
  data: { signal, provider, confidence }
}
{
  type: 'trade_update',
  data: { tradeId, status, pnl, timestamp }
}
{
  type: 'mt5_status_update',
  data: { connected, balance, equity }
}
```

### 2. Desktop Application ↔ Backend Connection

#### Firebridge API Integration
```python
# Desktop app uses HTTP requests to sync with server
POST /api/firebridge/sync-user          # Regular status sync
POST /api/firebridge/push-trade-result  # Trade execution results
GET  /api/firebridge/pull-strategy/:id  # Strategy updates
POST /api/firebridge/error-alert        # Error reporting
POST /api/firebridge/heartbeat          # Connection health
```

#### Auto-Sync Engine
```python
# auto_sync.py - Continuous synchronization
class AutoSyncEngine:
    async def sync_with_server(self):
        # Collect desktop app status
        terminal_status = self._collect_terminal_status()
        
        # Send to server via Firebridge API
        response = await self._make_api_request(
            "/firebridge/sync-user", 
            "POST", 
            sync_payload
        )
        
        # Process server response
        if "strategy" in response:
            await self._handle_strategy_update(response["strategy"])
```

### 3. Three-Way Communication Flow

```
┌─────────────────┐    HTTP/WebSocket     ┌─────────────────┐
│  Web Dashboard  │ ◄──────────────────► │ Backend Server  │
│   (React/TS)    │                      │  (Node.js/TS)   │
└─────────────────┘                      └─────┬───────────┘
                                                │
                                         HTTP Firebridge API
                                                │
                                                ▼
┌─────────────────┐    MetaTrader API     ┌─────────────────┐
│ Desktop Python  │ ◄──────────────────► │      MT5        │
│   Application   │                      │   Terminal      │
└─────────────────┘                      └─────────────────┘
```

## 🛠️ Core Backend Features

### 1. Authentication System
```typescript
// auth.ts - Passport.js integration
export function setupAuth(app: Express) {
  app.use(session({
    secret: process.env.SESSION_SECRET,
    resave: false,
    saveUninitialized: false,
    cookie: { secure: false, maxAge: 24 * 60 * 60 * 1000 }
  }));
  
  app.use(passport.initialize());
  app.use(passport.session());
}

// Role-based access control
function requireRole(role: string) {
  return (req: any, res: any, next: any) => {
    if (!req.user || req.user.role !== role) {
      return res.status(403).json({ error: "Insufficient permissions" });
    }
    next();
  };
}
```

### 2. Database Operations
```typescript
// storage.ts - Drizzle ORM operations
export class DatabaseStorage {
  // Signal management
  async createSignal(data: any) {
    return await this.db.insert(signals).values(data).returning();
  }
  
  // Trade management
  async createTrade(data: any) {
    return await this.db.insert(trades).values(data).returning();
  }
  
  // MT5 status tracking
  async updateMt5Status(userId: number, status: any) {
    return await this.db.insert(mt5Status)
      .values({ userId, ...status })
      .onConflictDoUpdate({
        target: mt5Status.userId,
        set: status
      });
  }
}
```

### 3. WebSocket Server Implementation
```typescript
// routes.ts - WebSocket setup
const wsServer = new WebSocketServer({ 
  server: httpServer,
  path: '/ws',
  perMessageDeflate: false,
  maxPayload: 1024 * 1024
});

// Connected clients management
interface ConnectedClients {
  [userId: number]: WebSocketClient[];
}

// Broadcast to specific user
function broadcastToUser(userId: number, message: any) {
  const clients = connectedClients[userId];
  if (clients && clients.length > 0) {
    const messageStr = JSON.stringify({
      ...message,
      timestamp: new Date().toISOString(),
      id: `srv_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
    });
    
    clients.forEach(client => {
      if (client.readyState === WebSocket.OPEN) {
        client.send(messageStr);
      }
    });
  }
}
```

## 🔌 API Endpoints

### Dashboard APIs
```typescript
// Real-time trading control
POST /api/trading/emergency-stop    # Emergency stop all trading
POST /api/trading/pause             # Pause signal processing
POST /api/trading/resume            # Resume trading
POST /api/trading/stealth-toggle    # Toggle stealth mode

// Trade management
GET    /api/trades/live             # Active trades
POST   /api/trades/:id/close        # Close specific trade
POST   /api/trades/:id/partial-close # Partial close
PUT    /api/trades/:id/modify       # Modify SL/TP
POST   /api/trades/:id/trailing-stop # Enable trailing stop

// Analytics and monitoring
GET /api/dashboard/stats            # Dashboard statistics
GET /api/dashboard/performance      # Performance metrics
GET /api/providers/stats            # Signal provider analytics
GET /api/system/health              # System health check
```

### Firebridge APIs (Desktop Integration)
```typescript
// Desktop app synchronization
POST /api/firebridge/sync-user       # Regular status sync
POST /api/firebridge/push-trade-result # Trade execution results
GET  /api/firebridge/pull-strategy/:userId # Strategy retrieval
POST /api/firebridge/error-alert     # Error reporting
POST /api/firebridge/heartbeat       # Connection monitoring
POST /api/firebridge/force-sync      # Manual sync trigger

// Signal processing
POST /api/signals/parse              # Parse signal text
POST /api/signals/simulate           # Simulate trade execution
POST /api/signals/:id/replay         # Replay historical signal
GET  /api/signals/formats            # Supported formats
```

### Data Management APIs
```typescript
// Signal management
GET    /api/signals                 # List signals
POST   /api/signals                 # Create signal
POST   /api/signals/:id/replay      # Replay signal

// Strategy management
GET    /api/strategies              # User strategies
POST   /api/strategies              # Create strategy
PUT    /api/strategies/:id          # Update strategy

// Channel management
GET    /api/channels                # Signal channels
POST   /api/channels                # Create channel
PUT    /api/channels/:id            # Update channel
DELETE /api/channels/:id            # Delete channel
```

## 🔄 Real-time Communication Flow

### 1. Signal Processing Flow
```
Telegram Signal → Desktop Parser → Firebridge API → Backend Storage
                                                      ↓
Web Dashboard ← WebSocket Broadcast ← Signal Created Event
```

### 2. Trade Execution Flow
```
Signal Approved → Desktop MT5 Bridge → Trade Execution → MT5 Terminal
                                          ↓
Trade Result → Firebridge API → Backend Update → WebSocket Broadcast
                                                      ↓
                                              Web Dashboard Update
```

### 3. Status Monitoring Flow
```
Desktop Status → Auto Sync → Firebridge API → Backend Storage
                                                  ↓
MT5 Status Update → WebSocket Broadcast → Web Dashboard
```

## 🛡️ Security Features

### Input Validation & Sanitization
```typescript
// Comprehensive input validation
app.post("/api/firebridge/sync-user", [
  body('userId').isInt({ min: 1 }).withMessage('Valid user ID required'),
  body('terminalId').optional().isString().trim().escape(),
  body('status.isConnected').optional().isBoolean()
], async (req, res) => {
  const errors = validationResult(req);
  if (!errors.isEmpty()) {
    return res.status(400).json({ 
      error: "Validation failed", 
      details: errors.array().map(e => e.msg)
    });
  }
  // Process validated data
});
```

### Authentication & Authorization
```typescript
// WebSocket authentication
ws.on('message', (data) => {
  const message = JSON.parse(data.toString());
  
  if (message.type === 'authenticate') {
    const { sessionId, userId } = message.data || {};
    
    if (!isValidSession(sessionId, userId)) {
      ws.send(JSON.stringify({
        type: 'auth_failed',
        data: { message: 'Invalid session or unauthorized' }
      }));
      ws.close(4003, 'Invalid authentication');
      return;
    }
    
    // Add to authenticated clients
    connectedClients[userId] = connectedClients[userId] || [];
    connectedClients[userId].push(ws);
  }
});
```

### Data Encryption
```typescript
// encryption.ts - AES-256-GCM encryption
export class EncryptionService {
  encrypt(data: string): EncryptedData {
    const iv = crypto.randomBytes(16);
    const cipher = crypto.createCipher('aes-256-gcm', this.key);
    cipher.setAAD(Buffer.from('SignalOS', 'utf8'));
    
    let encrypted = cipher.update(data, 'utf8', 'hex');
    encrypted += cipher.final('hex');
    
    return {
      data: encrypted,
      iv: iv.toString('hex'),
      tag: cipher.getAuthTag().toString('hex')
    };
  }
}
```

## 📊 Performance Optimization

### Query Optimization
```typescript
// query-optimizer.ts - Database performance
export class QueryOptimizer {
  private cache = new Map<string, { data: any; expiry: number }>();
  
  async optimizedQuery(key: string, queryFn: () => Promise<any>, ttl = 300000) {
    const cached = this.cache.get(key);
    if (cached && Date.now() < cached.expiry) {
      return cached.data;
    }
    
    const result = await queryFn();
    this.cache.set(key, { data: result, expiry: Date.now() + ttl });
    return result;
  }
}
```

### Connection Pooling
```typescript
// db.ts - Database connection management
export const db = drizzle(postgres(DATABASE_URL, {
  max: 20,                    // Maximum connections
  idleTimeoutMillis: 30000,   // Close idle connections
  connectionTimeoutMillis: 2000, // Connection timeout
}));
```

## 🔧 Environment Configuration

### Required Environment Variables
```bash
# Database
DATABASE_URL=postgresql://user:pass@host:5432/signalos

# Authentication
SESSION_SECRET=your-secure-session-secret-key

# Server Configuration
NODE_ENV=production
PORT=5000

# Email Reporting (Optional)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
```

### Config.json Integration
```typescript
// Server reads desktop app config for integration
const config = {
  server: {
    url: "http://localhost:5000",
    websocket_url: "ws://localhost:5000/ws"
  },
  sync: {
    interval_seconds: 60,
    retry_attempts: 3,
    timeout_seconds: 10
  },
  firebridge: {
    endpoints: {
      sync: "/api/firebridge/sync-user",
      strategy: "/api/firebridge/pull-strategy",
      trade_result: "/api/firebridge/push-trade-result"
    }
  }
}
```

## 🚀 Deployment on Replit

### Production Configuration
```typescript
// index.ts - Production setup
const app = express();

// Security middleware
app.use(helmet());
app.use(cors({ origin: process.env.FRONTEND_URL || true }));
app.use(express.json({ limit: '10mb' }));

// Rate limiting
app.use(rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: 100 // Limit each IP to 100 requests per windowMs
}));

// Serve static files in production
if (app.get("env") === "production") {
  serveStatic(app);
} else {
  await setupVite(app, server);
}

// Always serve on port 5000 (Replit requirement)
server.listen(5000, "0.0.0.0", () => {
  console.log("SignalOS Backend serving on port 5000");
});
```

### Health Monitoring
```typescript
// System health endpoint
app.get("/api/health", async (req, res) => {
  const health = {
    status: 'healthy',
    timestamp: new Date().toISOString(),
    uptime: process.uptime(),
    memory: process.memoryUsage(),
    database: await testDatabaseConnection(),
    websocket: wsServer.clients.size,
    version: process.env.npm_package_version || '1.0.0'
  };
  
  res.json(health);
});
```

## 📈 Monitoring & Logging

### Request Logging
```typescript
// Comprehensive request logging
app.use((req, res, next) => {
  const start = Date.now();
  res.on("finish", () => {
    const duration = Date.now() - start;
    if (req.path.startsWith("/api")) {
      console.log(`${req.method} ${req.path} ${res.statusCode} in ${duration}ms`);
    }
  });
  next();
});
```

### Error Handling
```typescript
// Global error handler
app.use((err: any, req: Request, res: Response, next: NextFunction) => {
  const status = err.status || err.statusCode || 500;
  const message = err.message || "Internal Server Error";
  
  console.error(`Error ${status}: ${message}`, err.stack);
  res.status(status).json({ message });
});
```

This comprehensive backend architecture ensures robust, scalable, and secure communication between all SignalOS components while maintaining high performance and reliability.
