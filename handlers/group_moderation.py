import time
from aiogram import Router, F, Bot
from aiogram.filters import Command, CommandObject
from aiogram.types import Message
from aiogram.enums import ChatType

import database as db
from utils import restrict_user, unrestrict_user, human_delta, today_str, is_group_admin, user_mention
from config import WARN_LIMIT, WARN_BAN_DAYS, LINK_LIMIT_PER_DAY, LINK_MUTE_HOURS

router = Router(name="group_moderation")
router.message.filter(F.chat.type.in_({ChatType.GROUP, ChatType.SUPERGROUP}))


async def _require_admin_and_reply(message: Message, bot: Bot) -> bool:
    """Buyruq guruh admini tomonidan va reply tarzida yuborilganini tekshiradi."""
    if not await is_group_admin(bot, message.chat.id, message.from_user.id):
        await message.reply("⛔️ Bu buyruqni faqat guruh adminlari ishlata oladi.")
        return False
    if not message.reply_to_message:
        await message.reply("ℹ️ Bu buyruqni kerakli foydalanuvchi xabariga <b>javoban (reply)</b> yuboring.")
        return False
    return True


# ---------------- /warn ----------------

@router.message(Command("warn"))
async def cmd_warn(message: Message, bot: Bot):
    if not await _require_admin_and_reply(message, bot):
        return
    target = message.reply_to_message.from_user
    if target.is_bot:
        await message.reply("Botlarga ogohlantirish berib bo'lmaydi.")
        return

    try:
        await message.reply_to_message.delete()
    except Exception:
        pass

    count = await db.add_warning(message.chat.id, target.id)

    if count >= WARN_LIMIT:
        until_ts = int(time.time()) + WARN_BAN_DAYS * 86400
        try:
            await restrict_user(bot, message.chat.id, target.id, until_ts)
        except Exception:
            pass
        await db.reset_warnings(message.chat.id, target.id)
        await message.answer(
            f"🚫 {user_mention(target.id, target.full_name)} {WARN_LIMIT}/{WARN_LIMIT} ogohlantirish oldi "
            f"va <b>{WARN_BAN_DAYS} kunga</b> yoza olmaydigan qilib qo'yildi.",
        )
    else:
        await message.answer(
            f"⚠️ {user_mention(target.id, target.full_name)} ogohlantirildi. "
            f"Ogohlantirishlar: <b>{count}/{WARN_LIMIT}</b>",
        )


# ---------------- /mute ----------------

@router.message(Command("mute"))
async def cmd_mute(message: Message, bot: Bot, command: CommandObject):
    if not await _require_admin_and_reply(message, bot):
        return
    target = message.reply_to_message.from_user
    if target.is_bot:
        await message.reply("Botlarni mute qilib bo'lmaydi.")
        return

    hours = 1
    if command.args:
        try:
            hours = max(1, int(command.args.strip().split()[0]))
        except ValueError:
            await message.reply("ℹ️ To'g'ri format: <code>/mute 3</code> (3 soatga mute qiladi)")
            return

    try:
        await message.reply_to_message.delete()
    except Exception:
        pass

    until_ts = int(time.time()) + hours * 3600
    await restrict_user(bot, message.chat.id, target.id, until_ts)
    await db.set_mute(message.chat.id, target.id, until_ts, "admin buyrug'i")
    await message.answer(
        f"🔇 {user_mention(target.id, target.full_name)} <b>{hours} soatga</b> mute qilindi."
    )


# ---------------- /ban ----------------

@router.message(Command("ban"))
async def cmd_ban(message: Message, bot: Bot):
    if not await _require_admin_and_reply(message, bot):
        return
    target = message.reply_to_message.from_user
    if target.is_bot:
        await message.reply("Botlarni ban qilib bo'lmaydi.")
        return

    try:
        await message.reply_to_message.delete()
    except Exception:
        pass

    await bot.ban_chat_member(message.chat.id, target.id)
    await db.reset_warnings(message.chat.id, target.id)
    await db.clear_mute(message.chat.id, target.id)
    await message.answer(f"⛔️ {user_mention(target.id, target.full_name)} guruhdan bloklandi (ban).")


