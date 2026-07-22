import logging
import time
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest

import database as db
from config import DELETED_ACCOUNTS_CHECK_INTERVAL, CHANNEL_STATS_INTERVAL

logger = logging.getLogger(__name__)


async def _is_deleted_account(bot: Bot, user_id: int) -> bool:
    """Telegram Bot API orqali foydalanuvchi hisobi o'chirilganini aniqlashga urinadi.
    O'chirilgan hisoblar odatda 'Deleted Account' nomi va bo'sh profil bilan qaytadi."""
    try:
        chat = await bot.get_chat(user_id)
        if chat.first_name in ("Deleted Account", None) and not chat.last_name and not chat.username:
            return True
        return False
    except (TelegramBadRequest, TelegramForbiddenError):
        # Foydalanuvchi topilmadi / bot bilan hech qanday aloqasi yo'q — aniqlab bo'lmaydi, o'tkazib yuboramiz
        return False
    except Exception:
        return False


async def clean_deleted_accounts_job(bot: Bot):
    channels = await db.all_channels_with_feature("clean_deleted_enabled")
    for ch in channels:
        channel_id = ch["channel_id"]
        member_ids = await db.get_tracked_members(channel_id)
        removed = 0
        for user_id in member_ids:
            try:
                if await _is_deleted_account(bot, user_id):
                    await bot.ban_chat_member(channel_id, user_id)
                    await bot.unban_chat_member(channel_id, user_id, only_if_banned=True)
                    await db.track_channel_member_left(channel_id, user_id)
                    removed += 1
            except Exception as e:
                logger.warning(f"clean_deleted: {channel_id}/{user_id} - {e}")
        if removed:
            try:
                await bot.send_message(
                    ch["owner_id"],
                    f"🧹 <b>{ch['title']}</b> kanalidan <b>{removed}</b> ta o'chirilgan hisob avtomatik chiqarib yuborildi.",
                    parse_mode="HTML",
                )
            except Exception:
                pass


async def send_channel_stats_job(bot: Bot):
    channels = await db.all_channels_with_feature("stats_enabled")
    since_ts = int(time.time()) - CHANNEL_STATS_INTERVAL
    for ch in channels:
        channel_id = ch["channel_id"]
        events = await db.get_channel_events_since(channel_id, since_ts)
        try:
            current_count = await bot.get_chat_member_count(channel_id)
        except Exception:
            current_count = "?"
        text = (
            f"📊 <b>{ch['title']}</b> — so'nggi 12 soat statistikasi\n\n"
            f"🟢 Qo'shildi: <b>{events.get('joined', 0)}</b>\n"
            f"🔴 Chiqib ketdi: <b>{events.get('left', 0)}</b>\n"
            f"👥 Hozirgi obunachilar: <b>{current_count}</b>"
        )
        try:
            await bot.send_message(ch["owner_id"], text, parse_mode="HTML")
        except Exception as e:
            logger.warning(f"send_stats: {channel_id} - {e}")


def setup_scheduler(bot: Bot) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        clean_deleted_accounts_job, "interval",
        seconds=DELETED_ACCOUNTS_CHECK_INTERVAL, args=[bot], id="clean_deleted",
    )
    scheduler.add_job(
        send_channel_stats_job, "interval",
        seconds=CHANNEL_STATS_INTERVAL, args=[bot], id="channel_stats",
    )
    return scheduler
