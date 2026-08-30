import asyncio
from datetime import datetime, timezone

from aiogram import Bot

import database as db
from locales import t


async def reminder_loop(bot: Bot):
    """Har daqiqada tekshiradi va foydalanuvchi belgilagan vaqtda eslatma yuboradi."""
    sent_today = set()
    last_day = None
    while True:
        now = datetime.now(timezone.utc)
        if last_day != now.date():
            sent_today = set()
            last_day = now.date()
        users = await db.users_with_reminder()
        for u in users:
            key = (u["user_id"], now.date())
            if key in sent_today:
                continue
            if u["reminder_hour"] == now.hour and u["reminder_minute"] == now.minute:
                lang = await db.get_language(u["user_id"])
                try:
                    await bot.send_message(u["user_id"], t("reminder_text", lang))
                except Exception:
                    pass
                sent_today.add(key)
        await asyncio.sleep(60)


async def new_book_notify(bot: Bot, book_id: int, genre_id: int):
    """Janrga obuna bo'lgan foydalanuvchilarga yangi kitob haqida xabar."""
    book = await db.get_book(book_id)
    if not book:
        return
    subscribers = await db.genre_subscribers(genre_id)
    for uid in subscribers:
        lang = await db.get_language(uid)
        try:
            await bot.send_message(uid, f"🆕 Yangi kitob: <b>{book['title']}</b> — {book['author'] or ''}")
        except Exception:
            pass


async def weekly_digest_loop(bot: Bot):
    """Har dushanba kuni 09:00 UTC da haftalik eng yaxshi kitoblar haqida xabar."""
    last_sent_week = None
    while True:
        now = datetime.now(timezone.utc)
        iso_year, iso_week, iso_weekday = now.isocalendar()
        if iso_weekday == 1 and now.hour == 9 and now.minute == 0 and last_sent_week != (iso_year, iso_week):
            top = await db.top_books(5)
            if top:
                lines = "\n".join(f"{i+1}. {b['title']} — {b['author'] or ''}" for i, b in enumerate(top))
                users = await db.all_user_ids()
                for uid in users:
                    try:
                        await bot.send_message(uid, f"📬 Haftalik dayjest — eng yaxshi kitoblar:\n\n{lines}")
                    except Exception:
                        pass
            last_sent_week = (iso_year, iso_week)
        await asyncio.sleep(60)
