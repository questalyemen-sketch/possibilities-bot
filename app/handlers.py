from __future__ import annotations

import logging
from typing import Any

from .brain import generate_reply
from .database import clear_messages, init_database, save_message, save_user
from .knowledge import assistant_name, load_knowledge
from .telegram_api import send_message

LOGGER = logging.getLogger("personal-assistant.handlers")


def startup() -> None:
    init_database()


def welcome_text() -> str:
    knowledge = load_knowledge()
    name = assistant_name(knowledge)
    return (
        f"مرحبًا، أنا {name}.\n\n"
        "أستطيع الرد على الرسائل بالنيابة عن صالح، باستخدام المعلومات الموجودة في قاعدة معرفتي.\n"
        "اكتب سؤالك أو رسالتك مباشرة.\n\n"
        "الأوامر المتاحة: /help و /who و /reset"
    )


async def handle_update(update: dict[str, Any]) -> None:
    message = update.get("message") or update.get("edited_message")
    if not message:
        return
    chat = message.get("chat") or {}
    user = message.get("from") or {}
    chat_id = chat.get("id")
    user_id = user.get("id") or chat_id
    if not chat_id or not user_id:
        return

    save_user(user)
    text = (message.get("text") or "").strip()
    if not text:
        await send_message(chat_id, load_knowledge().get("fallback", {}).get("non_text", "أرسل رسالتك كتابةً من فضلك."))
        return

    command = text.split()[0].split("@")[0].casefold()
    if command == "/start":
        await send_message(chat_id, welcome_text())
        return
    if command == "/help":
        await send_message(chat_id, "أرسل أي سؤال أو رسالة. أستخدم معلومات صالح الموجودة في data/data.json وأرد بأسلوب واضح.\n\n/who لمعرفة هويتي\n/reset لمسح سياق محادثتك")
        return
    if command == "/who":
        await send_message(chat_id, f"أنا {assistant_name(load_knowledge())}، ولست صالح الخليفي نفسه.")
        return
    if command == "/reset":
        clear_messages(user_id)
        await send_message(chat_id, "تم مسح سياق محادثتك. يمكنك البدء من جديد.")
        return

    save_message(user_id, "in", text)
    reply = await generate_reply(user_id, text)
    save_message(user_id, "out", reply)
    await send_message(chat_id, reply)
