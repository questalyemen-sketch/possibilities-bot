from __future__ import annotations

import asyncio
import hmac
import os
from typing import Any

from flask import Flask, jsonify, request

from app.handlers import handle_update, startup


app = Flask(__name__)

# تهيئة قاعدة البيانات عند تشغيل الدالة
startup()

EXPECTED_SECRET = os.getenv("TELEGRAM_WEBHOOK_SECRET", "").strip()


def process_webhook() -> tuple[dict[str, Any], int]:
    """استقبال ومعالجة تحديثات Telegram."""
    
    # التحقق من Secret Token إذا كان مفعّلًا في Vercel
    if EXPECTED_SECRET:
        supplied_secret = request.headers.get(
            "X-Telegram-Bot-Api-Secret-Token", ""
        )

        if not hmac.compare_digest(supplied_secret, EXPECTED_SECRET):
            return {"ok": False, "error": "Unauthorized"}, 401

    # قراءة تحديث Telegram
    update = request.get_json(silent=True)

    if not isinstance(update, dict):
        return {"ok": False, "error": "Invalid Telegram update"}, 400

    try:
        asyncio.run(handle_update(update))
    except Exception:
        app.logger.exception("Telegram webhook update failed")
        return {"ok": False, "error": "Internal server error"}, 500

    return {"ok": True}, 200


@app.get("/")
def health() -> tuple[dict[str, str], int]:
    """صفحة فحص حالة البوت."""
    return {
        "status": "ok",
        "service": "possibilities-bot",
    }, 200


@app.get("/health")
def health_alias() -> tuple[dict[str, str], int]:
    """مسار إضافي لفحص الخدمة."""
    return jsonify({
        "status": "ok",
        "service": "possibilities-bot",
    })


@app.post("/")
def webhook_root() -> tuple[dict[str, Any], int]:
    """استقبال Webhook إذا وصل إلى الجذر."""
    return process_webhook()


@app.post("/api")
def webhook_api() -> tuple[dict[str, Any], int]:
    """استقبال Webhook من Telegram على مسار /api."""
    return process_webhook()