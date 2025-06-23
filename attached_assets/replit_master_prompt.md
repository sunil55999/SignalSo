# 🤖 Replit Agent – Master Development Prompt for SignalOS

Welcome Agent. You are working on **SignalOS**, a full-featured, intelligent Telegram Signal Copier system. Your role is to continue development **module by module**, referencing the defined upgrade plan and task protocols.

---

## 📁 Project Structure

The project is structured into 3 major layers:

```
/desktop-app/              # Signal parsing, execution, logic, retry, filters
/server/                   # Express API, Firebridge, routes, database sync
/client/                   # React + TS frontend (admin panel, dashboard, builder)
/attached_assets/          # *.md tracking files
```

✅ Only write inside the `/desktop-app/`, `/client/`, and `/server/` directories.
❌ Never create files in root, `/mobile/`, `/firebase/`, or other legacy folders.

---

## 📘 What You Must Follow

### 1. Always Read the Next Task

* File: `/attached_assets/next_task.md`
* It defines:

  * 📂 File to create/edit
  * 🧠 Description of what to build
  * 🔁 Related modules to integrate with
  * 🧪 Required test suite

### 2. Track Your Progress

After completing any module:

* ✅ Mark complete in `/attached_assets/feature_status.md`
* 📘 Log a summary to `/attached_assets/dev_changelog.md`
* 🧾 Append to `/attached_assets/execution_history.md`

Do this *before* you move to the next task.

### 3. Stay Within Scope

* Only build what is in `next_task.md`
* Do not start the next phase or build multiple modules in one pass
* No code duplication – always check `execution_history.md` for existing logic

---

## ⚙️ Required Conventions

### Tests

* All test modules go in: `/desktop-app/tests/`
* Match file names: `test_<module>.py`
* Cover edge cases, integrations, and failure modes

### Configuration Files

* Strategy files use `.json` or `.config.ts`
* Core logic modules are `.py`
* UI blocks are `.tsx`

### Telegram Bot Features

* All Copilot logic must be under `/desktop-app/copilot_*.py`

---

## 📌 Do Not:

* Skip tasks
* Modify existing files without logging it
* Start new phases on your own
* Add external services unless explicitly stated

---

## ✅ Start Instructions

Before any work:

```bash
# Step 1: Read the next task
open /attached_assets/next_task.md

# Step 2: Confirm existing progress
open /attached_assets/feature_status.md

# Step 3: Avoid duplication
open /attached_assets/execution_history.md
```

After completing a task:

```bash
# Track your work
edit /attached_assets/dev_changelog.md
edit /attached_assets/execution_history.md
edit /attached_assets/feature_status.md
```

---

Thank you. Please continue building the future of SignalOS one task at a time, clearly, robustly, and efficiently.
