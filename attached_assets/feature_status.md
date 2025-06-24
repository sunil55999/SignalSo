✅ TASK COMPLETED – Lotsize Engine (Phase 8: Lotsize + Entry)
📅 Date: 2025-06-24

🧠 Task:
✅ COMPLETED: Implement `lotsize_engine.py` to support advanced position sizing logic based on signal content or user configuration.

🔧 File to Upgrade:
`/desktop-app/parser.py`

🧩 Required Features:
1. **Signal Intent Recognition:**
   - Identify BUY/SELL, market/pending order
   - Extract symbol (e.g., XAUUSD, BTCUSD, NAS100)

2. **Price Extraction:**
   - Entry price (e.g., “Enter at 1.1045”)
   - Stop loss and take profits (up to 3 levels)
   - Support ranges (e.g., “Entry: 1.1045–1.1055”)

3. **Advanced Text Processing:**
   - Handle multiple formats (English, Hindi, Arabic, Russian)
   - Use spaCy/transformers-based parser (NLP pipeline stub)
   - Add fallback regex rules

4. **Confidence Scoring:**
   - Assign confidence 0–1 per extracted field
   - Drop/flag if score < threshold (e.g., 0.7)

5. **Parser Output Format:**
   - Return unified `ParsedSignal` object:
     ```python
     {
       "symbol": "XAUUSD",
       "entry": 1.1045,
       "sl": 1.1000,
       "tp": [1.1080, 1.1100],
       "order_type": "BUY_LIMIT",
       "confidence": 0.86
     }
     ```

🧪 Test File:
`/desktop-app/tests/test_parser.py`

Test Scenarios:
- “Buy GOLD at 2355 SL 2349 TP 2362”
- “بيع EURUSD دخول: 1.0990 وقف: 1.0940 هدف: 1.1060”
- Hindi/Arabic/Russian text with correct extraction
- Unclear message → low confidence

📦 Integration Requirements:
- Parser must be used by: `strategy_runtime.py`, `signal_simulator.py`, `copilot_bot.py`
- Add to parser registry/config if modular

📂 Update After Completion:
- `attached_assets/feature_status.md`
- `attached_assets/dev_changelog.md`
- `attached_assets/execution_history.md`

❗ Implementation Guidelines:
- Use fallback-safe logic (NLP → regex → fail gracefully)
- Log failed parses for analysis
- Must support dry-run mode (used in simulation)

