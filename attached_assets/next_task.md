# 📌 NEXT TASK – Replit Agent Build Guide (Auto Updated per Phase)

📅 Date: 2025-06-24

🧠 Task:
Implement `signal_success_tracker.ts` from **Phase 11: Analytics + UI**.

🔧 File to Create:
`/client/src/utils/signal_success_tracker.ts`

🧩 Description:
Develop a utility module to track and analyze signal parsing success rates and execution performance. This creates a feedback loop for parser improvement and provides analytics on signal quality.

Key Features:

* Track TP/SL hit rates by signal format and provider
* Monitor parsing confidence vs actual trade outcomes
* Store success metrics with time-based aggregation (daily, weekly, monthly)
* Generate performance reports for parser optimization
* Integration with existing analytics dashboard
* Export functionality for external analysis

🧪 Required Tests:
`/client/src/tests/signal_success_tracker.test.ts`

* Test success rate calculations for different time periods
* Validate signal format pattern recognition
* Test data aggregation and reporting functions
* Verify integration with analytics components

📂 Tracking Instructions:

* ✅ Update `/attached_assets/feature_status.md`
* 📘 Append log in `/attached_assets/dev_changelog.md`
* 🧾 Register task in `/attached_assets/execution_history.md`

❗ Rules:

* Must integrate with existing parser confidence scoring
* Store data efficiently for large datasets
* Provide real-time and historical analytics
* Support filtering by provider, symbol, and time range
