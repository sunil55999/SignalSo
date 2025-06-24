# 📌 NEXT TASK – Replit Agent Build Guide (Auto Updated per Phase)

📅 Date: 2025-06-23

🧠 Task:
Implement the `ProviderCompare.tsx` component from **Phase 11: Analytics + UI**.

🔧 File to Create:
`/client/src/components/ProviderCompare.tsx`

🧩 Description:
Build a React component that displays side-by-side comparison of signal provider performance metrics for analytics dashboard.

Key Features:

* Display provider performance metrics in comparison table format
* Show profit/loss, win rate, average R:R, drawdown, and execution speed
* Interactive sorting and filtering by performance criteria
* Visual charts for performance trends and comparison graphs
* Provider reliability badges and rating system
* Export functionality for performance reports
* Integration with existing dashboard layout and theme system
* Real-time data updates via WebSocket or polling

🧪 Required Tests:
`/client/src/components/__tests__/ProviderCompare.test.tsx`

* Test component rendering with mock provider data
* Test sorting and filtering functionality
* Test chart interactions and data visualization
* Test responsive layout and accessibility features

📂 Tracking Instructions:

* ✅ Update `/attached_assets/feature_status.md`
* 📘 Append log in `/attached_assets/dev_changelog.md`
* 🧾 Register task in `/attached_assets/execution_history.md`

❗ Rules:

* Follow existing UI component patterns and styling
* Ensure responsive design for mobile and desktop
* Use TypeScript with proper type definitions for all props and data
