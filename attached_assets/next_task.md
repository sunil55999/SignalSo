📌 NEXT TASK – Replit Agent Build Guide (Auto Updated)
📅 Date: 2025-06-23

🧠 Task:
Implement `end_of_week_sl_remover.py` from Phase 5 – Prop Firm Stealth Features.

🔧 File to Create:
/signalos/desktop-app/end_of_week_sl_remover.py

🧩 Description:
This module will remove or adjust stop-losses before the market closes on Fridays, to prevent SL spikes or broker flagging.

Key Features:
- Check if current time is near market close (Friday 15:30–16:59 UTC)
- Option to:
  - Remove SL completely
  - Move SL far enough to avoid accidental hit
  - Skip affected trades (configurable)
- Configurable in strategy settings:
  - Mode: `remove`, `widen`, or `ignore`
  - Pairs to exclude (e.g., crypto)
  - Prop firm mode on/off
- Log all actions with timestamp and reason

🔁 System Integration:
- Hook into strategy runtime OR post-trade validator
- Works with MT5 bridge to update trade SL before close
- Compatible with stealth SL masking logic
- Can notify Copilot Bot of changes (optional)

🧪 Add Tests:
/signalos/desktop-app/tests/test_end_of_week_sl_remover.py

Test Cases:
- SL removed before Friday close
- SL widened (moved 300 pips away)
- Time-based activation (only triggers on Friday UTC)
- Edge: trade with no SL – skip or log

📂 Tracking:
Once complete:
- ✅ Update `feature_status.md`
- 🧾 Append to `execution_history.md`
- 📘 Log in `dev_changelog.md`

❗ Rules:
- DO NOT apply outside Friday close window
- DO NOT modify SL if strategy config disables it
- DO NOT leak SL adjustment in MT5 comment/log
