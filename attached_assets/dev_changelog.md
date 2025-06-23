# 📘 SignalOS Dev Changelog

> Chronological log of development milestones, timestamps, and affected files/modules.

---

## \[2025-06-23] – Phase 7–9 Completion

📂 /desktop-app/tp\_sl\_adjustor.py
🧠 Added pip-based SL/TP adjustment logic
📂 /desktop-app/multi\_tp\_manager.py
🧠 Enabled up to 100 TP levels + SL shift logic

📂 /desktop-app/spread\_checker.py
🧠 Block trades when spread > configured threshold
📂 /desktop-app/news\_filter.py
🧠 Block signals near red news events
📂 /desktop-app/margin\_level\_checker.py
🧠 Margin% threshold enforcement before trade

📂 /desktop-app/reverse\_strategy.py
🧠 Reverses trade signal direction
📂 /desktop-app/grid\_strategy.py
🧠 Implements fixed pip interval grid logic

📂 /client/StrategyBlocks/rr\_condition.tsx
🧠 Add R\:R ratio filter to GUI strategy builder
📂 /client/StrategyBlocks/keyword\_blacklist.tsx
🧠 UI block to block signals by content words

---

## \[2025-06-22] – Core Infrastructure Setup

📂 /desktop-app/strategy\_runtime.py
🧠 Strategy profile engine with JSON + GUI integration
📂 /desktop-app/retry\_engine.py
🧠 Smart retry logic on failed executions
📂 /desktop-app/auto\_sync.py
🧠 Sync config and logic from server to desktop
📂 /desktop-app/copilot\_bot.py
🧠 Telegram Bot for trade preview and command

📂 /server/routes/firebridge.ts
🧠 MT5 signal sync API setup
📂 /server/ws/server.ts
🧠 WebSocket real-time sync handler

📂 /client/pages/Dashboard.vue
🧠 Live execution feed with trade signal info
📂 /client/components/StrategyBuilder.vue
🧠 Drag & drop block builder for signal logic

✅ Changelog maintained manually after each module.
