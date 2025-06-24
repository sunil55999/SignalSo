📌 NEXT TASK – Replit Agent Build Guide (Phase 8: Lotsize + Entry)
📅 Date: 2025-06-24

🧠 Task:
Implement `lotsize_engine.py` to support advanced position sizing logic based on signal content or user configuration.

🔧 File to Create:
`/desktop-app/lotsize_engine.py`

🧩 Description:
This module will calculate trade lotsize from:
- Signal message (e.g., “Risk 2%” or “Use 0.5 lots”)
- Strategy rules (e.g., per pair, pip-value-based sizing)
- Global config fallback (e.g., fixed risk %, default lot)

Must Support:
- `fixed_lot`
- `risk_percent` (e.g., 1% of balance)
- `fixed_cash` (e.g., $10 per trade)
- `pip_value` sizing (e.g., $1 per pip)
- Text override (e.g., HIGH RISK = 2x default)

✅ Inputs:
- Signal content
- Risk config (per user or global)
- MT5 account balance

✅ Outputs:
- Normalized float lot size (e.g., `0.2`)

🧪 Test File:
`/desktop-app/tests/test_lotsize_engine.py`

Test Scenarios:
- “0.1 lots” in signal message
- “Risk 2%” + $1,000 account
- HIGH RISK → adjusted multiplier
- Fallback to config default

📂 Update After Completion:
- `attached_assets/feature_status.md`
- `attached_assets/dev_changelog.md`
- `attached_assets/execution_history.md`

❗ Rules:
- Use safe bounds (0.01 to 5.0 lots)
- Ensure test passes all risk mode combinations
- Do not hardcode account values
