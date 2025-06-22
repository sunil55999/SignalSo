# 🧠 Replit Agent Build Plan for SignalOS

> This file contains detailed prompts and development guidance for Replit Agent to handle backend, desktop logic, MT5 integration, and web dashboard development. Keep all changes scoped to assigned directories.

---

## 📁 Folders Under Replit's Control

```
signalos/
├── desktop-app/         ✅ MT5, Parser, Retry Engine
├── admin-panel/         ✅ Express API, Sync Layer
├── dashboard/           ✅ Web UI with React + TS
├── shared/              ✅ Shared schemas + types
├── deployment/          ✅ Docker, PM2 setup
```

---

## 🧠 Desktop App Prompts

### `SignalParser.py`

```prompt
Create a Python class `SignalParser` that:
- Parses Telegram signal messages
- Supports BUY/SELL, pending orders
- Extracts Entry, SL, TP1–TP5
- Returns parsed JSON with confidence score
```

### `SmartRetryExecutor.py`

```prompt
Develop a retry engine that:
- Buffers failed trades
- Retries trades based on MT5 connection, slippage, spread
- Logs retries in `retry_log.json`
- Configurable via `config.json`
```

### `mt5_bridge.py`

```prompt
Use MetaTrader5 Python API to:
- Open MT5 trades from parsed signals
- Support stealth mode (hide SL/TP, comments)
- Validate trade success and return ticket
```

### `copilot_bot.py`

```prompt
Build a Telegram bot that:
- Responds to /status, /trades, /replay, /stealth
- Sends alert on errors or failed trades
- Uses python-telegram-bot library
```

### `auto_sync.py`

```prompt
Poll the `/api/firebridge/sync-user` endpoint every 60s:
- Download updated strategy
- Push terminal and parser status
- Save sync logs to `sync_log.json`
```

### `strategy_runtime.py`

```prompt
Load signal + strategy JSON
- Evaluate logic like IF TP1 Hit → Move SL to Entry
- Return adjusted signal JSON for execution
```

---

## ⚙️ Admin Panel Prompts

### Auth

```prompt
Build JWT-based session management:
- /auth/login
- /auth/logout
- /auth/refresh
```

### User, Channel & Strategy APIs

```prompt
Create REST APIs for:
- /users, /channels (CRUD)
- /strategy/push, /strategy/pull
- /parser/push (accept .py file)
```

### Firebridge Sync APIs

```prompt
Create bridge endpoints:
- POST /firebridge/sync-user
- POST /firebridge/error-alert
- GET /firebridge/pull-strategy/:userId
```

### WebSocket (MT5 Health)

```prompt
Allow desktop app to push status updates
- `socket.emit("status", { terminalId, online: true, latency })`
```

---

## 🎨 Dashboard Prompts (React)

### Pages

```prompt
1. Dashboard → shows live trades
2. Strategy → JSON + Visual builder
3. Signals → History + Replay
4. Admin → Channel/User manager
```

### Strategy Builder (React Flow)

```prompt
Use React Flow to:
- Create drag/drop blocks like:
  [IF Confidence < 70%] → [Skip Trade]
- Output JSON config from visual layout
```

### Signal Replay

```prompt
Add a "Replay" button to signal history row:
- Sends /api/signal/replay
- Desktop picks and re-executes
```

---

## 🧪 Testing Checklist

```prompt
- [ ] SignalParser unit test (10 formats)
- [ ] RetryEngine retry cycle test (mock MT5)
- [ ] API routes tested with Postman
- [ ] Dashboard interaction (React Query logs)
- [ ] WebSocket MT5 ping emulation
```

---

## 📦 Deployment Tasks

```prompt
- Dockerfile for admin-panel
- PM2 config for desktop-app modules
- .env for secure config injection
```

Use this file **only with Replit Agent**. All Gemini 2.5 instructions are in `gemini_build_plan.md`.

