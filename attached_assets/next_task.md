# 📌 NEXT TASK – Replit Agent Build Guide (Final Upgrade Phase)

📅 Date: 2025-06-23

🧠 Task:
Upgrade `entrypoint_range_handler.py` to support advanced entrypoint resolution logic.

🔧 File to Upgrade:
`/desktop-app/entrypoint_range_handler.py`

🧩 Description:
Support multi-entry logic from a signal. Add entry mode evaluation:

* `average`: Mean of all entries
* `best`: Closest to market price
* `second`: Second entrypoint from list

Key Features:

* Accept list of entry prices from parser
* New method:

```python
resolve_entry(entry_list: List[float], mode: str, current_price: float) -> float
```

* Fallback to first entry if list invalid

📂 Integration:

* `strategy_runtime.py`
* `parser.py`

🧪 Required Tests:
`/desktop-app/tests/test_entrypoint_range_handler.py`

* Validate correct resolution per mode
* Test with invalid or single-entry signals
* Confirm correct fallback behavior

📁 Tracking:

* ✅ Update `feature_status.md`
* 🧾 Append to `execution_history.md`
* 📘 Log to `dev_changelog.md`

❗ Rules:

* Log fallback/invalid mode to `/logs/trade_errors.log`
* Support float precision to 5 decimals
* Must not break current single-entry logic
