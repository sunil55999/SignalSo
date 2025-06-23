# 📌 NEXT TASK – Replit Agent Build Guide (Auto Updated per Phase)

📅 Date: 2025-06-23

🧠 Task:
Implement the `margin_level_checker.py` module from **Phase 8: Risk & Filter Logic**.

🔧 File to Create:
`/desktop-app/margin_level_checker.py`

🧩 Description:
Develop a margin level monitoring system that prevents new trades when account margin falls below safe thresholds.

Key Features:

* Monitor MT5 account margin level in real-time
* Configurable margin level thresholds (warning and blocking levels)
* Block new trades when margin drops below minimum safe level
* Send alerts when margin approaches danger zones
* Integration with strategy runtime for pre-trade validation
* Historical margin tracking for analysis

🧪 Required Tests:
`/desktop-app/tests/test_margin_level_checker.py`

* Test margin level calculations and thresholds
* Test trade blocking at different margin levels
* Simulate low margin scenarios

📂 Tracking Instructions:

* ✅ Update `/attached_assets/feature_status.md`
* 📘 Append log in `/attached_assets/dev_changelog.md`
* 🧾 Register task in `/attached_assets/execution_history.md`

❗ Rules:

* Use mock MT5 account data for testing
* All logs must go to `/logs/risk_management.log`
* Prioritize account safety over trade execution
