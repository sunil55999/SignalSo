📌 NEXT TASK – Replit Agent Build Guide (Auto Updated)
📅 Date: 2025-06-23

🧠 Task:
Implement `randomized_lot_inserter.py` from Phase 5 – Prop Firm Stealth Systems.

🔧 File to Create:
/signalos/desktop-app/randomized_lot_inserter.py

🧩 Description:
Build a stealth utility that randomizes lot sizes slightly per trade to avoid detection by prop firm tracking systems.

Capabilities:
- Intercept trade before it is dispatched to MT5
- Modify lot size within a configurable variance range (e.g., ±0.003)
- Prevent identical repeated lot sizes across sessions
- Support optional rounding behavior (e.g., round to 0.01)
- Configurable on a per-user or per-strategy basis

🔁 System Integration:
- Hook into strategy runtime before trade execution
- Pull variance config from synced user profile or JSON
- Log applied randomization and final lot size
- Send log to Copilot Bot (optional toggle)

🧪 Add Tests:
/signalos/desktop-app/tests/test_randomized_lot_inserter.py

Test Scenarios:
- Trade with default lot 0.10 → randomized to 0.102 / 0.098
- Config range set to ±0.005 → respects bounds
- Edge case: rounding enabled
- Consistency check: same signal doesn't repeat lot size exactly

📂 Tracking:
Once complete:
- ✅ Update `feature_status.md`
- 🧾 Append to `execution_history.md`
- 📘 Log in `dev_changelog.md`

❗ Rules:
- DO NOT use hardcoded randomness — always make it seedable/testable
- DO NOT override user-configured lot if override is disabled
- Ensure changes are reflected in MT5 dispatch but logged securely
