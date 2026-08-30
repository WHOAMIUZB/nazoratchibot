from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from locales import t
from config import BOOK_CLUB_CHAT_LINK, MINIAPP_URL


def main_menu(lang: str, is_admin: bool = False) -> ReplyKeyboardMarkup:
    b = ReplyKeyboardBuilder()
    if MINIAPP_URL.startswith("https://"):
        b.button(text="🚀 Mini App orqali ochish", web_app=WebAppInfo(url=MINIAPP_URL))
    b.button(text=t("menu_search", lang))
    b.button(text=t("menu_catalog", lang))
    b.button(text=t("menu_favorites", lang))
    b.button(text=t("menu_library", lang))
    b.button(text=t("menu_top", lang))
    b.button(text=t("menu_history", lang))
    b.button(text=t("menu_quiz", lang))
    b.button(text=t("menu_promo", lang))
    b.button(text=t("menu_profile", lang))
    b.button(text=t("menu_club", lang))
    b.button(text=t("menu_feedback", lang))
    b.button(text=t("menu_settings", lang))
    if is_admin:
        b.button(text="🛠 Admin panel")
    if MINIAPP_URL.startswith("https://"):
        b.adjust(1, *([2] * 10))
    else:
        b.adjust(2)
    return b.as_markup(resize_keyboard=True)


def language_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="🇺🇿 O‘zbekcha", callback_data="lang:uz")
    b.button(text="🇷🇺 Русский", callback_data="lang:ru")
    b.button(text="🇬🇧 English", callback_data="lang:en")
    b.adjust(1)
    return b.as_markup()


def genres_kb(genres, lang: str, back_to=None) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    name_field = f"name_{lang}"
    for g in genres:
        name = g[name_field] or g["name_uz"]
        b.button(text=name, callback_data=f"genre:{g['genre_id']}")
    if back_to:
        b.button(text=t("menu_back", lang), callback_data=back_to)
    b.adjust(2)
    return b.as_markup()


def genre_subscribe_kb(genre_id: int, subscribed: bool, lang: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    labels = {
        "uz": ("🔕 Yangiliklardan chiqish", "🔔 Yangi kitoblardan xabardor bo‘lish"),
        "ru": ("🔕 Отписаться от новинок", "🔔 Уведомлять о новых книгах"),
        "en": ("🔕 Unsubscribe from updates", "🔔 Notify me about new books"),
    }[lang]
    text = labels[0] if subscribed else labels[1]
    b.button(text=text, callback_data=f"gsub:{genre_id}")
    return b.as_markup()


def books_list_kb(books, lang: str, page_prefix="book") -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for book in books:
        title = book["title"]
        if len(title) > 40:
            title = title[:37] + "..."
        b.button(text=f"📖 {title}", callback_data=f"{page_prefix}:{book['book_id']}")
    b.adjust(1)
    return b.as_markup()


def book_detail_kb(book_id: int, lang: str, is_fav: bool, has_text: bool) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    if has_text:
        b.button(text=t("btn_read_online", lang), callback_data=f"read:{book_id}:0")
    b.button(text=t("btn_download", lang), callback_data=f"download:{book_id}")
    fav_text = t("btn_remove_favorite", lang) if is_fav else t("btn_add_favorite", lang)
    b.button(text=fav_text, callback_data=f"fav:{book_id}")
    b.button(text=t("btn_rate", lang), callback_data=f"rate:{book_id}")
    b.button(text=t("btn_similar", lang), callback_data=f"similar:{book_id}")
    b.button(text=t("btn_shelf", lang), callback_data=f"shelf:{book_id}")
    b.adjust(1)
    return b.as_markup()


def reading_kb(book_id: int, page: int, total_pages: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    row = []
    if page > 0:
        b.button(text="⬅️", callback_data=f"read:{book_id}:{page-1}")
    if page < total_pages - 1:
        b.button(text="➡️", callback_data=f"read:{book_id}:{page+1}")
    b.button(text="🔙", callback_data=f"book:{book_id}")
    b.adjust(2, 1)
    return b.as_markup()


def rating_kb(book_id: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for i in range(1, 6):
        b.button(text="⭐" * i, callback_data=f"setrating:{book_id}:{i}")
    b.adjust(1)
    return b.as_markup()


def shelf_kb(book_id: int, lang: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text=t("shelf_reading", lang), callback_data=f"setshelf:{book_id}:reading")
    b.button(text=t("shelf_read", lang), callback_data=f"setshelf:{book_id}:read")
    b.button(text=t("shelf_planned", lang), callback_data=f"setshelf:{book_id}:planned")
    b.adjust(1)
    return b.as_markup()


def quiz_kb(question_id: int, options: dict) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for key, text in options.items():
        if text:
            b.button(text=text, callback_data=f"quizans:{question_id}:{key}")
    b.adjust(1)
    return b.as_markup()


def club_kb(lang: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text=t("menu_club", lang), url=BOOK_CLUB_CHAT_LINK)
    return b.as_markup()


def settings_kb(lang: str, reminder_on: bool) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="🇺🇿🇷🇺🇬🇧 " + t("menu_settings", lang), callback_data="settings:lang")
    reminder_label = t("reminder_off", lang) if reminder_on else t("reminder_on", lang)
    b.button(text=reminder_label, callback_data="settings:reminder")
    b.adjust(1)
    return b.as_markup()


# ---------- ADMIN KEYBOARDS ----------
def admin_main_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="➕ Kitob qo‘shish", callback_data="admin:addbook")
    b.button(text="✏️ Kitobni tahrirlash", callback_data="admin:editbook")
    b.button(text="🗑 Kitobni o‘chirish", callback_data="admin:delbook")
    b.button(text="📄 Onlayn o‘qish matni", callback_data="admin:settext")
    b.button(text="🖼 Muqova rasm qo‘yish", callback_data="admin:setcover")
    b.button(text="📁 Janr qo‘shish", callback_data="admin:addgenre")
    b.button(text="📢 Xabar yuborish", callback_data="admin:broadcast")
    b.button(text="🎁 Promo-kod yaratish", callback_data="admin:addpromo")
    b.button(text="❓ Viktorina savoli", callback_data="admin:addquiz")
    b.button(text="📊 Statistika", callback_data="admin:stats")
    b.button(text="💬 Fikr-mulohazalar", callback_data="admin:feedbacks")
    b.button(text="🚫 Foydalanuvchini bloklash", callback_data="admin:block")
    b.button(text="✅ Blokdan chiqarish", callback_data="admin:unblock")
    b.adjust(1)
    return b.as_markup()


def admin_back_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="⬅️ Admin menyu", callback_data="admin:menu")
    return b.as_markup()