# ---------------- /unmute ----------------

@router.message(Command("unmute"))
async def cmd_unmute(message: Message, bot: Bot):
    if not await is_group_admin(bot, message.chat.id, message.from_user.id):
        await message.reply("⛔️ Bu buyruqni faqat guruh adminlari ishlata oladi.")
        return
    if not message.reply_to_message:
        await message.reply("ℹ️ Bu buyruqni kerakli foydalanuvchi xabariga javoban yuboring.")
        return

    target = message.reply_to_message.from_user
    await unrestrict_user(bot, message.chat.id, target.id)
    await db.clear_mute(message.chat.id, target.id)
    await db.reset_warnings(message.chat.id, target.id)
    await db.clear_odam(message.chat.id, target.id)
    await message.answer(
        f"✅ {user_mention(target.id, target.full_name)} uchun barcha cheklov va ogohlantirishlar bekor qilindi."
    )


# ---------------- /forward ----------------

@router.message(Command("forward"))
async def cmd_forward(message: Message, bot: Bot):
    if not await is_group_admin(bot, message.chat.id, message.from_user.id):
        await message.reply("⛔️ Bu buyruqni faqat guruh adminlari ishlata oladi.")
        return
    group = await db.get_group(message.chat.id)
    new_val = 0 if group and group["forward_locked"] else 1
    await db.set_group_field(message.chat.id, "forward_locked", new_val)
    if new_val:
        await message.answer("🚫 Endi guruhga <b>uzatilgan (forward) xabarlar</b> taqiqlandi.")
    else:
        await message.answer("✅ Guruhga uzatilgan (forward) xabarlarni yuborishga ruxsat berildi.")


# ---------------- /link ----------------

@router.message(Command("link"))
async def cmd_link(message: Message, bot: Bot):
    if not await is_group_admin(bot, message.chat.id, message.from_user.id):
        await message.reply("⛔️ Bu buyruqni faqat guruh adminlari ishlata oladi.")
        return
    group = await db.get_group(message.chat.id)
    new_val = 0 if group and group["link_lock_enabled"] else 1
    await db.set_group_field(message.chat.id, "link_lock_enabled", new_val)
    if new_val:
        await message.answer(
            f"🚫 Havola yuborish cheklandi. Kuniga <b>{LINK_LIMIT_PER_DAY} marta</b> dan ortiq havola "
            f"yuborgan foydalanuvchi <b>{LINK_MUTE_HOURS} soatga</b> mute qilinadi."
        )
    else:
        await message.answer("✅ Havola yuborish cheklovi olib tashlandi.")


# ---------------- /salom ----------------

@router.message(Command("salom"))
async def cmd_salom(message: Message, bot: Bot):
    if not await is_group_admin(bot, message.chat.id, message.from_user.id):
        await message.reply("⛔️ Bu buyruqni faqat guruh adminlari ishlata oladi.")
        return
    group = await db.get_group(message.chat.id)
    new_val = 0 if group and group["salom_enabled"] else 1
    await db.set_group_field(message.chat.id, "salom_enabled", new_val)
    await message.answer("✅ Yangi a'zolar bilan salomlashish yoqildi." if new_val else "❌ Salomlashish o'chirildi.")


# ---------------- /tozala ----------------

@router.message(Command("tozala"))
async def cmd_tozala(message: Message, bot: Bot):
    if not await is_group_admin(bot, message.chat.id, message.from_user.id):
        await message.reply("⛔️ Bu buyruqni faqat guruh adminlari ishlata oladi.")
        return
    group = await db.get_group(message.chat.id)
    new_val = 0 if group and group["tozala_enabled"] else 1
    await db.set_group_field(message.chat.id, "tozala_enabled", new_val)
    await message.answer(
        "✅ \"Guruhga qo'shildi\" xabarlarini avtomatik tozalash yoqildi." if new_val
        else "❌ Avtomatik tozalash o'chirildi."
    )


# ---------------- /odam ----------------

