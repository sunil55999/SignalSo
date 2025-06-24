# 📌 NEXT TASK – Replit Agent Build Guide (Auto Updated per Phase)

📅 Date: 2025-06-23

🧠 Task:
Implement `AnalyticsProviderTable.tsx` from **Phase 11: Analytics + UI**.

🔧 File to Create:
`/client/src/components/analytics/AnalyticsProviderTable.tsx`

🧩 Description:
Build a UI table component that displays performance stats for all signal providers in a sortable and filterable format.

Key Features:

* Fetch provider stats from `/server/routes.ts` (API endpoint: `/api/providers/stats`)
* Columns:

  * Provider Name
  * Total Signals
  * Win Rate %
  * Avg RR
  * Max Drawdown
  * Last Signal Date
* Table features:

  * Column sorting (asc/desc)
  * Row filtering by win rate or symbol
  * Export to CSV
  * Highlight top performers

🧪 Required Tests:
Use mock data in `/client/src/tests/mocks/provider_stats.json`

* Validate column sorting logic
* Check conditional rendering (e.g. highlight win rate > 75%)
* Test mobile responsiveness and hover states

📂 Tracking Instructions:

* ✅ Update `/attached_assets/feature_status.md`
* 📘 Append log in `/attached_assets/dev_changelog.md`
* 🧾 Register task in `/attached_assets/execution_history.md`

❗ Rules:

* Use `shadcn/ui` table components
* Keep styling consistent with SignalHistory.vue and ProviderCompare.tsx
* Ensure accessibility and keyboard navigation support
