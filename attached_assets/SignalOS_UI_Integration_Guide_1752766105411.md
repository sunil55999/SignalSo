# 🖥️ SignalOS Desktop App – UI Integration & Functional Wiring Guide

**Last Updated:** 2025-07-17 15:25:21

---

## 🎯 Objective

Build a modular, future-proof UI that cleanly connects:
- AI Parser
- Execution Engine (MT4/MT5 bridge)
- Telegram Integration
- Config & Logs System
- Licensing
- Auto-Updater
- Placeholder for Future API/Backend

---

## 1. 📁 Suggested Folder Structure

```
/src
  /ui                # UI components (Tauri/Svelte or Electron/React)
  /parser            # AI parser interfaces (LLM, regex, spaCy)
  /executor          # Trade bridge + MT4 socket manager
  /telegram          # Telegram login/session/channel management
  /auth              # License check + session management
  /config            # Load/save per-channel settings
  /logs              # Error/success logs
  /updater           # Auto-update manager
  /router            # Orchestrates signal flow
  /bridge_api        # Socket placeholders for backend/API
```

---

## 2. 🧩 UI Components & Connections

| UI Panel | Connected Modules |
|----------|--------------------|
| Login/Auth | `auth`, `telegram`, `config` |
| Dashboard | `logs`, `executor`, `parser`, `config` |
| Signal Validator | `parser`, `logs` |
| Channel Setup | `telegram`, `parser`, `config` |
| Logs View | `logs` |
| Strategy Backtest | `parser`, `executor`, `logs` |
| Settings Panel | `config`, `telegram`, `auth`, `updater` |

---

## 3. 🧠 Main Router Logic (Signal → Execution)

```js
onSignalReceived(signalRaw) => {
  parsed = parser.process(signalRaw)
  if (parsed.valid) {
    executor.sendToMT4(parsed)
    logs.success(parsed)
  } else {
    logs.error(signalRaw, parsed.error)
    if (config.retryOnFailure) retry()
  }
}
```

---

## 4. 🧪 Future-Proofing Considerations

| Feature | Implementation |
|--------|----------------|
| **API-ready Hooks** | Add stubs in `bridge_api` to send `parsed`, `executed`, and `logs` to cloud |
| **Version Handling** | Use `version.json` in root and `versionManager.js` to compare & sync |
| **Config Sync** | Add `configSync()` method in config module to push/pull from user cloud |
| **Multi-Language** | Create language JSON files under `/i18n` and make all UI use dynamic strings |
| **Offline Mode** | Always run parser & config locally; fallback to disk if server not reachable |

---

## 5. 🧰 Developer To-Dos

- [ ] Connect `parser.process()` with multiple engines (LLM, regex fallback)
- [ ] Route signal from Telegram → parser → executor → logger
- [ ] Load/save configs per channel with edit UI
- [ ] Add updater system using Tauri's updater or external zip + patch
- [ ] Add license system using JWT + hardware ID + telegram ID
- [ ] Include error center UI for manual retry/bug report
- [ ] Create API placeholders (`bridge_api/sendResult`, etc.)
- [ ] Log everything locally and rotate old logs

---

## 6. ✅ UI UX Enhancements

- ✅ Use step-by-step channel setup wizard
- ✅ Floating toolbar for live signal feed (on/off toggle)
- ✅ Parser test window with copy-paste simulation
- ✅ Real-time license + session status
- ✅ Light/Dark theme toggle

---

## 📌 Summary

This guide ensures the UI is not just functional — but stable, responsive, and prepped for long-term growth. Once this phase is done, proceed to:

- Phase 2: Backend API
- Phase 3: Admin Panel + Team dashboard
- Phase 4: Cloud backtesting + mobile app

---

**Author:** SignalOS System Architect
