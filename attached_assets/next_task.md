📌 NEXT TASK – Replit Agent Build Guide (Auto Updated)
📅 Date: 2025-06-23

🧠 Task:
Implement `drawdown_handler.ts` from Phase 3 – Risk Controls.

🔧 File to Create:
/signalos/server/routes/drawdown_handler.ts

🧩 Description:
Build a backend module to enforce drawdown limits per account, per provider, and per group of trades.

Requirements:
- Monitor live drawdown as % of current balance
- If threshold is hit:
  - ✅ Close all open trades for user
  - ✅ Optionally, close only trades from a flagged provider
  - ✅ Optionally, close trades by pair or session tag
- Admins can configure drawdown rules per user or provider
- Log trigger reason, trade list closed, % drawdown
- Auto-disable trade reception for flagged providers until reset

🔁 System Impact:
- Integrates with MT5 command executor and user database
- Depends on real-time P&L tracking from MT5 bridge
- Affects user strategy engine (can trigger shutdowns)
- Linked to Telegram bot notification system

🧪 Add Tests:
/signalos/server/tests/test_drawdown_handler.ts

Test Scenarios:
- Trigger global drawdown → all trades closed
- Trigger provider drawdown only
- Ignore threshold when trades already closed
- Admin reset / restart of trading after trigger

📂 Tracking:
Once complete:
- ✅ Update `feature_status.md`
- 🧾 Log in `execution_history.md`
- 📘 Append changelog in `dev_changelog.md`

❗ Rules:
- DO NOT hardcode thresholds — pull from DB
- DO NOT mix this with equity_limits.ts logic
- DO NOT send duplicate close commands to MT5