@router.message(Command("odam"))
async def cmd_odam(message: Message, bot: Bot):
    if not await _require_admin_and_reply(message, bot):
        return
    target = message.reply_to_message.from_user
    # /odam buyrug'i son bilan yuboriladi, lekin talab reply qilingan foydalanuvchiga qo'yiladi
    parts = message.text.split()
    if len(parts) < 2 or not parts[1].isdigit():
        await message.reply("ℹ️ To'g'ri format: kerakli foydalanuvchi xabariga reply qilib <code>/odam 5</code> "
                             "(5 kishi qo'shmaguncha yoza olmaydi)")
        return
    required = int(parts[1])
    await db.set_odam_requirement(message.chat.id, target.id, required)
    try:
        await restrict_user(bot, message.chat.id, target.id, None)
    except Exception:
        pass
    await message.answer(
        f"👥 {user_mention(target.id, target.full_name)} guruhga kamida <b>{required} kishi</b> "
        f"qo'shmaguncha yoza olmaydi."
    )


# ============ Avtomatik nazorat (har bir xabarda ishlaydi) ============

@router.message(F.new_chat_members)
async def new_members_handler(message: Message, bot: Bot):
    group = await db.get_group(message.chat.id)
    if not group:
        await db.upsert_group(message.chat.id, message.chat.title)
        group = await db.get_group(message.chat.id)

    if group and group["tozala_enabled"]:
        try:
            await message.delete()
        except Exception:
            pass
        # tozala yoqilgan bo'lsa, salom xabari alohida (chiroyli) yuboriladi (agar yoqilgan bo'lsa)

    if group and group["salom_enabled"]:
        names = ", ".join(user_mention(u.id, u.full_name) for u in message.new_chat_members if not u.is_bot)
        if names:
            await bot.send_message(
                message.chat.id,
                f"👋 Xush kelibsiz, {names}! Guruhimizda faol bo'lishingizni istaymiz.",
            )


@router.message(F.left_chat_member)
async def left_member_handler(message: Message, bot: Bot):
    group = await db.get_group(message.chat.id)
    if group and group["tozala_enabled"]:
        try:
            await message.delete()
        except Exception:
            pass


LINK_MARKERS = ("http://", "https://", "t.me/", "@")


def _contains_link(message: Message) -> bool:
    if message.entities:
        for e in message.entities:
            if e.type in ("url", "text_link", "mention"):
                return True
    text = message.text or message.caption or ""
    return any(marker in text for marker in LINK_MARKERS)


@router.message(F.text | F.caption | F.forward_date | F.forward_origin)
async def message_guard(message: Message, bot: Bot):
    """Forward va havola cheklovlarini bitta joyda tekshiradi (tartib muammosining oldini olish uchun)."""
    group = await db.get_group(message.chat.id)
    if not group:
        return
    if await is_group_admin(bot, message.chat.id, message.from_user.id):
        return

    # 1) Forward cheklovi
    is_forward = bool(message.forward_date or message.forward_origin)
    if group["forward_locked"] and is_forward:
        try:
            await message.delete()
        except Exception:
            pass
        return

    # 2) Havola cheklovi
    if group["link_lock_enabled"] and _contains_link(message):
        try:
            await message.delete()
        except Exception:
            pass

        count = await db.add_link_violation(message.chat.id, message.from_user.id, today_str())
        if count >= LINK_LIMIT_PER_DAY:
            until_ts = int(time.time()) + LINK_MUTE_HOURS * 3600
            await restrict_user(bot, message.chat.id, message.from_user.id, until_ts)
            await db.set_mute(message.chat.id, message.from_user.id, until_ts, "havola cheklovi")
            await message.answer(
                f"🚫 {user_mention(message.from_user.id, message.from_user.full_name)} bugun "
                f"{LINK_LIMIT_PER_DAY} martadan ortiq havola yubordi va <b>{LINK_MUTE_HOURS} soatga</b> "
                f"mute qilindi."
            )
        else:
            await message.answer(
                f"⚠️ {user_mention(message.from_user.id, message.from_user.full_name)}, guruhda havola "
                f"yuborish cheklangan. ({count}/{LINK_LIMIT_PER_DAY})"
            )
