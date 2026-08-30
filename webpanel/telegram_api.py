from aiogram import Bot
from aiogram.types import BufferedInputFile

from config import BOT_TOKEN, ADMIN_IDS

_bot: Bot | None = None


def get_bot() -> Bot:
    global _bot
    if _bot is None:
        _bot = Bot(token=BOT_TOKEN)
    return _bot


async def upload_document_get_file_id(file_bytes: bytes, filename: str) -> str:
    """
    Faylni birinchi admin bilan bo'lgan shaxsiy chatga yuboradi va Telegram
    qaytargan file_id ni oladi (bazada shu ID saqlanadi, fayl Telegram serverida qoladi).
    Admin bot bilan kamida bitta marta /start bosgan bo'lishi kerak.
    """
    bot = get_bot()
    admin_id = ADMIN_IDS[0]
    doc = BufferedInputFile(file_bytes, filename=filename)
    message = await bot.send_document(
        chat_id=admin_id, document=doc, caption=f"📥 Web panel orqali yuklandi: {filename}"
    )
    return message.document.file_id


async def upload_photo_get_file_id(file_bytes: bytes, filename: str) -> str:
    """Muqova rasmini birinchi admin bilan chatga yuboradi va photo file_id ni oladi."""
    bot = get_bot()
    admin_id = ADMIN_IDS[0]
    photo = BufferedInputFile(file_bytes, filename=filename)
    message = await bot.send_photo(chat_id=admin_id, photo=photo, caption=f"🖼 Muqova (web panel): {filename}")
    return message.photo[-1].file_id


async def get_file_bytes(file_id: str) -> tuple[bytes, str]:
    """Telegram serveridan fayl baytlarini yuklab oladi (token brauzerga chiqmasligi uchun serverda proksi qilinadi)."""
    bot = get_bot()
    file = await bot.get_file(file_id)
    buf = await bot.download_file(file.file_path)
    return buf.read(), file.file_path


_bot_username: str | None = None


async def get_bot_username() -> str:
    global _bot_username
    if _bot_username is None:
        bot = get_bot()
        me = await bot.get_me()
        _bot_username = me.username
    return _bot_username


async def send_message_to_user(user_id: int, text: str) -> bool:
    bot = get_bot()
    try:
        await bot.send_message(user_id, text)
        return True
    except Exception:
        return False


async def broadcast_text(user_ids: list[int], text: str, photo_bytes: bytes | None = None, filename: str = "image.jpg"):
    bot = get_bot()
    sent, failed = 0, 0
    for uid in user_ids:
        try:
            if photo_bytes:
                photo = BufferedInputFile(photo_bytes, filename=filename)
                await bot.send_photo(uid, photo, caption=text)
            else:
                await bot.send_message(uid, text)
            sent += 1
        except Exception:
            failed += 1
    return sent, failed


async def close_bot():
    global _bot
    if _bot is not None:
        await _bot.session.close()
        _bot = None
