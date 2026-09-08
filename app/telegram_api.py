from __future__ import annotations

import logging
import os
from typing import Any

import httpx

LOGGER = logging.getLogger("personal-assistant.telegram")
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
BASE_URL = f"https://api.telegram.org/bot{TOKEN}"


async def call(method: str, payload: dict[str, Any]) -> dict[str, Any]:
    if not TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is required")
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(f"{BASE_URL}/{method}", json=payload)
        response.raise_for_status()
        return response.json()


async def send_message(chat_id: int, text: str) -> None:
    chunks = [text[index:index + 4000] for index in range(0, len(text), 4000)] or ["..."]
    for chunk in chunks:
        await call("sendMessage", {"chat_id": chat_id, "text": chunk})
