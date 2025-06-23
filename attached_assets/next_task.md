# 📌 NEXT TASK – Replit Agent Build Guide (Auto Updated per Phase)

## 📅 Date: 2025-06-23

## 🧠 Task:
You must now implement the **TP manager logic** in Phase 2 Advanced Order Management.

## 🔧 File to Create:
- `/desktop-app/tp_manager.py`

## 🧩 Description:
Implement advanced take profit management:
- Support for multiple TP levels (TP1, TP2, TP3, TP4, TP5)
- Partial close automation when TP levels are hit
- Dynamic TP adjustment based on market conditions
- Integration with existing partial close and break even engines
- TP hit detection and automated actions

## 🔁 System Impact:
- Updates strategy runtime logic
- Integrates with `partial_close.py` and `break_even.py`
- Will need integration with `mt5_bridge.py` for TP modifications
- Integration with signal parser for TP commands

## 🧪 Add Tests:
- `/desktop-app/tests/test_tp_manager.py`
- Cover: multiple TP levels, partial closes, dynamic adjustments, edge cases

## 📂 Tracking:
Once complete:
- Update `feature_status.md`
- Log in `execution_history.md`
- Add changelog entry to `dev_changelog.md`

## ❗ Rules:
- DO NOT start next module until this is ✅ done
- DO NOT re-create any already implemented file listed in `execution_history.md`
- DO NOT write into `/mobile/`, `/firebase/`, or non-project folders

