# 📌 NEXT TASK – Replit Agent Build Guide (Auto Updated per Phase)

📅 Date: 2025-06-23

🧠 Task:
Implement the `copilot_command_interpreter.py` module from **Phase 10: Copilot & Command**.

🔧 File to Create:
`/desktop-app/copilot_command_interpreter.py`

🧩 Description:
Build a natural language command interpreter that converts Telegram bot commands into signal operations and strategy management actions.

Key Features:

* Parse natural language commands from Telegram copilot bot
* Convert text to structured commands (pause, resume, adjust, replay)
* Support signal management: "Pause GBP signals", "Resume GOLD trades"  
* Strategy adjustments: "Set EURUSD lot to 0.05", "Enable reverse mode"
* Signal replay: "Replay last Gold signal", "Re-execute GBPUSD from 10am"
* Integration with existing strategy modules and signal processing
* Command validation and confirmation before execution
* Comprehensive logging and audit trail

🧪 Required Tests:
`/desktop-app/tests/test_copilot_command_interpreter.py`

* Test command parsing for different natural language inputs
* Test strategy adjustment commands and validation
* Test signal management operations (pause/resume)
* Test integration with strategy modules and error handling

📂 Tracking Instructions:

* ✅ Update `/attached_assets/feature_status.md`
* 📘 Append log in `/attached_assets/dev_changelog.md`
* 🧾 Register task in `/attached_assets/execution_history.md`

❗ Rules:

* Commands must be validated before execution
* Provide clear feedback on command interpretation
* Integrate with existing copilot_bot.py for seamless operation
