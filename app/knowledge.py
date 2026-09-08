from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

LOGGER = logging.getLogger("personal-assistant.knowledge")
DEFAULT_PATH = Path(__file__).resolve().parent.parent / "data" / "data.json"


def load_knowledge() -> dict[str, Any]:
    path = Path(os.getenv("KNOWLEDGE_PATH", str(DEFAULT_PATH)))
    try:
        with path.open("r", encoding="utf-8") as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError, OSError) as exc:
        LOGGER.warning("Could not load knowledge file: %s", type(exc).__name__)
        return {
            "assistant": {"name": "مساعد صالح الخليفي", "owner_name": "صالح الخليفي"},
            "style": {"language": "العربية", "tone": "ودود ومختصر", "use_emojis": False},
            "facts": [],
            "projects": [],
            "services": [],
            "contacts": [],
            "rules": [],
            "fallback": {"unknown": "لا أملك هذه المعلومة حاليًا."},
        }


def assistant_name(knowledge: dict[str, Any]) -> str:
    return knowledge.get("assistant", {}).get("name", "مساعد صالح الخليفي")


def owner_name(knowledge: dict[str, Any]) -> str:
    return knowledge.get("assistant", {}).get("owner_name", "صالح الخليفي")


def find_relevant_knowledge(query: str, knowledge: dict[str, Any], limit: int = 5) -> list[str]:
    normalized = query.casefold()
    matches: list[str] = []
    for fact in knowledge.get("facts", []):
        keywords = [str(item).casefold() for item in fact.get("keywords", [])]
        if any(keyword and keyword in normalized for keyword in keywords):
            answer = fact.get("answer")
            if answer:
                matches.append(str(answer))
    return matches[:limit]


def knowledge_context(knowledge: dict[str, Any]) -> str:
    owner = knowledge.get("owner", {})
    lines = [
        f"اسم صاحب المساعد: {owner.get('name', owner_name(knowledge))}",
        f"نبذة: {owner.get('bio', '')}",
        f"الدور: {owner.get('role', '')}",
        f"الموقع: {owner.get('location', '')}",
    ]
    for label, key in [("المشاريع", "projects"), ("الخدمات", "services"), ("جهات التواصل", "contacts")]:
        values = knowledge.get(key, [])
        if values:
            lines.append(f"{label}: {json.dumps(values, ensure_ascii=False)}")
    return "\n".join(line for line in lines if line.split(":", 1)[-1].strip())


def fallback_reply(text: str, knowledge: dict[str, Any]) -> str:
    matches = find_relevant_knowledge(text, knowledge)
    if matches:
        return matches[0]
    return knowledge.get("fallback", {}).get(
        "unknown",
        f"أنا {assistant_name(knowledge)}. لا أملك هذه المعلومة حاليًا.",
    )
