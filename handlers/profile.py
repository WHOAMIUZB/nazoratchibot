from aiogram import Router, F
from aiogram.types import Message

import database as db
from locales import t
from keyboards import books_list_kb

router = Router()


@router.message(F.text.in_({"👤 Profil", "👤 Профиль", "👤 Profile"}))
async def show_profile(message: Message):
    lang = await db.get_language(message.from_user.id)
    user = await db.get_user(message.from_user.id)
    favorites = await db.list_favorites(message.from_user.id)
    read_books = await db.get_shelf(message.from_user.id, "read")
    text = t(
        "profile_text", lang,
        name=message.from_user.first_name, language=lang.upper(),
        xp=user["xp"], fav_count=len(favorites), read_count=len(read_books),
    )
    await message.answer(text)


@router.message(F.text.in_({"⭐ Sevimlilar", "⭐ Избранное", "⭐ Favorites"}))
async def show_favorites(message: Message):
    lang = await db.get_language(message.from_user.id)
    favorites = await db.list_favorites(message.from_user.id)
    if not favorites:
        await message.answer(t("favorites_empty", lang))
        return
    await message.answer(t("search_results", lang, count=len(favorites)), reply_markup=books_list_kb(favorites, lang))


@router.message(F.text.in_({"🕘 Tarix", "🕘 История", "🕘 History"}))
async def show_history(message: Message):
    lang = await db.get_language(message.from_user.id)
    history = await db.get_history(message.from_user.id)
    if not history:
        await message.answer(t("history_empty", lang))
        return
    lines = []
    for h in history:
        if h["book_id"]:
            lines.append(f"• {h['action']} — {h['title']} ({h['author'] or '—'})")
        else:
            lines.append(f"• {h['action']}")
    await message.answer("\n".join(lines))


@router.message(F.text.in_({"📖 Kutubxonam", "📖 Моя библиотека", "📖 My Library"}))
async def show_library(message: Message):
    lang = await db.get_language(message.from_user.id)
    reading = await db.get_shelf(message.from_user.id, "reading")
    read = await db.get_shelf(message.from_user.id, "read")
    planned = await db.get_shelf(message.from_user.id, "planned")

    labels = {
        "uz": ("📗 O‘qilmoqda", "✅ O‘qib bo‘lingan", "🕓 Rejadagi"),
        "ru": ("📗 Читаю", "✅ Прочитано", "🕓 В планах"),
        "en": ("📗 Reading", "✅ Read", "🕓 Planned"),
    }[lang]

    parts = []
    for label, items in zip(labels, (reading, read, planned)):
        parts.append(f"<b>{label}</b> ({len(items)})")
        for b in items[:10]:
            parts.append(f"  • {b['title']}")
    await message.answer("\n".join(parts) if parts else t("favorites_empty", lang))
