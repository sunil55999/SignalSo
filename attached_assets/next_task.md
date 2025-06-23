📌 NEXT TASK – Replit Agent Build Guide (Auto Updated)
📅 Date: 2025-06-23

🧠 Task:
Implement `equity_limits.ts` from Phase 3 – Risk Controls.

🔧 File to Create:
/signalos/server/routes/equity_limits.ts

🧩 Description:
Create a server-side route and logic to enforce equity-based risk rules.

Requirements:
- Define max % gain or loss allowed per day
- On trigger: automatically send shutdown command to all terminals
- Store per-user equity thresholds in DB (linked to account)
- Endpoint: `POST /equity-limit/check`
- Auto-reset next day or via admin override
- Log trip reason: user, equity %, triggered action

🔁 System Impact:
- Tied to real-time profit/loss monitoring
- Enforced on server-side, not user-configurable from frontend
- Dashboard will later query status (active/inactive)
- Will dispatch notification to Telegram bot when triggered

🧪 Add Tests:
/signalos/server/tests/test_equity_limits.ts

Test Coverage:
- Threshold crossed → block new trades
- Threshold not reached → allow
- Manual reset by admin API
- Logging of reason and user context

📂 Tracking:
Once complete:
- ✅ Update `feature_status.md`
- 🧾 Log in `execution_history.md`
- 📘 Append changelog in `dev_changelog.md`

❗ Rules:
- DO NOT write frontend for this in this task
- DO NOT override user limits in DB directly
- Do NOT proceed to drawdown module until this is ✅ complete
