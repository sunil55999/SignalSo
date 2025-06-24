# 🧠 FINAL UPGRADE PLAN – SignalOS Desktop App Completion

📅 Date: 2025-06-23

This plan outlines the **last 10–15% of features** required to bring SignalOS to full parity with TSC and beyond, focusing on smart trade logic, automation, and analytics. Each module below includes:

* Goal
* Module to create or upgrade
* Dependencies
* Integration notes
* Testing expectations

---

## ✅ 1. Entrypoint Management Enhancements

**🎯 Goal:** Allow flexible logic for signals with multiple entries.

🔧 File: `entrypoint_range_handler.py`

* Add logic for `average`, `best`, `second` entry selection
* Use current market price to determine "best"

📂 Integration:

* `parser.py`, `strategy_runtime.py`

🧪 Tests:

* Simulate 2–4 entries with all modes

---

## ✅ 2. Dynamic Lotsize Parser

**🎯 Goal:** Extract lotsize from message content or keywords.

🔧 File: `lotsize_engine.py`

* Add `get_lotsize_from_signal_text()`
* Use regex to find "0.2 lots", or phrases like “risk small”

📂 Integration:

* `parser.py`, `strategy_runtime.py`

🧪 Tests:

* Various text examples with embedded lots

---

## ✅ 3. Drawdown Management Engine

**🎯 Goal:** Kill trades that breach drawdown risk limits.

🔧 File: `drawdown_handler.py`

* Monitor equity vs balance
* Kill trades above risk % or provider-specific cap

📂 Integration:

* `risk_engine.py`, `copilot_alert_manager.py`

🧪 Tests:

* Simulate equity drop scenarios

---

## ✅ 4. Edit-On-Update Handler

**🎯 Goal:** Auto-edit open MT5 order if original signal is modified.

🔧 File: `edit_trade_on_signal_change.py`

* Detect change in SL/TP
* Edit live order with new parameters

📂 Integration:

* `parser.py`, `mt5_bridge.py`, `ticket_tracker.py`

🧪 Tests:

* Simulate SL/TP message edits

---

## ✅ 5. Advanced Take Profit Adjustments

**🎯 Goal:** Add spread to TP dynamically, allow override from signal.

🔧 File: `tp_adjustor.py`

* Read spread from MT5 terminal
* Add override if signal includes TP text

📂 Integration:

* `strategy_runtime.py`, `tp_manager.py`

🧪 Tests:

* Signal with override TP

---

## ✅ 6. Time-Based Automation

**🎯 Goal:** Support actions at fixed times daily.

🔧 File: `time_scheduler.py`

* Config to auto-close pending orders at X time
* Timezone support

📂 Integration:

* `copilot_command_interpreter.py`, `retry_engine.py`

🧪 Tests:

* Simulate time triggers

---

## ✅ 7. Signal Audit & Ticket Mapping

**🎯 Goal:** Link each trade to original signal, track status.

🔧 File: `ticket_tracker.py`

* Store trade ID → signal hash mapping
* Enable backtracking via audit log

📂 Integration:

* `mt5_bridge.py`, `strategy_runtime.py`, `analytics.py`

🧪 Tests:

* Verify trade-to-signal linkage

---

## ✅ 8. Provider Trust Scoring (AI-Ready)

**🎯 Goal:** Score providers based on SL hits, TP success, retry rate.

🔧 File: `provider_scorer.py`

* Score = function(confidence, RR win %, SL ratio, latency)
* Save in `provider_stats` table

📂 Integration:

* `analytics_pipeline.py`, `dashboard.vue`

🧪 Tests:

* Simulate 3 providers over 20 trades

---

## ✅ 9. Email Reporting System

**🎯 Goal:** Send daily/weekly summary to user/admin.

🔧 File: `email_reporter.ts`

* Use HTML template
* Include PnL, SL hit count, top providers

📂 Integration:

* Backend schedule or Copilot trigger

🧪 Tests:

* Fallback logging if email fails

---

## ✅ 10. Expand Analytics UI

**🎯 Goal:** Show peak profit/drawdown of each signal

🔧 Files:

* `/client/src/pages/SignalHistory.tsx`
* Add modal or expandable row with:

  * Peak profit
  * Max drawdown
  * Time-to-close

📂 Integration:

* `provider_stats`, `signal_tracker`

🧪 Tests:

* UI render, API fallback

---

# 🧩 Project Workflow

To ensure no regressions or overlap:

1. ➕ Add next task to `next_task.md`
2. ✅ Mark task complete in `feature_status.md`
3. 🧾 Log in `execution_history.md`
4. 📘 Document in `dev_changelog.md`


