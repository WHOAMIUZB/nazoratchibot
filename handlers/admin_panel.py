import asyncio
import time
from aiogram import Router, F, Bot
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest

import database as db
import keyboards as kb

router = Router(name="admin_panel")


async def _guard(callback: CallbackQuery) -> bool:
    if not await db.is_bot_admin(callback.from_user.id):
        await callback.answer("⛔️ Sizda ruxsat yo'q.", show_alert=True)
        return False
    return True


class Broadcast(StatesGroup):
    waiting_content = State()


class AdminManage(StatesGroup):
    waiting_add_id = State()
    waiting_remove_id = State()


@router.callback_query(F.data == "admin_panel")
async def open_admin_panel(callback: CallbackQuery):
    if not await _guard(callback):
        return
    await callback.message.edit_text("🛠 <b>Admin panel</b>", reply_markup=kb.admin_panel_kb())
    await callback.answer()


@router.callback_query(F.data == "adm_stats")
async def adm_stats(callback: CallbackQuery):
    if not await _guard(callback):
        return
    users_count = await db.count_users()
    groups = await db.all_groups()
    channels = await db.all_channels()
    text = (
        "📊 <b>Umumiy statistika</b>\n\n"
        f"👤 Bot foydalanuvchilari: <b>{users_count}</b>\n"
        f"👥 Ulangan guruhlar: <b>{len(groups)}</b>\n"
        f"📡 Ulangan kanallar: <b>{len(channels)}</b>\n"
    )
    await callback.message.edit_text(text, reply_markup=kb.back_kb("admin_panel"))
    await callback.answer()


@router.callback_query(F.data == "adm_groups")
async def adm_groups(callback: CallbackQuery, bot: Bot):
    if not await _guard(callback):
        return
    groups = await db.all_groups()
    if not groups:
        text = "👥 Hozircha ulangan guruhlar yo'q."
    else:
        lines = ["👥 <b>Guruhlar ro'yxati:</b>\n"]
        for g in groups:
            try:
                count = await bot.get_chat_member_count(g["group_id"])
            except Exception:
                count = "?"
            lines.append(f"• {g['title']} — <b>{count}</b> a'zo")
        text = "\n".join(lines)
    await callback.message.edit_text(text, reply_markup=kb.back_kb("admin_panel"))
    await callback.answer()


@router.callback_query(F.data == "adm_channels")
async def adm_channels(callback: CallbackQuery, bot: Bot):
    if not await _guard(callback):
        return
    channels = await db.all_channels()
    if not channels:
        text = "📡 Hozircha ulangan kanallar yo'q."
    else:
        lines = ["📡 <b>Kanallar ro'yxati:</b>\n"]
        for c in channels:
            try:
                count = await bot.get_chat_member_count(c["channel_id"])
            except Exception:
                count = "?"
            lines.append(f"• {c['title']} — <b>{count}</b> obunachi")
        text = "\n".join(lines)
    await callback.message.edit_text(text, reply_markup=kb.back_kb("admin_panel"))
    await callback.answer()


# ---------------- Admin qo'shish / olish ----------------

@router.callback_query(F.data == "adm_add_admin")
async def adm_add_admin(callback: CallbackQuery, state: FSMContext):
    if not await _guard(callback):
        return
    await state.set_state(AdminManage.waiting_add_id)
    await callback.message.edit_text(
        "➕ Yangi admin qo'shish uchun foydalanuvchining Telegram ID raqamini yuboring.\n\n"
        "(ID ni bilish uchun foydalanuvchi botga /start yozgan bo'lishi kerak, yoki @userinfobot orqali bilib olishingiz mumkin)",
        reply_markup=kb.back_kb("admin_panel"),
    )
    await callback.answer()


@router.message(StateFilter(AdminManage.waiting_add_id))
async def process_add_admin(message: Message, state: FSMContext):
    if not await db.is_bot_admin(message.from_user.id):
        return
    if not message.text or not message.text.strip().isdigit():
        await message.answer("ℹ️ Faqat raqamli ID yuboring.")
        return
    new_admin_id = int(message.text.strip())
    await db.add_bot_admin(new_admin_id, message.from_user.id)
    await state.clear()
    await message.answer(f"✅ <code>{new_admin_id}</code> endi bot admini.", reply_markup=kb.admin_panel_kb())


