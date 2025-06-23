# 📌 NEXT TASK – Replit Agent Build Guide (Auto Updated per Phase)

## 📅 Date: 2025-06-23

## 🧠 Task:
You must now implement the **entry range logic** in the Desktop App engine.

## 🔧 File to Create:
- `/desktop-app/entry_range.py`

## 🧩 Description:
Implement entry range functionality for pending orders:
- Support entry ranges with upper and lower bounds
- Handle partial fills within the range
- Scale position size based on entry quality
- Integration with pending order management
- Support for limit orders and stop orders within range

## 🔁 System Impact:
- Updates strategy runtime logic
- Will need integration with `mt5_bridge.py` for pending order placement
- Should work with existing trade management engines
- Integration with signal parser for range commands

## 🧪 Add Tests:
- `/desktop-app/tests/test_entry_range.py`
- Cover: range validation, partial fills, scaling logic, edge cases

## 📂 Tracking:
Once complete:
- Update `feature_status.md`
- Log in `execution_history.md`
- Add changelog entry to `dev_changelog.md`

## ❗ Rules:
- DO NOT start next module until this is ✅ done
- DO NOT re-create any already implemented file listed in `execution_history.md`
- DO NOT write into `/mobile/`, `/firebase/`, or non-project folders

