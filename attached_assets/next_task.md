📌 NEXT TASK – Replit Agent Build Guide (Auto Updated)
📅 Date: 2025-06-23

🧠 Task:
Implement `time_window` block from Phase 4 – Strategy Builder Blocks.

🔧 File to Create:
/signalos/client/src/components/strategy-blocks/TimeWindowBlock.tsx

🧩 Description:
Build a strategy builder block that allows users to set time-based filters for signal execution.

Requirements:
- Visual block for drag-and-drop strategy builder
- Configure trading time windows (e.g., 8:00-16:00 UTC)
- Support multiple time zones and session overlaps
- Weekend/holiday filtering options
- Block connections: input (signal), output (filtered signal)
- Real-time validation of current time against windows

🔁 System Impact:
- Integrates with existing strategy flow builder
- Affects signal processing pipeline in strategy runtime
- Links to desktop-app time validation logic
- Updates strategy execution conditions

🧪 Add Tests:
/signalos/client/src/components/strategy-blocks/__tests__/TimeWindowBlock.test.tsx

Test Cases:
- Time window validation during market hours
- Timezone conversion accuracy
- Weekend filtering behavior
- Block connection and data flow

📂 Tracking:
Once complete:
- ✅ Update `feature_status.md`
- 🧾 Append to `execution_history.md`
- 📘 Log the change in `dev_changelog.md`

❗ Rules:
- DO NOT hardcode time zones - use proper timezone libraries
- DO NOT bypass weekend checks in forex markets
- DO NOT skip responsive design for mobile strategy building