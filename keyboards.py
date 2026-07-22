from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def main_menu(is_admin: bool) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="📡 Kanalim", callback_data="my_channels")
    b.button(text="ℹ️ Guruh funksiyalari", callback_data="group_help")
    if is_admin:
        b.button(text="🛠 Admin panel", callback_data="admin_panel")
    b.adjust(1)
    return b.as_markup()


def channels_list_kb(channels: list[dict]) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for ch in channels:
        title = ch["title"] or str(ch["channel_id"])
        b.button(text=f"📡 {title}", callback_data=f"ch_open:{ch['channel_id']}")
    b.button(text="➕ Yangi kanal qo'shish", callback_data="ch_add")
    b.button(text="⬅️ Orqaga", callback_data="back_main")
    b.adjust(1)
    return b.as_markup()


def channel_detail_kb(channel_id: int, clean_on: bool, stats_on: bool) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    clean_text = "🧹 O'chirilgan hisoblarni tozalash: ✅ Yoqilgan" if clean_on else "🧹 O'chirilgan hisoblarni tozalash: ❌ O'chirilgan"
    stats_text = "📊 Statistika yuborish: ✅ Yoqilgan" if stats_on else "📊 Statistika yuborish: ❌ O'chirilgan"
    b.button(text=clean_text, callback_data=f"ch_toggle_clean:{channel_id}")
    b.button(text=stats_text, callback_data=f"ch_toggle_stats:{channel_id}")
    b.button(text="🗑 Kanalni olib tashlash", callback_data=f"ch_remove:{channel_id}")
    b.button(text="⬅️ Kanallar ro'yxatiga", callback_data="my_channels")
    b.adjust(1)
    return b.as_markup()


def confirm_remove_kb(channel_id: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="✅ Ha, olib tashlash", callback_data=f"ch_remove_confirm:{channel_id}")
    b.button(text="❌ Bekor qilish", callback_data=f"ch_open:{channel_id}")
    b.adjust(2)
    return b.as_markup()


def admin_panel_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="📢 Xabar yuborish (broadcast)", callback_data="adm_broadcast")
    b.button(text="📊 Umumiy statistika", callback_data="adm_stats")
    b.button(text="👥 Guruhlar ro'yxati", callback_data="adm_groups")
    b.button(text="📡 Kanallar ro'yxati", callback_data="adm_channels")
    b.button(text="➕ Admin qo'shish", callback_data="adm_add_admin")
    b.button(text="➖ Adminlikdan olish", callback_data="adm_remove_admin")
    b.button(text="⬅️ Orqaga", callback_data="back_main")
    b.adjust(1)
    return b.as_markup()


def broadcast_target_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="👤 Foydalanuvchilarga", callback_data="bc_target:users")
    b.button(text="👥 Guruhlarga", callback_data="bc_target:groups")
    b.button(text="📡 Kanallarga", callback_data="bc_target:channels")
    b.button(text="⬅️ Orqaga", callback_data="admin_panel")
    b.adjust(1)
    return b.as_markup()


def back_kb(callback_data: str = "back_main") -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="⬅️ Orqaga", callback_data=callback_data)
    return b.as_markup()
