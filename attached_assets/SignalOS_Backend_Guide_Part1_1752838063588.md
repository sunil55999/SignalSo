
# 🧱 SignalOS Backend Guide – Part 1: Structure, Setup, & Environment

📍 All development MUST stay inside `/backend`

---

## 📂 Folder Structure (Standardized)

```
backend/
├── api/             # Route handlers (FastAPI / Express endpoints)
├── core/            # Core logic: auth, licensing, parsing, trade flow
├── db/              # DB models, schema, and migrations
├── services/        # External services (Telegram, MT5, OCR, AI)
├── workers/         # Background tasks for parsing, sync, retry
├── utils/           # Shared utils (logging, parsing helpers)
├── config/          # Env files, app settings, constants
├── middleware/      # Auth checkers, error handlers
├── tests/           # All unit/integration tests
├── docs/            # Backend developer + AI agent docs
├── logs/            # System and audit logs
└── main.py          # Application entry point
```

---

## ⚙️ Initial Setup (Python Stack)

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install fastapi uvicorn pydantic sqlalchemy celery python-dotenv
```

Or with Node.js:

```bash
npm init -y
npm install express dotenv zod drizzle-orm bullmq jsonwebtoken axios
```

---

## 🔑 Entry Files

```py
# backend/main.py
from fastapi import FastAPI
from api.router import api_router

app = FastAPI()
app.include_router(api_router)
```

```ts
// backend/index.ts
import express from "express";
const app = express();
app.use("/api", require("./api/router"));
```

---

## ✅ AI Agent Must

- Only write inside `/backend`
- Use consistent structure for endpoints, logic, services
- Never store business logic in `/api` — use `/core` or `/services`
- Maintain `OpenAPI` docs inside `/docs/`