def admin_books_list_kb(books, action: str) -> InlineKeyboardMarkup:
    """action: editsel / delsel / textsel"""
    b = InlineKeyboardBuilder()
    for book in books:
        title = book["title"]
        if len(title) > 45:
            title = title[:42] + "..."
        b.button(text=f"📖 {title}", callback_data=f"adm_{action}:{book['book_id']}")
    b.button(text="⬅️ Admin menyu", callback_data="admin:menu")
    b.adjust(1)
    return b.as_markup()


def admin_edit_fields_kb(book_id: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="📝 Nomi", callback_data=f"adm_field:{book_id}:title")
    b.button(text="✍️ Muallif", callback_data=f"adm_field:{book_id}:author")
    b.button(text="📄 Tavsif", callback_data=f"adm_field:{book_id}:description")
    b.button(text="📅 Yil", callback_data=f"adm_field:{book_id}:year")
    b.button(text="💎 Premium yoqish/o‘chirish", callback_data=f"adm_toggle:{book_id}:is_premium")
    b.button(text="🗄 Arxivlash/tiklash", callback_data=f"adm_toggle:{book_id}:is_archived")
    b.button(text="⬅️ Admin menyu", callback_data="admin:menu")
    b.adjust(1)
    return b.as_markup()


def admin_confirm_kb(action: str, ref: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="✅ Ha", callback_data=f"{action}:{ref}:yes")
    b.button(text="❌ Yo‘q", callback_data=f"{action}:{ref}:no")
    b.adjust(2)
    return b.as_markup()


def admin_users_list_kb(users, action: str) -> InlineKeyboardMarkup:
    """action: blocksel / unblocksel"""
    b = InlineKeyboardBuilder()
    for u in users:
        name = u["first_name"] or "—"
        uname = f"@{u['username']}" if u["username"] else str(u["user_id"])
        b.button(text=f"{name} ({uname})", callback_data=f"adm_{action}:{u['user_id']}")
    b.button(text="✍️ ID orqali kiritish", callback_data=f"adm_{action}manual")
    b.button(text="⬅️ Admin menyu", callback_data="admin:menu")
    b.adjust(1)
    return b.as_markup()
