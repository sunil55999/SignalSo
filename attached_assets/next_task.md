# 📌 NEXT TASK – Replit Agent Build Guide (Auto Updated per Phase)

📅 Date: 2025-06-23

🧠 Task:
Implement the `copilot_alert_manager.py` module from **Phase 10: Copilot & Command**.

🔧 File to Create:
`/desktop-app/copilot_alert_manager.py`

🧩 Description:
Build an alert management system that sends notifications via Telegram copilot bot for critical trading events and system status changes.

Key Features:

* Send alerts for drawdown limit breaches and margin warnings
* Notify about failed trades and MT5 connection issues
* Alert on prop firm risk triggers and emergency stops
* Configurable alert levels: info, warning, critical, emergency
* Rate limiting and alert throttling to prevent spam
* Alert templates with customizable formatting
* Integration with existing copilot bot and notification systems
* Alert history tracking and acknowledgment system

🧪 Required Tests:
`/desktop-app/tests/test_copilot_alert_manager.py`

* Test alert generation for different event types and severity levels
* Test rate limiting and throttling mechanisms
* Test integration with copilot bot notification system
* Test alert formatting and template rendering

📂 Tracking Instructions:

* ✅ Update `/attached_assets/feature_status.md`
* 📘 Append log in `/attached_assets/dev_changelog.md`
* 🧾 Register task in `/attached_assets/execution_history.md`

❗ Rules:

* Integrate with existing copilot_bot.py for message delivery
* Implement proper rate limiting to avoid Telegram API limits
* Provide clear alert categories and escalation levels
