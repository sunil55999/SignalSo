# 📌 NEXT TASK – Replit Agent Build Guide (Auto Updated per Phase)

## 📅 Date: 2025-06-23

## 🧠 Task:
You must now implement the **SL manager logic** in Phase 2 Advanced Order Management.

## 🔧 File to Create:
- `/desktop-app/sl_manager.py`

## 🧩 Description:
Implement advanced stop loss management:
- Dynamic SL adjustment based on market conditions
- Trailing SL integration with existing trailing stop engine
- SL modification on TP hits and breakeven triggers
- Multiple SL strategies (ATR-based, volatility-based, time-based)
- Integration with existing risk management engines

## 🔁 System Impact:
- Updates strategy runtime logic
- Integrates with `trailing_stop.py`, `break_even.py`, and `tp_manager.py`
- Will need integration with `mt5_bridge.py` for SL modifications
- Integration with signal parser for SL commands

## 🧪 Add Tests:
- `/desktop-app/tests/test_sl_manager.py`
- Cover: dynamic adjustments, integration scenarios, edge cases

## 📂 Tracking:
Once complete:
- Update `feature_status.md`
- Log in `execution_history.md`
- Add changelog entry to `dev_changelog.md`

## ❗ Rules:
- DO NOT start next module until this is ✅ done
- DO NOT re-create any already implemented file listed in `execution_history.md`
- DO NOT write into `/mobile/`, `/firebase/`, or non-project folders

