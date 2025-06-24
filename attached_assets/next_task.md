# 📌 NEXT TASK – Replit Agent Build Guide (Auto Updated per Phase)

📅 Date: 2025-06-23

🧠 Task:
Implement `signal_success_tracker.ts` from **Phase 11: Analytics + UI**.

🔧 File to Create:
`/client/src/utils/signal_success_tracker.ts`

🧩 Description:
Build a tracking utility that analyzes the success rate of signals from providers based on execution results, RR targets hit, and SL trigger history.

Key Features:

* Accept signal execution logs (via API or client data cache)
* Aggregate stats by provider: win rate %, average RR, max drawdown, signal count
* Cache results in local storage or query live from backend
* Provide easy method: `getSuccessStats(providerId: string)`
* UI-ready format output for rendering in dashboards

🧪 Required Tests:
`/client/src/tests/signal_success_tracker.test.ts`

* Validate correct win rate calculation
* Confirm proper RR average aggregation
* Simulate edge cases: 0 trades, mixed win/losses, extreme drawdowns

📂 Tracking Instructions:

* ✅ Update `/attached_assets/feature_status.md`
* 📘 Append log in `/attached_assets/dev_changelog.md`
* 🧾 Register task in `/attached_assets/execution_history.md`

❗ Rules:

* Should not require full re-fetch for each view
* Use memoized selectors or localStorage where applicable
* Ensure API fallback if local data is missing
