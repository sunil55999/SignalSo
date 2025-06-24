# 📌 NEXT TASK – Replit Agent Build Guide (Auto Updated per Phase)

📅 Date: 2025-06-24

🧠 Task:
Implement the `EmailReporter.ts` module from **Phase 11: Analytics + UI**.

🔧 File to Create:
`/server/EmailReporter.ts`

🧩 Description:
Build an email reporting system that generates and sends automated performance reports, trade summaries, and analytics to users on a scheduled basis.

Key Features:

* Generate daily, weekly, and monthly performance reports with key metrics
* Send trade execution summaries with profit/loss breakdowns
* Provider performance comparison reports via email
* Customizable email templates with HTML formatting
* Scheduled email delivery using cron jobs or similar scheduling
* User preferences for email frequency and report types
* Integration with existing provider stats and trade data
* Email queue management with retry logic for failed deliveries

🧪 Required Tests:
`/server/tests/EmailReporter.test.ts`

* Test email template generation with different report types
* Test scheduling functionality and delivery queue management
* Test user preference handling and customization options
* Test error handling and retry logic for failed email deliveries

📂 Tracking Instructions:

* ✅ Update `/attached_assets/feature_status.md`
* 📘 Append log in `/attached_assets/dev_changelog.md`
* 🧾 Register task in `/attached_assets/execution_history.md`

❗ Rules:

* Use a reliable email service (SendGrid, SES, or similar)
* Implement proper error handling and logging
* Ensure email templates are responsive and professional
