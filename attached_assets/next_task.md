# 📌 NEXT TASK – Replit Agent Build Guide (Auto Updated per Phase)

📅 Date: 2025-06-23

🧠 Task:
Implement `email_reporter.ts` from **Phase 12: Infrastructure**.

🔧 File to Create:
`/server/utils/email_reporter.ts`

🧩 Description:
Build a backend utility to send daily/weekly email reports summarizing:

* Total trades executed
* Win rate and average RR
* Top performing providers
* Errors or blocked signals

Key Features:

* Support SMTP or API-based email sending (SendGrid, Mailgun, etc.)
* HTML and plain text email format
* Read data from PostgreSQL or API endpoints
* Schedule via cron job or manual trigger
* Configurable per user or admin scope

🧪 Required Tests:
`/server/tests/email_reporter.test.ts`

* Test successful email formatting and delivery
* Handle SMTP/API failures gracefully
* Ensure template loads dynamic stats properly

📂 Tracking Instructions:

* ✅ Update `/attached_assets/feature_status.md`
* 📘 Append log in `/attached_assets/dev_changelog.md`
* 🧾 Register task in `/attached_assets/execution_history.md`

❗ Rules:

* Use server-side only, do not expose secrets in frontend
* Place templates in `/server/templates/` as `.html`
* Log success/failure of reports in `/logs/email_reports.log`
