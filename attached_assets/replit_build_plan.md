# 🧠 SignalOS Replit Upgrade Plan (Full + Detailed + Trackable)

> This file defines a full upgrade path for Replit Agent to finish SignalOS cleanly, robustly, and without duplication. It includes:
>
> - All missing feature implementations
> - Strict file boundaries
> - Real-time tracking setup (changelog + status)
> - Testing & deployment workflows

---

## 🧼 Phase 0: Clean Structure Enforcement

### 📁 Re-organize into this permanent layout:

```
signalos/
├── desktop-app/         # Python: MT5 Executor, Parser, Retry Engine, Copilot
├── server/              # Express + TypeScript: API, DB, Auth, Firebridge
├── client/              # React + TypeScript: Dashboard (User/Admin)
├── shared/              # Shared JSON/Zod schemas (used across modules)
├── logs/                # Execution, retry, sync logs
├── deployment/          # Docker, PM2 configs, .env.template
└── attached_assets/     # Runtime changelog + status checklist
```

### 🔁 Files to auto-generate:

- `attached_assets/dev_changelog.md`: append every file change
- `attached_assets/feature_status.md`: markdown checklist of features

---

## 🚀 Phase 1: Missing Feature Completion Checklist

### 🔹 A. Desktop App (Python)

#### `signal_parser.py`

- AI + regex hybrid parser
- Supports: BUY, SELL, SL, TP1–TP5, ENTRY
- Parses from both text and OCR image (if module exists)
- Outputs structured JSON + confidence score

#### `mt5_bridge.py`

- Place trade (market + pending)
- Modify trade (move SL, partial close, close)
- Return ticket, log result, handle MT5 disconnect

#### `retry_engine.py`

- Buffer failed trades
- Retry up to N times
- Check spread, slippage, latency
- Store result in `logs/retry_log.json`

#### `strategy_runtime.py`

- Parse rules like:
  - IF TP1 hit → Move SL to Entry
  - IF Confidence < 70 → Abort
- Accepts parsed signal + strategy JSON
- Outputs trade execution package

#### `auto_sync.py`

- Every 60 seconds:
  - Pull strategy from `/firebridge/sync-user`
  - Push terminal/health status
  - Detect if parser version is outdated

#### `copilot_bot.py`

- Telegram bot handles:
  - /status, /pause, /stealth, /replay, /alert
  - Sends alert on failed trade or parser error
  - Shows inline YES/NO buttons for retry confirmation

---

### 🔹 B. Server (Express + TypeScript)

#### `routes/firebridge.ts`

- `/sync-user` – return strategy config
- `/error-alert` – accept error log from desktop
- `/pull-strategy/:userId` – get full strategy pack

#### `routes/signal.ts`

- `/parse` → returns signal JSON from message
- `/simulate` → dry-run execution plan from parsed signal
- `/replay/:signalId` → triggers re-run of past signal

#### `routes/strategy.ts`

- POST `/push` → save/update strategy JSON
- GET `/pull/:uid` → return strategy config
- Supports named strategy versions

#### `websocket.ts`

- Client connections:
  - Join with session ID (user)
- Emit events:
  - `signal_parsed`, `trade_executed`, `retry_attempted`, `parser_error`, `status`

#### `auth.ts`

- JWT auth + refresh
- Middleware with roles: `user`, `admin`

---

### 🔹 C. Dashboard (React + TypeScript)

#### `/dashboard`

- Realtime health status for MT5 (via WebSocket)
- Retry queue monitor
- Signal activity feed

#### `/signals`

- Replay button next to each signal
- Parse/test signal manually from message input

#### `/strategy`

- Visual strategy builder (React Flow)
- Export JSON from drag-drop logic blocks
- View + test execution path for logic

#### `/admin`

- Manage:
  - Telegram channels
  - User roles
  - Force sync / test signal push

---

## 🧪 Phase 2: Testing & QA

Create per-module test files:

### Desktop Tests (`/desktop-app/tests/`)

- `test_parser.py` → 10+ real-world signals
- `test_retry.py` → simulate MT5 down
- `test_strategy.py` → validate TP1 triggers SL move

### Server Tests (`/server/tests/`)

- All API endpoints covered
- Mock Firebridge signals
- WebSocket message emit success

### Frontend Tests (`/client/__tests__/`)

- Form validation, signal testing logic
- Replay flow end-to-end
- Admin UI functionality

---

## 🗂 Phase 3: Runtime Dev Tracking System

### `attached_assets/dev_changelog.md`

```md
## [2025-06-22] - Added retry_engine.py
- Created retry logic for MT5 auto-execution
- Connected with `mt5_bridge.py`
```

### `attached_assets/feature_status.md`

```md
- [x] Parser module (basic)
- [x] Trade executor
- [ ] Retry buffer w/ smart logic
- [ ] Telegram bot command routing
- [ ] Strategy visual builder (UI)
- [ ] Firebridge sync + strategy pull
- [ ] Signal replay from dashboard
```

> These must be updated every time Replit adds/changes features. They are the single source of dev truth.

---

## 🛠 Phase 4: Deployment Checklist

### PM2

- Run: `desktop-app/index.py`, `copilot_bot.py`, `auto_sync.py`
- Watch logs: stdout + custom `logs/*.json`

### Docker

- `Dockerfile` for `/server`
- `docker-compose.yml` for `server + db + optional proxy`
- `.env.template` with defaults:
  - `PORT=5000`
  - `DB_URL=postgres://...`
  - `MT5_PATH=C:\Program Files\...`
  - `JWT_SECRET=...`

---

## 🔐 Phase 5: Final Enforcement Rules

- ✅ Replit must check `dev_changelog.md` before starting any task
- ✅ Update `feature_status.md` after every addition
- ✅ Respect folder boundaries:
  - Python → `desktop-app/`
  - API/DB → `server/`
  - Web UI → `client/`
- ✅ Shared logic goes in `/shared/schema/`
- ✅ Do not include Firebase, Gemini, or mobile

---

## ✅ END RESULT

If followed exactly, this plan will result in:

- ✅ Clean architecture (no overlap/mess)
- ✅ All promised SignalOS features implemented
- ✅ Real-time signals, parsing, execution, retries, alerts
- ✅ Admin + User dashboards fully functional
- ✅ One-click deploy with logs, roles, and sync

Ready for deployment to any VPS with 8GB+ RAM. Let’s finish SignalOS strong. 💥

