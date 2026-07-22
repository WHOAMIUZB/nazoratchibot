import datetime
from aiogram import Bot
from aiogram.types import ChatPermissions

FULL_PERMISSIONS = ChatPermissions(
    can_send_messages=True,
    can_send_audios=True,
    can_send_documents=True,
    can_send_photos=True,
    can_send_videos=True,
    can_send_video_notes=True,
    can_send_voice_notes=True,
    can_send_polls=True,
    can_send_other_messages=True,
    can_add_web_page_previews=True,
    can_change_info=False,
    can_invite_users=True,
    can_pin_messages=False,
)

NO_MESSAGES_PERMISSIONS = ChatPermissions(
    can_send_messages=False,
    can_send_audios=False,
    can_send_documents=False,
    can_send_photos=False,
    can_send_videos=False,
    can_send_video_notes=False,
    can_send_voice_notes=False,
    can_send_polls=False,
    can_send_other_messages=False,
    can_add_web_page_previews=False,
    can_invite_users=False,
)


async def restrict_user(bot: Bot, chat_id: int, user_id: int, until_ts: int | None = None):
    kwargs = {"chat_id": chat_id, "user_id": user_id, "permissions": NO_MESSAGES_PERMISSIONS}
    if until_ts:
        kwargs["until_date"] = until_ts
    await bot.restrict_chat_member(**kwargs)


async def unrestrict_user(bot: Bot, chat_id: int, user_id: int):
    await bot.restrict_chat_member(chat_id=chat_id, user_id=user_id, permissions=FULL_PERMISSIONS)


def human_delta(seconds: int) -> str:
    seconds = int(seconds)
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, _ = divmod(rem, 60)
    parts = []
    if days:
        parts.append(f"{days} kun")
    if hours:
        parts.append(f"{hours} soat")
    if minutes and not days:
        parts.append(f"{minutes} daqiqa")
    return " ".join(parts) if parts else "1 daqiqadan kam"


def today_str() -> str:
    return datetime.date.today().isoformat()


async def is_group_admin(bot: Bot, chat_id: int, user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        return member.status in ("administrator", "creator")
    except Exception:
        return False


def user_mention(user_id: int, name: str) -> str:
    safe_name = name.replace("<", "").replace(">", "")
    return f'<a href="tg://user?id={user_id}">{safe_name}</a>'
