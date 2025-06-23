# 📌 NEXT TASK – Replit Agent Build Guide (Auto Updated per Phase)

## 📅 Date: 2025-06-23

## 🧠 Task:
You must now implement the **R:R converter logic** in Phase 2 Advanced Order Management.

## 🔧 File to Create:
- `/desktop-app/rr_converter.py`

## 🧩 Description:
Implement risk-reward ratio converter and calculator:
- Convert R:R ratios to specific price levels
- Calculate optimal SL and TP placement based on R:R targets
- Support for multiple R:R strategies (1:1, 1:2, 1:3, custom ratios)
- Integration with existing SL and TP managers
- Real-time R:R monitoring and adjustment capabilities

## 🔁 System Impact:
- Updates strategy runtime logic
- Integrates with `sl_manager.py`, `tp_manager.py`, and risk management engines
- Will need integration with `mt5_bridge.py` for price calculations
- Integration with signal parser for R:R commands

## 🧪 Add Tests:
- `/desktop-app/tests/test_rr_converter.py`
- Cover: R:R calculations, price conversions, integration scenarios, edge cases

## 📂 Tracking:
Once complete:
- Update `feature_status.md`
- Log in `execution_history.md`
- Add changelog entry to `dev_changelog.md`

## ❗ Rules:
- DO NOT start next module until this is ✅ done
- DO NOT re-create any already implemented file listed in `execution_history.md`
- DO NOT write into `/mobile/`, `/firebase/`, or non-project folders