@router.callback_query(F.data == "adm_remove_admin")
async def adm_remove_admin(callback: CallbackQuery, state: FSMContext):
    if not await _guard(callback):
        return
    admins = await db.list_bot_admins()
    text = "➖ Adminlikdan olib tashlash uchun ID yuboring.\n\nHozirgi adminlar:\n" + "\n".join(f"• <code>{a}</code>" for a in admins)
    await state.set_state(AdminManage.waiting_remove_id)
    await callback.message.edit_text(text, reply_markup=kb.back_kb("admin_panel"))
    await callback.answer()


@router.message(StateFilter(AdminManage.waiting_remove_id))
async def process_remove_admin(message: Message, state: FSMContext):
    if not await db.is_bot_admin(message.from_user.id):
        return
    if not message.text or not message.text.strip().isdigit():
        await message.answer("ℹ️ Faqat raqamli ID yuboring.")
        return
    target_id = int(message.text.strip())
    from config import SUPER_ADMIN_ID
    if target_id == SUPER_ADMIN_ID:
        await message.answer("⛔️ Bosh adminni olib tashlab bo'lmaydi.")
        return
    await db.remove_bot_admin(target_id)
    await state.clear()
    await message.answer(f"✅ <code>{target_id}</code> adminlikdan olindi.", reply_markup=kb.admin_panel_kb())


# ---------------- Broadcast ----------------

@router.callback_query(F.data == "adm_broadcast")
async def adm_broadcast(callback: CallbackQuery):
    if not await _guard(callback):
        return
    await callback.message.edit_text(
        "📢 Xabarni kimga yubormoqchisiz?", reply_markup=kb.broadcast_target_kb()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("bc_target:"))
async def bc_target(callback: CallbackQuery, state: FSMContext):
    if not await _guard(callback):
        return
    target = callback.data.split(":")[1]
    await state.update_data(bc_target=target)
    await state.set_state(Broadcast.waiting_content)
    label = {"users": "foydalanuvchilarga", "groups": "guruhlarga", "channels": "kanallarga"}[target]
    await callback.message.edit_text(
        f"✍️ Endi {label} yuboriladigan xabarni menga yuboring (matn, rasm, video — istalgan turdagi xabar bo'lishi mumkin).",
        reply_markup=kb.back_kb("admin_panel"),
    )
    await callback.answer()


@router.message(StateFilter(Broadcast.waiting_content))
async def process_broadcast(message: Message, state: FSMContext, bot: Bot):
    if not await db.is_bot_admin(message.from_user.id):
        return
    data = await state.get_data()
    target = data.get("bc_target")
    await state.clear()

    if target == "users":
        ids = await db.all_user_ids()
    elif target == "groups":
        ids = [g["group_id"] for g in await db.all_groups()]
    else:
        ids = [c["channel_id"] for c in await db.all_channels()]

    status_msg = await message.answer(f"⏳ Yuborilmoqda... (0/{len(ids)})")
    sent, failed = 0, 0
    for i, chat_id in enumerate(ids, start=1):
        try:
            await message.copy_to(chat_id)
            sent += 1
        except (TelegramForbiddenError, TelegramBadRequest):
            failed += 1
        except Exception:
            failed += 1
        if i % 25 == 0:
            try:
                await status_msg.edit_text(f"⏳ Yuborilmoqda... ({i}/{len(ids)})")
            except Exception:
                pass
        await asyncio.sleep(0.05)  # Telegram flood-limitiga tushmaslik uchun

    async with db.get_db() as conn:
        await conn.execute(
            "INSERT INTO broadcast_log (admin_id, target_type, sent_count, failed_count, ts) VALUES (?, ?, ?, ?, ?)",
            (message.from_user.id, target, sent, failed, int(time.time())),
        )
        await conn.commit()

    await status_msg.edit_text(
        f"✅ Xabar yuborish yakunlandi.\n\n📤 Yuborildi: <b>{sent}</b>\n❌ Xatolik: <b>{failed}</b>",
    )
    await message.answer("🛠 <b>Admin panel</b>", reply_markup=kb.admin_panel_kb())
