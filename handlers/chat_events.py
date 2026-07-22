"""
Bot biror kanal yoki guruhga admin qilib qo'shilganda / olib tashlanganda,
shuningdek kanal/guruh a'zolari o'zgarganda ishlaydigan handlerlar.
"""
import logging
from aiogram import Router, Bot
from aiogram.types import ChatMemberUpdated
from aiogram.enums import ChatType, ChatMemberStatus
from aiogram.filters import ChatMemberUpdatedFilter, IS_NOT_MEMBER, ADMINISTRATOR

import database as db
from utils import unrestrict_user

router = Router(name="chat_events")
logger = logging.getLogger(__name__)


@router.my_chat_member(ChatMemberUpdatedFilter(member_status_changed=ADMINISTRATOR))
async def bot_promoted_to_admin(event: ChatMemberUpdated, bot: Bot):
    chat = event.chat
    added_by = event.from_user.id

    if chat.type == ChatType.CHANNEL:
        await db.add_channel(chat.id, added_by, chat.title, chat.username)
        try:
            await bot.send_message(
                added_by,
                f"✅ <b>{chat.title}</b> kanali muvaffaqiyatli qo'shildi!\n\n"
                f"Endi \"📡 Kanalim\" bo'limidan kerakli funksiyalarni yoqishingiz mumkin.",
                parse_mode="HTML",
            )
        except Exception:
            pass

    elif chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
        await db.upsert_group(chat.id, chat.title)
        try:
            await bot.send_message(
                added_by,
                f"✅ <b>{chat.title}</b> guruhi uchun bot admin etib tayinlandi.\n\n"
                f"Endi guruh adminlari quyidagi buyruqlardan foydalanishlari mumkin:\n"
                f"/warn /mute /ban /unmute /forward /link /salom /tozala /odam",
                parse_mode="HTML",
            )
        except Exception:
            pass


@router.my_chat_member(ChatMemberUpdatedFilter(member_status_changed=IS_NOT_MEMBER))
async def bot_removed(event: ChatMemberUpdated):
    chat = event.chat
    if chat.type == ChatType.CHANNEL:
        ch = await db.get_channel(chat.id)
        if ch:
            await db.remove_channel(chat.id, ch["owner_id"])


@router.chat_member()
async def channel_member_changed(event: ChatMemberUpdated, bot: Bot):
    """Kanal/guruh a'zolari sonini kuzatish uchun (statistika va o'chirilgan
    hisoblarni tozalash funksiyalari shu ma'lumotlarga tayanadi)."""
    chat = event.chat
    user = event.new_chat_member.user
    if user.is_bot:
        return

    old_status = event.old_chat_member.status
    new_status = event.new_chat_member.status

    was_member = old_status in (ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR, ChatMemberStatus.RESTRICTED)
    is_member = new_status in (ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR, ChatMemberStatus.RESTRICTED)

    if chat.type == ChatType.CHANNEL:
        if is_member and not was_member:
            await db.track_channel_member_joined(chat.id, user.id)
        elif was_member and not is_member:
            await db.track_channel_member_left(chat.id, user.id)

    elif chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
        # "odam" funksiyasi uchun: kimdir yangi a'zoni qo'shsa (invite_link orqali
        # yoki guruhga a'zo qo'shsa), taklif qiluvchi shaxsni aniqlash imkoni bo'lsa hisoblaymiz.
        if is_member and not was_member and event.from_user and event.from_user.id != user.id:
            result = await db.increment_odam_invited(chat.id, event.from_user.id)
            if result:
                invited, required = result
                if invited >= required:
                    try:
                        await unrestrict_user(bot, chat.id, event.from_user.id)
                    except Exception:
                        pass
