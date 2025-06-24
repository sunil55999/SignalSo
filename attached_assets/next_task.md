📌 NEXT TASK – Replit Agent Build Guide (Phase 7: UI + Analytics)

🧠 Task:
Create a trust scoring engine to evaluate signal providers based on historical performance and signal quality.

🔧 File to Create:
`/client/src/utils/ProviderTrustScore.ts`

🧩 Description:
Build a scoring system that outputs a numeric trust score (0–100) for each signal provider, based on:

📊 Metrics to Factor:
- ✅ Total signals vs total trades
- ✅ TP hit rate vs SL hit rate
- ✅ Average drawdown
- ✅ Cancelled signal ratio
- ✅ Parsing confidence average
- ✅ Execution delay average (from MT5 logs)

🎯 Example Output:
```ts
{
  provider_id: "@gold_signals",
  trust_score: 87.5,
  grade: "A",
  metrics: {
    tp_rate: 0.75,
    avg_drawdown: 3.2,
    cancel_rate: 0.08,
    confidence: 0.92,
    latency: 1.4
  }
}
🧪 Test File:
/client/src/tests/ProviderTrustScore.test.ts

Test Scenarios:

TP > 60%, low SL = high score

High cancel ratio → trust < 50

Score normalizes correctly across providers

Edge case: < 10 signals → neutral score fallback

📦 Integration Targets:

Used by: ProviderCompare.tsx, AnalyticsProviderTable.tsx

Optional: show badge/score on Dashboard provider card

📂 Once Done:

✅ Update /attached_assets/feature_status.md

🧾 Log to /attached_assets/execution_history.md

📘 Log to /attached_assets/dev_changelog.md

❗ Rules:

Normalize metrics (0–1 range), then weight and scale to 0–100

Use shared utility functions (import from shared/metrics.ts if needed)

Must support real-time recalculation


