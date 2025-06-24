📌 NEXT TASK – Replit Agent Build Guide (Phase 13: Auth + Terminal Integration)

🧠 Objective:
Integrate user authentication and terminal identification to securely bind desktop app usage to dashboard users.

---

🔧 1. `/desktop-app/auth.py` – Desktop Auth Token Manager
📂 Description:
- Handle login via token input OR read from `.signalos/config.json`
- Store JWT securely for future sessions
- Validate token by calling `/api/me` endpoint

✅ Implement:
```python
get_auth_token() → str
store_auth_token(token: str)
validate_token(token: str) → bool
🔧 2. /desktop-app/terminal_identity.py – Terminal Fingerprint
📂 Description:

Generate a terminal_id using UUID4 + OS + MAC hash

Save to local file and reuse across sessions

✅ Implement:

python
Copy
Edit
get_terminal_id() → str
🔧 3. /desktop-app/api_client.py – Authenticated API Utility
📂 Description:

Reusable helper to send authenticated requests

Handles errors + retries + token inclusion

✅ Must Support:

POST /api/register_terminal

GET /api/terminal_config

POST /api/report_status

🔧 4. Add Call to register_terminal() on Startup
📂 File to Update: main.py or auto_sync.py

✅ Payload Example:

json
Copy
Edit
{
  "token": "<JWT>",
  "terminal_id": "xyz-1234",
  "os": "Windows",
  "version": "1.0.6"
}
🧩 Server API will respond with:

✅ Whether the terminal is approved

🧠 Config overrides if present

🧪 5. Add Tests:

/tests/test_auth.py – validate token storage and retry

/tests/test_terminal_identity.py – test ID persistency

/tests/test_api_client.py – simulate mock API and retry logic

📦 Once Done:

✅ Update feature_status.md

📘 Log into dev_changelog.md

🧾 Log into execution_history.md

❗ Guidelines:

Do not hardcode token anywhere

Do not allow trade execution if auth fails

Future support: QR token auth, multi-terminal management