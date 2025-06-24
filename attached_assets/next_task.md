📌 NEXT TASK – Replit Agent Build Guide (Phase 4: Strategy Builder Blocks)
📅 Date: 2025-06-24

🧠 Task:
Complete the `KeywordBlacklistBlock.tsx` by adding the missing logic to preview how blacklisted keywords affect live signals before execution.

🔧 File to Complete:
`/client/src/blocks/KeywordBlacklistBlock.tsx`

🧩 Description:
This UI block is already scaffolded visually. You now need to implement:
- A form to input blacklisted keywords (comma-separated or tag-style)
- A live preview panel showing: ✅ allowed or ❌ blocked signals
- Connection to runtime config so it updates `strategy_runtime.ts` rules dynamically

🎯 Features to Implement:
- Real-time filtering preview based on test messages
- Keyword matching in lowercase
- Exact match and fuzzy mode toggle
- “Apply to all pairs” checkbox
- Store block config in local strategy state

🧪 Required Test File:
`/client/src/tests/blocks/keyword_blacklist_block.test.tsx`

Test Scenarios:
- Signal: “HIGH RISK - GOLD” → blocked with “high risk” keyword
- Signal: “Buy BTC with leverage” → blocked if “leverage” is set
- Signal preview reflects changes immediately
- Fuzzy vs strict match modes

📦 Integration:
- Syncs with: `strategy_runtime.ts`, `strategy_config.json`
- Hooks into existing signal simulator if present

📂 Track Upon Completion:
- `attached_assets/feature_status.md`
- `attached_assets/dev_changelog.md`
- `attached_assets/execution_history.md`

❗ Guidelines:
- Match logic must use `.includes()` or regex depending on mode
- Should not affect system performance on large datasets
- Make sure this integrates cleanly into strategy export JSON
