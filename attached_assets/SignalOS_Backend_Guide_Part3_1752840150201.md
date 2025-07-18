
# 📈 SignalOS Backend Guide – Part 3: Trade Execution, Analytics, Scaling

---

## 🧭 Trade Router (MT4/MT5)

### `/api/trades`

- `POST /open` → with symbol, sl, tp, risk
- `POST /close`
- `GET /status`

📦 Logic → `/core/trade.py`
📦 Service → `/services/mt5_bridge.py` (socket or file-based connector)

Example MT5 payload:

```json
{
  "symbol": "XAUUSD",
  "type": "SELL",
  "lot": 1.0,
  "sl": 1962.0,
  "tp": [1958.0, 1955.0]
}
```

---

## 📊 Analytics System

### `/api/analytics`

- `GET /summary` → PnL, WinRate, DD, Latency
- `GET /report/pdf` → Export reports
- `GET /provider/:id` → Signals by provider

📦 Logic → `/core/analytics.py`
📦 Report Builder → `/services/report_pdf.py`

---

## 🔐 Security & Monitoring

- Middleware: `/middleware/auth.py`, `/middleware/rate_limit.py`
- Logs in `/logs/*` (auth.log, trade.log, parser.log)
- `/status` and `/healthz` endpoints

---

## 🧠 AI Agent Dev Checklist

- [ ] Full coverage test for `/api/*`
- [ ] License + Auth + Parser logic in `/core/`
- [ ] Logging and retry support for MT5 connector
- [ ] Unit test coverage in `/tests/`
- [ ] Queue-based retry for parsing/trade

## 🔮 Future Phase Prep

- `/api/marketplace` → strategy/plugin store
- `/webhook/*` → event push to Discord/Slack/Telegram
- Offline mode parser with sync queue

📦 Place all future prep logic in `/core/future/`
