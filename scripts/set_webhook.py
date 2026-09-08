from __future__ import annotations

import os
import sys

import httpx
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
SECRET = os.getenv("TELEGRAM_WEBHOOK_SECRET", "").strip()

if len(sys.argv) != 2:
    raise SystemExit("Usage: python scripts/set_webhook.py https://your-domain.vercel.app/api")
if not TOKEN:
    raise SystemExit("TELEGRAM_BOT_TOKEN is required")

url = sys.argv[1].rstrip("/")
payload = {"url": url}
if SECRET:
    payload["secret_token"] = SECRET
response = httpx.post(f"https://api.telegram.org/bot{TOKEN}/setWebhook", json=payload, timeout=30)
response.raise_for_status()
result = response.json()
print({"ok": result.get("ok"), "description": result.get("description")})
