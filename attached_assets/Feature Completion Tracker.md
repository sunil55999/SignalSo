# ✅ MISSING FEATURE TRACKER – SignalOS Completion Phase

📅 Date: 2025-06-23

This document tracks **incomplete or unimplemented features** still required to reach full parity with commercial copiers like TSC.

---

## 🧩 Entrypoint Management

* [ ] Pick **average entrypoint** from multiple (range)
* [ ] Pick **best/second entrypoint** based on proximity
* [ ] Handle **two-entry signals** with staged logic

📂 Module: `entrypoint_range_handler.py`

---

## 🧠 Lotsize Management

* [ ] Parse **lotsize from signal message** text (e.g., "0.3 lots")
* [ ] Allow **per-pair lotsize configuration** (symbol override)
* [ ] Change lotsize based on **signal content/keywords** (e.g., “HIGH RISK”)

📂 Module: `lotsize_engine.py`, `parser.py`

---

## 📈 Advanced TP / SL Logic

* [ ] Support **TP override via signal**
* [ ] Add **spread to TP automatically**
* [ ] Allow **R\:R-based TP generation** in real-time

📂 Module: `tp_adjustor.py`, `rr_converter.py`

---

## 📉 Drawdown Guardian

* [ ] Close all trades if **account drawdown** breaches %
* [ ] Close all trades from **a provider** if they cause drawdown
* [ ] Block new signals while in drawdown

📂 Module: `drawdown_handler.py`

---

## 🕒 Time-based Automation

* [ ] Auto-close **pending orders at a fixed time**
* [ ] Configure **time window per pair/provider**

📂 Module: `time_scheduler.py`, `time_window_block`

---

## 🧾 Ticket & Signal Tracking

* [ ] Auto-edit trades when **signal is updated** (TP/SL)
* [ ] Track trade ID ↔ signal link in logs

📂 Module: `ticket_tracker.py`, `edit_trade_on_signal_change.py`

---

## 📊 UI + Analytics

* [ ] Show **peak profit/drawdown** of each signal
* [ ] Add **Signal History Modal** with trade lifecycle
* [ ] Implement **Provider Trust Score** system

📂 Files: `AnalyticsProviderTable.tsx`, `SignalHistory.vue`, `provider_scorer.py`

---

## 📬 Notifications + Reporting

* [ ] Implement `email_reporter.ts` for weekly/daily reports
* [ ] Add fallback/alert logs for failed messages

📂 Files: `email_reporter.ts`, `copilot_alert_manager.py`

---

# ✅ Completion Rules

Each item above must:

* Be implemented & tested
* Have ✅ in `feature_status.md`
* Have log in `execution_history.md`
* Have a record in `dev_changelog.md`

Once all items are ✅: SignalOS is fully production ready.
