from __future__ import annotations

import json
import logging
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
LOGGER = logging.getLogger("possibilities-bot")

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
OPENAI_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip()
DB_PATH = Path(os.getenv("DATABASE_PATH", "data/possibilities.db"))

FALLBACK_BRANCHES = [
    {
        "title": "المسار الجريء",
        "mood": "شرارة وبداية جديدة",
        "text": "تتوقف عن انتظار الإشارة المثالية. تبدأ بخطوة صغيرة يراها الآخرون عادية، لكنها تغيّر طريقة رؤيتك لنفسك.",
        "first_step": "اكتب أصغر تجربة يمكن تنفيذها خلال 24 ساعة.",
    },
    {
        "title": "المسار الآمن",
        "mood": "هدوء وبناء ذكي",
        "text": "لا تهدم كل شيء. تحتفظ بما يحميك، وتبني مساحة اختبار سرية قبل أن تتخذ القرار الكبير.",
        "first_step": "حدد ما الذي يجب أن يبقى ثابتًا، وما الذي يمكن تجربته.",
    },
    {
        "title": "المسار الغريب",
        "mood": "مصادفة لا تشبه الخطة",
        "text": "تظهر فرصة لم تكن تبحث عنها أصلًا. لا تبدو منطقية في البداية، لكنها تكشف رغبة قديمة أخفيتها تحت كلمة لاحقًا.",
        "first_step": "تحدث مع شخص خارج دائرتك عن هذا القرار واسأله سؤالًا واحدًا فقط.",
    },
]


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def db() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db() -> None:
    with db() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                user_id INTEGER PRIMARY KEY,
                decision TEXT NOT NULL,
                branches TEXT NOT NULL,
                selected_index INTEGER,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )


def save_session(user_id: int, decision: str, branches: list[dict[str, Any]]) -> None:
    timestamp = now()
    with db() as connection:
        connection.execute(
            """
            INSERT INTO sessions(user_id, decision, branches, selected_index, created_at, updated_at)
            VALUES (?, ?, ?, NULL, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                decision=excluded.decision,
                branches=excluded.branches,
                selected_index=NULL,
                updated_at=excluded.updated_at
            """,
            (user_id, decision, json.dumps(branches, ensure_ascii=False), timestamp, timestamp),
        )


def get_session(user_id: int) -> sqlite3.Row | None:
    with db() as connection:
        return connection.execute("SELECT * FROM sessions WHERE user_id = ?", (user_id,)).fetchone()


def select_branch(user_id: int, index: int) -> None:
    with db() as connection:
        connection.execute(
            "UPDATE sessions SET selected_index = ?, updated_at = ? WHERE user_id = ?",
            (index, now(), user_id),
        )


async def generate_branches(decision: str) -> list[dict[str, Any]]:
    if not OPENAI_KEY:
        return FALLBACK_BRANCHES

    system_prompt = """
أنت كاتب تجربة سردية عربية ساحرة اسمها بوابة الاحتمالات. لا تدّعي معرفة المستقبل ولا تقدّم نصيحة حاسمة.
حوّل قرار المستخدم إلى ثلاثة مسارات تخيلية مختلفة: الجريء، الآمن، والغريب.
أعد JSON صالحًا فقط بهذا الشكل:
{"branches":[{"title":"...","mood":"...","text":"...","first_step":"..."}, ...]}
كل نص بين 35 و70 كلمة، دافئ ومثير للتأمل، وتجنب التخويف أو الوعود المضمونة.
""".strip()
    payload = {
        "model": OPENAI_MODEL,
        "temperature": 0.9,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"القرار أو السؤال: {decision}"},
        ],
    }
    try:
        async with httpx.AsyncClient(timeout=45) as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {OPENAI_KEY}"},
                json=payload,
            )
            response.raise_for_status()
            raw = response.json()["choices"][0]["message"]["content"]
            parsed = json.loads(raw)
            branches = parsed.get("branches", [])
            if len(branches) >= 3:
                return branches[:3]
    except Exception:
        LOGGER.exception("AI generation failed; using fallback branches")
    return FALLBACK_BRANCHES


