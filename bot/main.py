"""Job Tracker Bot: кидаєш вакансію, ШІ розбирає її в JSON, запис іде в Supabase."""
import asyncio
import hashlib
import logging
from html import escape

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ChatAction, ParseMode
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

import config
from ai import AIError, Gemini
from db import DB
from scrape import URL_RE, fetch_page_text

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
)
logging.getLogger("httpx").setLevel(logging.WARNING)  # не світити URL з токеном у логах
log = logging.getLogger("bot")

STATUS_LABELS = {
    "new": "🆕 Нова",
    "applied": "📨 Відгукнувся",
    "interview": "🎤 Співбесіда",
    "rejected": "❌ Відмова",
}
MIN_VACANCY_CHARS = 200

db = DB(config.SUPABASE_URL, config.SUPABASE_KEY)
ai = Gemini(config.GEMINI_API_KEY, config.GEMINI_MODEL)


def allowed(update: Update) -> bool:
    user = update.effective_user
    return not config.ALLOWED_USER_IDS or (user and user.id in config.ALLOWED_USER_IDS)


def keyboard(vacancy_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("Відгукнувся", callback_data=f"st:{vacancy_id}:applied"),
                InlineKeyboardButton("Співбесіда", callback_data=f"st:{vacancy_id}:interview"),
                InlineKeyboardButton("Відмова", callback_data=f"st:{vacancy_id}:rejected"),
            ],
            [InlineKeyboardButton("🎯 Match зі стеком", callback_data=f"match:{vacancy_id}")],
        ]
    )


def summary(v: dict) -> str:
    def val(x):
        return escape(str(x)) if x else "—"

    lines = [
        f"<b>#{v['id']} {val(v.get('role'))}</b>",
        f"🏢 {val(v.get('company'))}",
        f"🛠 {val(', '.join(v.get('stack') or []))}",
        f"💰 {val(v.get('salary'))}",
        f"📍 {val(v.get('work_format'))} · {val(v.get('level'))}",
        f"Статус: {STATUS_LABELS.get(v['status'], v['status'])}",
    ]
    if v.get("url"):
        lines.append(f"🔗 {escape(v['url'])}")
    return "\n".join(lines)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not allowed(update):
        await update.effective_message.reply_text(
            f"Це приватний бот. Твій Telegram ID: {update.effective_user.id}"
        )
        return
    await update.effective_message.reply_text(
        "Кинь текст вакансії або посилання на неї, і я збережу її.\n\n"
        "/list — останні вакансії\n"
        "/stats — відгуки, співбесіди, відмови\n"
        "/match [id] — порівняти вакансію з твоїм стеком\n\n"
        f"Твій Telegram ID: {update.effective_user.id}"
    )


async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not allowed(update):
        return
    msg = update.effective_message
    text = msg.text.strip()
    await msg.chat.send_action(ChatAction.TYPING)

    found = URL_RE.search(text)
    url = found.group(0) if found else None
    # Якщо крім посилання тексту майже немає, беремо текст зі сторінки.
    if url and len(text) - len(url) < MIN_VACANCY_CHARS:
        try:
            text = await fetch_page_text(url)
        except Exception as e:
            log.warning("Не відкрилося посилання %s: %s", url, e)
            text = ""
        if len(text) < MIN_VACANCY_CHARS:
            await msg.reply_text(
                "Не вдалося прочитати сторінку (сайт може вимагати вхід). "
                "Скопіюй сюди текст вакансії."
            )
            return
    elif len(text) < 50:
        await msg.reply_text("Замало тексту. Кинь повний текст вакансії або посилання.")
        return

    try:
        fields = await ai.extract_vacancy(text)
        vacancy = await db.add(
            {**fields, "user_id": update.effective_user.id, "url": url, "raw_text": text}
        )
    except AIError as e:
        log.error("Gemini: %s", e)
        await msg.reply_text("ШІ не зміг розібрати вакансію. Спробуй ще раз.")
        return
    except Exception:
        log.exception("Не вдалося зберегти вакансію")
        await msg.reply_text("Помилка збереження. Спробуй пізніше.")
        return

    await msg.reply_text(
        summary(vacancy),
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard(vacancy["id"]),
        disable_web_page_preview=True,
    )


