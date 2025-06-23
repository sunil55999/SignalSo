# 📌 NEXT TASK – Replit Agent Build Guide (Auto Updated per Phase)

📅 Date: 2025-06-23

🧠 Task:
Implement the `multi_tp_manager.py` module from **Phase 7: TP & SL Enhancements**.

🔧 File to Create:
`/desktop-app/multi_tp_manager.py`

🧩 Description:
Build an advanced take profit management system that supports up to 100 TP levels with partial closure functionality and dynamic SL shifting.

Key Features:

* Support for multiple TP levels (up to 100) per trade
* Partial position closure at each TP level
* Automatic SL shifting to break-even after first TP hit
* Volume distribution across TP levels
* Integration with existing ticket tracker and TP manager
* Real-time monitoring of TP level hits

🧪 Required Tests:
`/desktop-app/tests/test_multi_tp_manager.py`

* Test multiple TP level setup and monitoring
* Test partial closure at TP levels
* Test SL shifting to break-even
* Test volume distribution calculations

📂 Tracking Instructions:

* ✅ Update `/attached_assets/feature_status.md`
* 📘 Append log in `/attached_assets/dev_changelog.md`
* 🧾 Register task in `/attached_assets/execution_history.md`

❗ Rules:

* Use real-time price monitoring for TP level detection
* All logs must go to `/logs/multi_tp_manager.log`
* Ensure partial closures maintain proper lot size calculations
