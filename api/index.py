from __future__ import annotations

import asyncio
import hmac
import os

from flask import Flask, jsonify, request

from app.handlers import handle_update, startup

app = Flask(__name__)
startup()
EXPECTED_SECRET = os.getenv("TELEGRAM_WEBHOOK_SECRET", "").strip()


@app.get("/")
def health() -> tuple[dict[str, str], int]:
    return {"status": "ok", "service": "personal-assistant"}, 200


@app.post("/")
def webhook() -> tuple[dict[str, bool], int]:
    if EXPECTED_SECRET:
        supplied = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
        if not hmac.compare_digest(supplied, EXPECTED_SECRET):
            return {"ok": False}, 401
    update = request.get_json(silent=True)
    if not isinstance(update, dict):
        return {"ok": False}, 400
    try:
        asyncio.run(handle_update(update))
    except Exception:
        app.logger.exception("Webhook update failed")
        return {"ok": False}, 500
    return {"ok": True}, 200


@app.get("/health")
def health_alias():
    return jsonify({"status": "ok"})