async def on_status_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not allowed(update):
        await query.answer()
        return
    _, vacancy_id, status = query.data.split(":")
    try:
        vacancy = await db.set_status(update.effective_user.id, int(vacancy_id), status)
    except Exception:
        log.exception("Не вдалося оновити статус")
        await query.answer("Помилка, спробуй ще раз", show_alert=True)
        return
    if not vacancy:
        await query.answer("Вакансію не знайдено", show_alert=True)
        return
    await query.answer(STATUS_LABELS[status])
    new_text = summary(vacancy)
    if query.message and query.message.text_html != new_text:
        try:
            await query.edit_message_text(
                new_text,
                parse_mode=ParseMode.HTML,
                reply_markup=keyboard(vacancy["id"]),
                disable_web_page_preview=True,
            )
        except Exception as e:  # "message is not modified" тощо
            log.debug("edit_message_text: %s", e)


async def cmd_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not allowed(update):
        return
    rows = await db.recent(update.effective_user.id)
    if not rows:
        await update.effective_message.reply_text("Поки порожньо. Кинь першу вакансію.")
        return
    lines = [
        f"<b>#{r['id']}</b> {escape(r.get('role') or '—')} · {escape(r.get('company') or '—')}"
        f" — {STATUS_LABELS.get(r['status'], r['status'])}"
        for r in rows
    ]
    await update.effective_message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)


async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not allowed(update):
        return
    c = await db.status_counts(update.effective_user.id)
    total = sum(c.values())
    # Співбесіда чи відмова означають, що відгук уже був.
    responded = c["applied"] + c["interview"] + c["rejected"]
    await update.effective_message.reply_text(
        f"Усього вакансій: {total}\n"
        f"📨 Відгуків: {responded}\n"
        f"🎤 Співбесід: {c['interview']}\n"
        f"❌ Відмов: {c['rejected']}\n"
        f"⏳ Чекають відповіді: {c['applied']}\n"
        f"🆕 Ще без відгуку: {c['new']}"
    )


async def send_match(update: Update, vacancy_id: int | None) -> None:
    msg = update.effective_message
    if not config.MY_STACK:
        await msg.reply_text("Задай свій стек в env-змінній MY_STACK, наприклад: Python, SQL, React")
        return
    vacancy = await db.get(update.effective_user.id, vacancy_id)
    if not vacancy:
        await msg.reply_text("Вакансію не знайдено.")
        return
    await msg.chat.send_action(ChatAction.TYPING)
    try:
        m = await ai.match(vacancy, config.MY_STACK)
    except AIError as e:
        log.error("Gemini: %s", e)
        await msg.reply_text("ШІ не відповів. Спробуй ще раз.")
        return
    await msg.reply_text(
        f"<b>#{vacancy['id']} {escape(vacancy.get('role') or '—')}</b>: "
        f"збіг {m['match_percent']}%\n"
        f"✅ Є: {escape(', '.join(m['matched']) or '—')}\n"
        f"❗ Бракує: {escape(', '.join(m['missing']) or 'нічого')}\n\n"
        f"{escape(m['advice'])}",
        parse_mode=ParseMode.HTML,
    )


async def cmd_match(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not allowed(update):
        return
    vacancy_id = None
    if context.args:
        arg = context.args[0].lstrip("#")
        if not arg.isdigit():
            await update.effective_message.reply_text("Формат: /match або /match 12")
            return
        vacancy_id = int(arg)
    await send_match(update, vacancy_id)


async def on_match_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if allowed(update):
        await send_match(update, int(query.data.split(":")[1]))


async def on_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    log.exception("Помилка в обробнику", exc_info=context.error)


async def on_shutdown(app: Application) -> None:
    await db.close()
    await ai.close()


def main() -> None:
    app = (
        Application.builder()
        .token(config.TELEGRAM_TOKEN)
        .post_shutdown(on_shutdown)
        .build()
    )
    app.add_handler(CommandHandler(["start", "help"], cmd_start))
    app.add_handler(CommandHandler("list", cmd_list))
    app.add_handler(CommandHandler("stats", cmd_stats))
    app.add_handler(CommandHandler("match", cmd_match))
    app.add_handler(CallbackQueryHandler(on_status_button, pattern=r"^st:\d+:\w+$"))
    app.add_handler(CallbackQueryHandler(on_match_button, pattern=r"^match:\d+$"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))
    app.add_error_handler(on_error)

    asyncio.set_event_loop(asyncio.new_event_loop())  # Python 3.14 не створює цикл сам
    if config.WEBHOOK_URL:
        log.info("Режим webhook: %s", config.WEBHOOK_URL)
        app.run_webhook(
            listen="0.0.0.0",
            port=config.PORT,
            url_path="telegram",
            webhook_url=f"{config.WEBHOOK_URL}/telegram",
            secret_token=hashlib.sha256(config.TELEGRAM_TOKEN.encode()).hexdigest()[:32],
        )
    else:
        log.info("Режим polling")
        app.run_polling()


if __name__ == "__main__":
    main()
