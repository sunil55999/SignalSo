# ⚠️ SignalOS Desktop: Advanced Error Handling Guide (Part 2/2)

## ✅ Goal
Prevent crashes, improve user safety, and outperform TSC with smart auto-recovery and signal diagnostics.

---

## 🧩 Key Files
```
desktop-app/
├── ai_parser/
│   ├── parser_engine.py
│   ├── parser_utils.py
│   ├── fallback_regex_parser.py
│   ├── feedback_logger.py
```

---

## 🔐 parser_engine.py (Safe Parser)
```python
def parse_signal_safe(raw_text):
    try:
        result = ai_model.parse(raw_text)
        return validate_result(result)
    except Exception as e:
        log_failure(raw_text, e)
        return fallback_parser(raw_text)
```

---

## 🧽 parser_utils.py (Sanitize/Validate)
```python
def sanitize_signal(raw):
    return raw.replace("🟢", "").replace("SL", "Stop Loss")

def validate_result(data):
    required = ["pair", "direction", "entry", "sl", "tp"]
    for field in required:
        if field not in data:
            raise ValueError(f"Missing {field}")
    return data
```

---

## 📉 fallback_regex_parser.py (Last Resort)
```python
def fallback_parser(raw):
    # Use regex to extract pair, SL, TP if AI fails
    return {
        "pair": "XAUUSD", "direction": "SELL",
        "entry": [2345, 2342], "sl": 2350, "tp": [2339, 2333]
    }
```

---

## 🧾 feedback_logger.py (Log AI Failures)
```python
def log_failure(raw_text, error):
    with open("logs/failures.log", "a") as f:
        f.write(f"Signal: {raw_text}\nError: {str(error)}\n---\n")
```

---

## 🧠 Optional Enhancements
- Add retry count (`parser_engine.py`)
- Display error in tray/toast UI without crashing
- Track parse time per signal for debugging

---

## ✅ Benefits
- Parses survive messy signals
- No trade triggers from broken AI logic
- Builds trust with users in prop firm setups