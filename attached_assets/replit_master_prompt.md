# 📌 Replit Agent Master Prompt – SignalOS

This file defines the **official execution protocol** for Replit Agent when building SignalOS. It ensures all tasks are aligned with the upgrade plan, changes are tracked, and no mess is introduced.

---

## 🧠 PRIMARY RULE

You must follow the file `/attached_assets/SignalOS Replit Upgrade Plan.md` step-by-step. Do not build outside of it. Do not improvise.

---

## ✅ FOLDER RULES

Allowed folders only:

```
signalos/
├── desktop-app/
├── server/
├── client/
├── shared/
├── logs/
├── deployment/
├── attached_assets/
```

Do NOT use or touch:

- `/mobile/`
- `/firebase-app/`
- Anything outside `signalos/`

---

## 🚧 HOW TO START EVERY SESSION

1. Read `/attached_assets/SignalOS Replit Upgrade Plan.md`
2. Read `/attached_assets/execution_history.md` (see what’s already done)
3. Read `/attached_assets/next_task.md` (defines current module)
4. Log changes to `/attached_assets/dev_changelog.md`
5. Implement task
6. Mark complete in `/attached_assets/feature_status.md`
7. Append update to `/attached_assets/execution_history.md`

---

## 🧪 TESTING REQUIREMENTS

Every new file/module must have tests in:

- `/desktop-app/tests/`
- `/server/tests/`
- `/client/__tests__/`

Example test cases:

- Retry conditions
- Invalid SL/TP parsing
- MT5 bridge failure recovery
- Strategy logic branch coverage

---

## 🚀 DEPLOYMENT SETUP

Every build must:

- Use `.env.template`
- Support PM2 or Docker
- Include log outputs to `/logs/`
- Be tested with terminal simulator

---

## 🔒 FINAL SAFETY RULES

- DO NOT duplicate features
- DO NOT create random new files
- Always consult `execution_history.md` and `next_task.md`
- If unsure, request clarification in `execution_history.md`

---

## 🎯 SignalOS Finish Criteria

You are finished when:

- All features in `feature_status.md` are ✅
- `execution_history.md` and `dev_changelog.md` are complete
- `next_task.md` says "No pending items."

This prompt governs every development session for SignalOS and prevents all redundancy or wasted code.

