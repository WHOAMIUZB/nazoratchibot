from aiogram import Router, F, Bot
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery

import database as db
import keyboards as kb

router = Router(name="start")

WELCOME = (
    "👋 Salom! Men <b>Nazoratchi</b> botiman — kanal va guruhlaringizni professional "
    "darajada boshqarish uchun yordamchi botman.\n\n"
    "📡 <b>Kanal uchun:</b> meni kanalingizga admin qilib qo'shing, so'ng \"Kanalim\" "
    "bo'limidan kerakli funksiyalarni yoqing.\n"
    "👥 <b>Guruh uchun:</b> meni guruhingizga admin qilib qo'shing — guruh adminlari "
    "maxsus buyruqlardan (/warn, /mute, /ban va h.k.) foydalana olishadi."
)


@router.message(CommandStart())
async def cmd_start(message: Message):
    await db.upsert_user(message.from_user.id, message.from_user.username, message.from_user.full_name)
    is_admin = await db.is_bot_admin(message.from_user.id)
    await message.answer(WELCOME, reply_markup=kb.main_menu(is_admin))


@router.message(Command("admin"))
async def cmd_admin(message: Message):
    if not await db.is_bot_admin(message.from_user.id):
        await message.answer("⛔️ Sizda admin panelga kirish huquqi yo'q.")
        return
    await message.answer("🛠 <b>Admin panel</b>", reply_markup=kb.admin_panel_kb())


@router.callback_query(F.data == "back_main")
async def back_main(callback: CallbackQuery):
    is_admin = await db.is_bot_admin(callback.from_user.id)
    await callback.message.edit_text(WELCOME, reply_markup=kb.main_menu(is_admin))
    await callback.answer()


@router.callback_query(F.data == "group_help")
async def group_help(callback: CallbackQuery):
    text = (
        "👥 <b>Guruh uchun buyruqlar</b> (faqat guruh adminlari uchun, xabarga reply qilib yuboriladi):\n\n"
        "🔸 /warn — ogohlantirish berish va xabarni o'chirish (3 ta ogohlantirishda 3 kunga ban)\n"
        "🔸 /mute (soat) — foydalanuvchini belgilangan soatga mute qilish\n"
        "🔸 /ban — foydalanuvchini guruhdan bloklash\n"
        "🔸 /unmute — barcha ogohlantirish/mute cheklovlarini olib tashlash\n\n"
        "<b>Guruh sozlamalari</b> (reply shart emas):\n"
        "🔸 /forward — guruhga uzatilgan (forward) xabarlarni taqiqlash/ruxsat berish\n"
        "🔸 /link — havola yuborishni cheklash/ruxsat berish (kunига 3 martadan ko'p — 2 soat mute)\n"
        "🔸 /salom — yangi qo'shilgan a'zolar bilan salomlashishni yoqish/o'chirish\n"
        "🔸 /tozala — \"foydalanuvchi guruhga qo'shildi\" xabarlarini avtomatik o'chirishni yoqish/o'chirish\n"
        "🔸 /odam (son) — belgilangan miqdorda odam qo'shmaguncha yoza olmaslik cheklovi"
    )
    await callback.message.edit_text(text, reply_markup=kb.back_kb())
    await callback.answer()


# ---------------- Kanalim ----------------

@router.callback_query(F.data == "my_channels")
async def my_channels(callback: CallbackQuery):
    channels = await db.get_user_channels(callback.from_user.id)
    if not channels:
        text = (
            "📡 Sizda hali ulangan kanal yo'q.\n\n"
            "Kanal qo'shish uchun: kanalingizga o'ting → Administratorlar → botni qidiring "
            "va uni <b>admin</b> qilib tayinlang. Bot avtomatik ravishda ro'yxatga qo'shiladi."
        )
    else:
        text = "📡 <b>Sizning kanallaringiz:</b>\n\nKerakli kanalni tanlang:"
    await callback.message.edit_text(text, reply_markup=kb.channels_list_kb(channels))
    await callback.answer()


@router.callback_query(F.data == "ch_add")
async def ch_add(callback: CallbackQuery):
    await callback.answer(
        "Kanalingizga o'ting → Administratorlar → meni admin qilib qo'shing. "
        "Bot avtomatik ravishda ro'yxatga qo'shiladi.",
        show_alert=True,
    )


@router.callback_query(F.data.startswith("ch_open:"))
async def ch_open(callback: CallbackQuery):
    channel_id = int(callback.data.split(":")[1])
    ch = await db.get_channel(channel_id)
    if not ch or ch["owner_id"] != callback.from_user.id:
        await callback.answer("Kanal topilmadi.", show_alert=True)
        return
    text = (
        f"📡 <b>{ch['title']}</b>\n\n"
        f"Quyidagi funksiyalarni yoqish yoki o'chirish uchun tugmalarni bosing:"
    )
    await callback.message.edit_text(
        text,
        reply_markup=kb.channel_detail_kb(channel_id, bool(ch["clean_deleted_enabled"]), bool(ch["stats_enabled"])),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("ch_toggle_clean:"))
async def ch_toggle_clean(callback: CallbackQuery):
    channel_id = int(callback.data.split(":")[1])
    ch = await db.get_channel(channel_id)
    if not ch or ch["owner_id"] != callback.from_user.id:
        await callback.answer("Kanal topilmadi.", show_alert=True)
        return
    new_val = await db.toggle_channel_feature(channel_id, "clean_deleted_enabled")
    ch = await db.get_channel(channel_id)
    await callback.message.edit_reply_markup(
        reply_markup=kb.channel_detail_kb(channel_id, bool(ch["clean_deleted_enabled"]), bool(ch["stats_enabled"]))
    )
    await callback.answer("✅ Yoqildi" if new_val else "❌ O'chirildi")


@router.callback_query(F.data.startswith("ch_toggle_stats:"))
async def ch_toggle_stats(callback: CallbackQuery):
    channel_id = int(callback.data.split(":")[1])
    ch = await db.get_channel(channel_id)
    if not ch or ch["owner_id"] != callback.from_user.id:
        await callback.answer("Kanal topilmadi.", show_alert=True)
        return
    new_val = await db.toggle_channel_feature(channel_id, "stats_enabled")
    ch = await db.get_channel(channel_id)
    await callback.message.edit_reply_markup(
        reply_markup=kb.channel_detail_kb(channel_id, bool(ch["clean_deleted_enabled"]), bool(ch["stats_enabled"]))
    )
    await callback.answer("✅ Yoqildi" if new_val else "❌ O'chirildi")


@router.callback_query(F.data.startswith("ch_remove:"))
async def ch_remove(callback: CallbackQuery):
    channel_id = int(callback.data.split(":")[1])
    await callback.message.edit_text(
        "❗️ Kanalni ro'yxatdan olib tashlamoqchimisiz? (Botni kanaldan admin sifatida ham "
        "olib tashlashni unutmang, aks holda u hali ham kanalda faol qoladi.)",
        reply_markup=kb.confirm_remove_kb(channel_id),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("ch_remove_confirm:"))
async def ch_remove_confirm(callback: CallbackQuery):
    channel_id = int(callback.data.split(":")[1])
    await db.remove_channel(channel_id, callback.from_user.id)
    channels = await db.get_user_channels(callback.from_user.id)
    await callback.message.edit_text(
        "✅ Kanal ro'yxatdan olib tashlandi.\n\n📡 <b>Sizning kanallaringiz:</b>",
        reply_markup=kb.channels_list_kb(channels),
    )
    await callback.answer()
