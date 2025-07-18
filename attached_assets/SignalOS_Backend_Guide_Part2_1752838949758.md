
# 🔐 SignalOS Backend Guide – Part 2: Auth, Licensing, AI Parser, Worker Queue

---

## 🔐 Auth System (JWT + Device Binding)

### `/api/auth` endpoints

- `POST /login` → Return JWT + refresh
- `POST /register` → New user
- `POST /verify` → Validate token
- `POST /bind-device` → Save UUID/IP for hardware lock

📦 Store in: `/core/auth.py` or `/core/auth.ts`

---

## 🧾 License Engine

### Model Fields

```py
class License(Base):
    key: str
    user_id: UUID
    expires_at: datetime
    device_id: str
    active: bool
```

📌 Endpoints:

- `GET /license/status`
- `POST /license/activate`
- `POST /license/renew`

📦 Logic → `/core/license.py` + `/api/license.py`

---

## 🧠 AI Parser System

### Parsing Flow

```
text/image signal → /parser/parse
→ regex/NLP → LLM (offline/local) → confidence
→ return parsed JSON signal
```

📦 Modules:

- `/services/parser_ai.py` → LLM + fallback
- `/services/ocr.py` → EasyOCR / Tesseract
- `/core/parse.py` → Central controller

### User Feedback API

- `POST /parser/feedback`
- `POST /parser/train`

Stores feedback in `parser_feedback` table

---

## 🔄 Worker Queue (Retry + Background Tasks)

Use **Celery + Redis** (Python) or **BullMQ** (Node.js)

Tasks:

- `parse_worker`: run parsing async
- `retry_worker`: re-send failed MT5 trades
- `cleaner_worker`: delete expired sessions, logs

📦 Files:
- `/workers/parse_worker.py`
- `/workers/trade_retry.py`
