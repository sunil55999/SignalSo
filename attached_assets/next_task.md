📌 NEXT TASK – Replit Agent Build Guide (Phase 8: Lotsize + Entry)
🧠 Task:
Create the `lotsize_engine.py` module to support multiple lot size calculation strategies used by different user configurations and signals.

🔧 File to Create:
`/desktop-app/lotsize_engine.py`

🧩 Description:
This engine should compute the correct lot size for each trade based on strategy settings, signal context, and user risk profile.

✅ Required Modes:
1. Fixed Lot (e.g., always 0.05)
2. Risk Percent (e.g., 1% of account balance)
3. Fixed Cash Amount (e.g., $10 per trade)
4. Pip Value-Based Lot (e.g., $1 per pip on GOLD, US30)
5. Signal-Driven Multiplier (e.g., if “HIGH RISK” → apply 2x multiplier)

🧠 Required Input:
```python
calculate_lot(
  strategy_config: dict,
  signal_data: dict,
  account_balance: float,
  sl_pips: float,
  symbol: str
) → float
🎯 Output:

Returns float representing the final computed lot size (e.g., 0.12)

📚 Strategy Config Inputs:

mode: "fixed" | "risk_percent" | "cash_per_trade" | "pip_value" | "text_override"

base_risk: float

override_keywords: [“HIGH RISK”, “LOW RISK”, etc.]

🧱 Additional Module to Scaffold:
Create /desktop-app/pip_value_calculator.py to:

Provide pip values per symbol (e.g., GOLD = $10/pip, US30 = $1/pip)

Return pip value dynamically based on symbol input

Can later support broker-specific values

Example usage:

python
Copy
Edit
get_pip_value("XAUUSD") → 10.0
get_pip_value("US30") → 1.0
🧪 Required Test File:
/desktop-app/tests/test_lotsize_engine.py

Test Scenarios:

1% risk of $1000 account, SL 50 pips

Fixed $10 trade with pip value $1

Text contains “HIGH RISK” → double lot

Missing SL: fallback behavior

Symbol-specific pip valuation

📦 Integrations:

Used in: strategy_runtime.py, retry_engine.py, parser.py

May receive pip values from pip_value_calculator.py

Final lots sent to mt5_bridge.py

📂 After Completion:

✅ Mark complete in /attached_assets/feature_status.md

🧾 Log in /attached_assets/execution_history.md

📘 Update /attached_assets/dev_changelog.md

❗ Implementation Guidelines:

Safe output bounds: 0.01 ≤ lot ≤ 5.00

Must log warnings if pip value or SL is missing

Allow fallback to config-defined fixed lot if error occurs