📌 NEXT TASK – Replit Agent Build Guide (Auto Updated)
📅 Date: 2025-06-23

🧠 Task:
Implement `ticket_tracker.py` from Phase 2 – Advanced Order Management.

🔧 File to Create:
/signalos/desktop-app/ticket_tracker.py

🧩 Description:
Develop a system to track MT5 trade tickets and link them to their originating signal messages or providers.

Required Capabilities:
- Store ticket number, signal hash, and provider ID
- Map each open order to its originating message
- Match trade update commands (e.g., CLOSE, MODIFY) to correct MT5 ticket
- Integrate with the runtime and Copilot Bot
- Enable Telegram bot to respond with “Trade #123456 = GBPUSD from @GoldSignals”

🔁 System Impact:
- Adds trade-ticket mapping to trade log layer
- Updates runtime context with ticket tracking logic
- Required by partial close and edit systems

🧪 Add Tests:
/signalos/desktop-app/tests/test_ticket_tracker.py

Test Coverage:
- Ticket saved on trade open
- Ticket correctly linked to signal
- Ticket lookup from command context
- Edge: same provider, two signals with similar SL/TP

📂 Tracking:
Once complete:
- ✅ Update `feature_status.md`
- 🧾 Append to `execution_history.md`
- 📘 Log to `dev_changelog.md`

❗ Rules:
- Do NOT skip ahead
- Do NOT duplicate existing logic
- Work only inside `/desktop-app/` and `/shared/` if needed
