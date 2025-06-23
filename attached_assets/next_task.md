📌 NEXT TASK – Replit Agent Build Guide (Auto Updated)
📅 Date: 2025-06-23

🧠 Task:
Implement `signal_conflict_resolver.py` from Phase 3 – Risk Controls.

🔧 File to Create:
/desktop-app/signal_conflict_resolver.py

🧩 Description:
Build a desktop module to detect and resolve conflicting signals from different providers.

Requirements:
- Detect when multiple providers send opposing signals for same pair
- If conflict detected:
  - ✅ Pause trade execution for conflicting pair
  - ✅ Log conflict details (providers, signals, timestamps)
  - ✅ Optionally, execute strongest signal based on confidence
- Admins can configure conflict resolution strategies
- Support provider priority weighting
- Auto-resume after conflict resolution window expires

🔁 System Impact:
- Integrates with signal parser and strategy runtime
- Depends on provider confidence scoring system
- Affects trade execution flow and provider statistics
- Linked to Telegram bot notification system

🧪 Add Tests:
/desktop-app/tests/test_signal_conflict_resolver.py

Test Scenarios:
- Detect BUY vs SELL conflict → pause execution
- Priority-based resolution → execute higher priority
- Time window expiry → auto-resume normal flow
- Multiple pair conflict handling

📂 Tracking:
Once complete:
- ✅ Update `feature_status.md`
- 🧾 Log in `execution_history.md`
- 📘 Append changelog in `dev_changelog.md`

❗ Rules:
- DO NOT hardcode provider priorities — pull from config
- DO NOT block all trading, only conflicting pairs
- DO NOT ignore low-confidence signals without evaluation
