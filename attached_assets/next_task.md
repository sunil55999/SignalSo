📌 NEXT TASK – Replit Agent Build Guide (Auto Updated)
📅 Date: 2025-06-23

🧠 Task:
Implement the `margin_filter block` for the Strategy Builder in Phase 4.

🔧 File to Modify:
/client/src/components/StrategyBlocks/MarginFilterBlock.tsx  
(You may create this if it doesn’t exist yet)

🧩 Description:
Create a visual block that filters signals based on current free margin % or absolute margin value.

Capabilities:
- Allow user to set margin % threshold (e.g. “Only trade if margin > 25%”)
- Block signals if margin check fails at runtime
- Optionally allow override for specific signal types
- Connects to user’s terminal context via cloud sync (or simulation engine)
- Visual builder: accepts one input, one output, and dynamic config panel

🔁 System Integration:
- Ties into backend `/api/margin/status` or runtime margin monitor (MT5 bridge)
- Runtime strategy flow must skip signal if margin < configured threshold
- Error/log pushed to dashboard or Copilot Bot if blocked

🧪 Add Tests:
/client/src/__tests__/StrategyBlocks/MarginFilterBlock.test.tsx  
/backend/desktop-app/tests/test_margin_check.py (if runtime logic added)

Test Cases:
- Margin = 50% → passes
- Margin = 10% → fails (signal blocked)
- Override = true → signal allowed
- Invalid config → error message visible

📂 Tracking:
Once complete:
- ✅ Update `feature_status.md`
- 🧾 Append to `execution_history.md`
- 📘 Log in `dev_changelog.md`

❗ Rules:
- Do NOT confuse with equity limits (this is free margin based)
- Do NOT skip test coverage
- Keep UI/UX consistent with other blocks
