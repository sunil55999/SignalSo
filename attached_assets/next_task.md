📌 NEXT TASK – Replit Agent Build Guide (Phase 10: Simulation + Symbol Mapping)

🧠 Dual Module Task:
You must now implement two essential modules to complete SignalOS’s dry-run sandbox and broker symbol compatibility layer.

---

### ✅ 1. `/desktop-app/signal_simulator.py` – Signal Dry-Run Execution

🎯 Purpose:
Allow users to preview signal execution logic (entry, SL/TP, lotsize) without sending real trades.

🧩 Features:
- Accept input: parsed signal + strategy config
- Simulate:
  - Entry selection
  - Lotsize calculation (invoke `lotsize_engine.py`)
  - SL/TP adjustment logic
- Return dry-run summary:
```python
{
  "entry": 1.1055,
  "sl": 1.1020,
  "tp": [1.1100, 1.1125],
  "lot": 0.12,
  "mode": "shadow",
  "valid": True
}
🧪 Test File:
/desktop-app/tests/test_signal_simulator.py

✅ Test:

Valid BUY signal → correct simulation

TP override from strategy

Shadow mode test (no SL shown)

Fallback if config missing

✅ 2. /desktop-app/symbol_mapper.py – Broker Symbol Normalizer
🎯 Purpose:
Map general signal symbols (e.g., “GOLD”, “GER30”) to broker-specific equivalents (e.g., “XAUUSD”, “DE40.cash”).

🧩 Features:

Load symbol map config (e.g., from /config/symbol_map.json)

Function:

python
Copy
Edit
normalize_symbol(input_symbol: str) → str
Support dynamic overrides (per user/account)

Case-insensitive mapping (e.g., “gold” → “XAUUSD”)

🧪 Test File:
/desktop-app/tests/test_symbol_mapper.py

✅ Test:

“GOLD” → “XAUUSD”

Unknown symbol returns input

User override map test

📂 After Completion (Both Modules):

✅ Mark complete in /attached_assets/feature_status.md

🧾 Append to /attached_assets/execution_history.md

📘 Log both changes in /attached_assets/dev_changelog.md

❗ Guidelines:

Do not call MT5 or send live trades in simulation

Store all dry-run previews in /logs/simulation.log (optional)

Make sure symbol_mapper.py is accessible from parser.py, retry_engine.py, and lotsize_engine.py