def branch_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("⚡ الجريء", callback_data="choose:0")],
            [InlineKeyboardButton("🛡 الآمن", callback_data="choose:1")],
            [InlineKeyboardButton("🌀 الغريب", callback_data="choose:2")],
        ]
    )


def format_branches(decision: str, branches: list[dict[str, Any]]) -> str:
    lines = [
        "🪞 بوابة الاحتمالات فتحت...",
        "",
        f"قرارك: «{decision}»",
        "",
        "لا يوجد هنا مستقبل مؤكد. هناك ثلاث حكايات يمكنك اختبارها:",
        "",
    ]
    icons = ["⚡", "🛡", "🌀"]
    for index, branch in enumerate(branches[:3]):
        lines.extend(
            [
                f"{icons[index]} {branch.get('title', 'مسار مجهول')}",
                f"{branch.get('mood', '')}",
                f"{branch.get('text', '')}",
                "",
            ]
        )
    lines.append("اختر مسارًا، وسأريك المشهد الأول منه:")
    return "\n".join(lines)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "مرحبًا بك في 🪞 بوابة الاحتمالات.\n\n"
        "اكتب قرارًا يحيرك أو سؤالًا يطاردك، مثل: «هل أبدأ مشروعي؟»\n"
        "وسأفتح لك ثلاثة عوالم بديلة: الجريء، الآمن، والغريب.\n\n"
        "هذه تجربة تخيلية للتأمل وليست تنبؤًا بالمستقبل."
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "أرسل أي قرار أو سؤال في رسالة واحدة.\n"
        "استخدم /start للبداية و /reset لمسح آخر بوابة.\n\n"
        "كلما كان السؤال صادقًا ومحددًا، كانت الحكاية أعمق."
    )


async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    with db() as connection:
        connection.execute("DELETE FROM sessions WHERE user_id = ?", (update.effective_user.id,))
    await update.message.reply_text("أُغلقت البوابة القديمة. أرسل قرارًا جديدًا لفتح بوابة أخرى.")


async def decision_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    decision = (update.message.text or "").strip()
    if len(decision) < 4:
        await update.message.reply_text("اكتب قرارًا أو سؤالًا أطول قليلًا، حتى أستطيع بناء العوالم الثلاثة.")
        return
    if len(decision) > 1200:
        await update.message.reply_text("اختصر القرار إلى 1200 حرف كي أستطيع تحويله إلى مشهد واضح.")
        return

    await update.message.reply_text("أستمع إلى الاحتمالات... 🕯")
    branches = await generate_branches(decision)
    save_session(update.effective_user.id, decision, branches)
    await update.message.reply_text(format_branches(decision, branches), reply_markup=branch_keyboard())


async def choose_branch(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    try:
        index = int(query.data.split(":", 1)[1])
    except (ValueError, IndexError):
        await query.edit_message_text("انقطعت خيوط البوابة. أرسل قرارًا جديدًا للبدء من جديد.")
        return

    session = get_session(query.from_user.id)
    if not session:
        await query.edit_message_text("لا أجد بوابة مفتوحة لك. أرسل قرارًا جديدًا أولًا.")
        return
    branches = json.loads(session["branches"])
    if index not in range(len(branches)):
        await query.edit_message_text("هذا المسار اختفى في الضباب. جرّب قرارًا جديدًا.")
        return

    select_branch(query.from_user.id, index)
    branch = branches[index]
    text = (
        f"{branch.get('title', 'المسار')} فتح بابه.\n\n"
        f"{branch.get('text', '')}\n\n"
        f"🎒 أول أثر في هذا العالم: {branch.get('first_step', '')}\n\n"
        "نفّذ الخطوة أو تجاهلها. في الحالتين، أنت من يكتب النهاية."
    )
    await query.edit_message_text(text)
    await query.message.reply_text("أرسل قرارًا آخر عندما تريد فتح بوابة جديدة.")


def main() -> None:
    if not TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is required")
    init_db()
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("reset", reset))
    application.add_handler(CallbackQueryHandler(choose_branch, pattern=r"^choose:"))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, decision_message))
    LOGGER.info("Possibilities bot is running")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
