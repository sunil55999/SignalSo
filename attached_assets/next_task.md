📌 NEXT TASK – Replit Agent Build Guide (Auto Updated)
📅 Date: 2025-06-23

🧠 Task:
Implement `margin_filter` block from Phase 4 – Strategy Builder Blocks.

🔧 File to Create:
/client/src/components/strategy-blocks/MarginFilterBlock.tsx

🧩 Description:
Build a strategy builder block that filters signals based on margin requirements and account balance.

Requirements:
- Visual block for drag-and-drop strategy builder
- Calculate required margin for signal lot size
- Check available margin against minimum thresholds
- Support different account leverage settings
- Block connections: input (signal), output (filtered signal)
- Real-time margin calculation with account balance integration

🔁 System Impact:
- Integrates with existing strategy flow builder
- Links to desktop-app account balance monitoring
- Affects signal processing pipeline in strategy runtime
- Updates strategy execution conditions based on margin availability

🧪 Add Tests:
/client/src/components/strategy-blocks/__tests__/MarginFilterBlock.test.tsx

Test Cases:
- Margin calculation accuracy for different symbols
- Account balance threshold validation
- Leverage setting impact on margin requirements
- Block connection and data flow validation

📂 Tracking:
Once complete:
- ✅ Update `feature_status.md`
- 🧾 Append to `execution_history.md`
- 📘 Log the change in `dev_changelog.md`

❗ Rules:
- DO NOT use hardcoded margin requirements - calculate dynamically per symbol
- DO NOT bypass account balance checks
- DO NOT ignore leverage settings in margin calculations