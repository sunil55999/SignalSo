📌 NEXT TASK – Replit Agent Build Guide (Auto Updated)
📅 Date: 2025-06-23

🧠 Task:
Implement `edit_trade_on_signal_change.py` from Phase 2 – Advanced Order Management.

🔧 File to Create:
/signalos/desktop-app/edit_trade_on_signal_change.py

🧩 Description:
Build logic that detects when a Telegram signal message is edited and automatically adjusts the open order accordingly.

Requirements:
- Detect message edits from the parser system
- Compare entry/SL/TP values to existing trade
- Modify MT5 order if needed (without reopening)
- Log changes to the order: what changed and why

🔁 System Impact:
- Updates runtime strategy logic
- Connects to parser edit event listener
- Updates open trade via MT5 bridge
- Logs all trade modifications for auditing

🧪 Add Tests:
/signalos/desktop-app/tests/test_edit_trade_on_signal_change.py
Test Cases:
- Trade updated due to TP change
- SL changed after signal edit
- No change detected → no action taken
- Edge case: signal changed after trade closed

📂 Tracking:
Once complete:
- Update feature_status.md
- Log in execution_history.md
- Add changelog entry to dev_changelog.md

❗ Rules:
DO NOT continue to next module until this is ✅ done.
DO NOT reimplement existing files.
DO NOT create files outside allowed folders.
