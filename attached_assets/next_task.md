📌 NEXT TASK – Replit Agent Build Guide (Phase 1: Signal Execution Core)
📅 Date: 2025-06-24

🧠 Task:
Finalize the logic in `entry_range.py` to handle multiple entry point selection strategies from parsed signal ranges.

🔧 File to Complete:
`/desktop-app/entry_range.py`

🧩 Description:
Handle signals with entry ranges (e.g., “Entry: 1.1045–1.1065”) and select the optimal execution point based on strategy config.

✅ Required Modes:
- `best`: Select lowest price for BUY, highest for SELL
- `average`: Midpoint of entry range
- `second`: Second-best entry if multiple provided
- `fallback_to_single`: If only one entry is parsed

🎯 Inputs:
- `entry_range: List[float]` (e.g., [1.1045, 1.1055, 1.1065])
- `signal_direction: "BUY" | "SELL"`
- `strategy_mode: "best" | "average" | "second"`

🎯 Output:
- `selected_entry_price: float`

🧪 Required Test File:
`/desktop-app/tests/test_entry_range.py`

Test Cases:
- BUY range: [1.1000, 1.1020, 1.1035] → best = 1.1000
- SELL range: [1.1000, 1.1020, 1.1035] → best = 1.1035
- Average logic for both
- Second-best logic
- Single-entry fallback

📦 Integration:
- Used by: `parser.py`, `strategy_runtime.py`
- Optional hook in `signal_simulator.py` for preview

📂 Track Upon Completion:
- ✅ `attached_assets/feature_status.md`
- 🧾 `attached_assets/execution_history.md`
- 📘 `attached_assets/dev_changelog.md`

❗ Guidelines:
- Handle edge cases (empty list, duplicates, float rounding)
- Log selected mode and price
