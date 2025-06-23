# 📈 SignalOS Upgrade Plan – Full Feature Completion Roadmap

> Goal: Reach full feature parity with top-tier Telegram Signal Copiers (e.g., TSC) while maintaining SignalOS's unique advantages (AI parser, Copilot Bot, strategy builder).

---

## 📦 Phase 6: Advanced Order Management & Commands

### ✅ Already Implemented:

* Market Orders
* Partial Close
* Break-even logic

### 🔧 To Be Implemented:

#### 1. `smart_entry_mode.py`

* Waits for better price within X pips/spread before triggering execution
* Detects optimal entry using MT5 orderbook data or simulated delay

#### 2. `trigger_pending_order.py`

* Execute pending orders when market hits entry price (for LIMIT/STOP)
* Add config for retry + slippage tolerance

#### 3. `edit_trade_on_signal_change.py` (Already done, extend)

* Improve SL/TP re-entry on edited messages
* Add audit history tagging for edits

#### 4. `ticket_tracker.py`

* Link each trade to signal ticket
* Use MT5 order ID + internal hash

---

## 💰 Phase 7: TP/SL Enhancements

#### 1. `multi_tp_manager.py`

* Support up to 100 TP levels
* Move SL to Entry, TP1, TP2, etc.
* Handle overlap: SL to Entry when TP1 hit

#### 2. `tp_sl_adjustor.py`

* Add pips to SL/TP (manual buffer)
* Spread-based correction logic

#### 3. `rr_target_adjustor.py`

* Set TP/SL based on fixed R\:R values (1:2, 1:3)
* Integration with visual builder

---

## 🔐 Phase 8: Risk & Filter Logic

#### 1. `news_filter.py`

* Block trades during red news events
* Integrate with forex calendar API (Forexfactory or MyFxBook)

#### 2. `signal_limit_enforcer.py`

* Max signals per pair/channel/time window
* Strategy override for whitelisted pairs

#### 3. `margin_level_checker.py`

* Real-time margin % check before trade
* User config: minimum margin threshold (5%, 10%, etc.)

#### 4. `spread_checker.py`

* Block trade if spread exceeds user threshold
* Log Copilot Bot warning if blocked

---

## 🧠 Phase 9: Strategy & Behavior Modules

#### 1. `reverse_strategy.py`

* Reverse signal direction (BUY → SELL)
* Configurable per provider or pair

#### 2. `grid_strategy.py`

* Place grid orders at X pip intervals
* Set limit on grid size and risk caps

#### 3. `multi_signal_handler.py`

* Parse messages with 2–5 signals
* Execute all signals or select based on priority

#### 4. `strategy_condition_router.py`

* Route signal through different strategy logic depending on:

  * Symbol
  * Provider
  * Confidence Score

---

## 📊 Phase 10: Analytics + Visualization

#### 1. `provider_compare.vue`

* Display profit, drawdown, execution speed side-by-side
* Add badges for reliability, average RR

#### 2. `pair_mapper.ts`

* GOLD → XAUUSD, BTC → BTCUSD mapping UI
* Configurable for each user or terminal

#### 3. `signal_success_tracker.ts`

* Logs SL/TP success rate by signal format
* Feedback loop to parser improvement

---

## 🤖 Phase 11: Copilot Intelligence Expansion

#### 1. `copilot_command_interpreter.py`

* Natural language → signal commands
* E.g., "Pause GBP signals", "Replay last Gold signal"

#### 2. `copilot_alert_manager.py`

* Telegram alerts for:

  * Low margin
  * Failed trade
  * Drawdown limit breached
  * Prop firm risk triggered

---

## 🔁 Testing & Infrastructure

#### 1. Unit Tests

* Add test suite for every new `.py` in `/desktop-app/tests/`

#### 2. `feature_status.md`

* Must be updated after each module

#### 3. `execution_history.md`

* Summary of all builds (timestamped)

#### 4. `dev_changelog.md`

* Dev-facing notes + progress tracking

#### 5. `next_task.md`

* Auto-updated pointer to guide Replit Agent

---

## 🧠 Required Prompts and Protocols

#### `replit_master_prompt.md`

* Rules, scopes, directory protections

#### `replit_task_protocol.md`

* Enforce: no skipping, one module per phase, structured logging

#### `dev_guidelines.md`

* How to write modules, track status, and rollback

---

✅ Once all of the above are complete, SignalOS will:

* Match or exceed TSC in features
* Offer best-in-class AI parsing
* Be prop firm friendly by default
* Be fully auditable, scalable, and user-friendly
