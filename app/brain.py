from __future__ import annotations

import logging
import os
from typing import Any

import httpx

from .database import recent_messages
from .knowledge import (
    assistant_name,
    fallback_reply,
    find_relevant_knowledge,
    knowledge_context,
    load_knowledge,
)

LOGGER = logging.getLogger("personal-assistant.brain")
OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY", "").strip()
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "openrouter/free").strip()


def system_prompt(knowledge: dict[str, Any], relevant: list[str]) -> str:
    rules = "\n".join(f"- {rule}" for rule in knowledge.get("rules", []))
    relevant_text = "\n".join(f"- {item}" for item in relevant) or "لا توجد معلومة مباشرة مرتبطة بالسؤال."
    return f"""
أنت {assistant_name(knowledge)}.
أنت مساعد شخصي لصالح الخليفي، ولست صالح الخليفي نفسه. عندما يسأل أحد: من أنت؟ أجب: أنا مساعد صالح الخليفي.
مهمتك الرد بالنيابة عن صالح بأسلوب {knowledge.get('style', {}).get('tone', 'ودود وواضح')} وباللغة العربية.
كن مختصرًا ومفيدًا ولا تخترع معلومات. لا تقل إنك تملك مشاعر أو تجارب بشرية.

معلومات صاحب المساعد:
{knowledge_context(knowledge)}

معلومات مرتبطة بسؤال المستخدم:
{relevant_text}

قواعد ثابتة:
{rules}

إذا لم توجد إجابة في المعلومات، قل بوضوح إن المعلومة غير موجودة واطلب من المستخدم إضافة المعلومة إلى data/data.json.
""".strip()


async def generate_reply(user_id: int, text: str) -> str:
    knowledge = load_knowledge()
    relevant = find_relevant_knowledge(text, knowledge)
    if not OPENROUTER_KEY:
        return fallback_reply(text, knowledge)

    messages = [{"role": "system", "content": system_prompt(knowledge, relevant)}]
    messages.extend(recent_messages(user_id))
    messages.append({"role": "user", "content": text})
    payload = {
        "model": OPENROUTER_MODEL,
        "temperature": 0.55,
        "max_tokens": 500,
        "messages": messages,
    }
    headers = {
        "Authorization": f"Bearer {OPENROUTER_KEY}",
        "HTTP-Referer": os.getenv("OPENROUTER_SITE_URL", "https://github.com/questalyemen-sketch/possibilities-bot"),
        "X-Title": os.getenv("OPENROUTER_APP_NAME", "Possibilities Bot"),
    }
    try:
        async with httpx.AsyncClient(timeout=45) as client:
            response = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            body = response.json()
            message = (body.get("choices") or [{}])[0].get("message") or {}
            content = message.get("content")
            if content and isinstance(content, str):
                return content.strip()
    except Exception as exc:
        LOGGER.warning("AI provider failed: %s", type(exc).__name__)
    return fallback_reply(text, knowledge)
