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

2. Find the next feature in **Phase 1** that is `[⛔] Not Started` in `/attached_assets/feature_status.md`

3. Add a new entry in `/attached_assets/dev_changelog.md`:

   - 📂 File you’ll work on
   - 🧠 Task description
   - 🕒 Current timestamp

4. Implement feature strictly as defined in the upgrade plan.

5. Create required tests.

6. Mark feature as `[✅]` or `[🚧]` in `/attached_assets/feature_status.md`

7. Commit and move to the next feature.

---

## 🧪 TESTING

For every module, create test files in:

- `/desktop-app/tests/`
- `/server/tests/`
- `/client/__tests__/`

All tests must match real-world signal formats, retry conditions, or WebSocket output.

---

## 🚀 DEPLOYMENT SETUP

Every module must:

- Use `.env.template` properly
- Be compatible with Docker and PM2
- Support logs and restart safety

---

## 🔒 FINAL RULES

- Log your changes (dev\_changelog.md)
- Track your status (feature\_status.md)
- Follow the upgrade plan line-by-line
- NEVER skip steps or write duplicate logic

You are building SignalOS for production. Keep it modular. Keep it clean. Keep it tracked.

