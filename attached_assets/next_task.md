📌 NEXT TASK – Replit Agent Build Guide (Auto Updated)
📅 Date: 2025-06-23

🧠 Task:
Implement the next Phase 5 module: `randomized_lot_inserter.py` for the Prop Firm Stealth system.

🔧 File to Create:
/desktop-app/randomized_lot_inserter.py

🧩 Description:
This module should randomly insert small dummy trades with varying lot sizes to obfuscate trading patterns from prop firm detection algorithms.

Capabilities:
- Generate random lot sizes within configurable ranges (e.g., 0.01-0.05)
- Insert dummy trades at random intervals (not correlated with real signals)
- Use different symbols from a rotation list to avoid pattern detection
- Automatically close dummy trades after random durations (30s-5min)
- Respect daily/weekly limits to avoid excessive trading
- Log all dummy trades separately from real strategy trades

🔁 System Integration:
- Integrates with MT5 bridge for trade execution
- Coordinates with main strategy to avoid interference
- Respects account balance and margin requirements
- Can be enabled/disabled per strategy or globally

🧪 Add Tests:
/desktop-app/tests/test_randomized_lot_inserter.py

Test Scenarios:
- Dummy trades generated within configured parameters
- No interference with real strategy trades
- Proper logging and tracking of dummy vs real trades
- Margin and balance validation before dummy trade execution

📂 Tracking:
Once complete:
- ✅ Update `feature_status.md`
- 🧾 Append to `execution_history.md`
- 📘 Log in `dev_changelog.md`

❗ Rules:
- Dummy trades must be clearly distinguishable from real trades in logs
- Never interfere with or delay real signal execution
- Respect prop firm trading rules and limits
