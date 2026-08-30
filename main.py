import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN, MINIAPP_URL
from database import init_db
from scheduler import reminder_loop, weekly_digest_loop
from middlewares import MaintenanceMiddleware

from handlers import start, search, catalog, book_detail, profile, extras, admin

logging.basicConfig(level=logging.INFO)


async def main():
    await init_db()

    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())
    dp.message.middleware(MaintenanceMiddleware())

    dp.include_router(admin.router)      # admin commands first
    dp.include_router(start.router)
    dp.include_router(search.router)
    dp.include_router(catalog.router)
    dp.include_router(book_detail.router)
    dp.include_router(profile.router)
    dp.include_router(extras.router)

    asyncio.create_task(reminder_loop(bot))
    asyncio.create_task(weekly_digest_loop(bot))

    from webpanel.app import run_webpanel
    from miniapp.app import run_miniapp
    asyncio.create_task(run_webpanel())
    asyncio.create_task(run_miniapp())

    if MINIAPP_URL.startswith("https://"):
        from aiogram.types import MenuButtonWebApp, WebAppInfo
        try:
            await bot.set_chat_menu_button(
                menu_button=MenuButtonWebApp(text="📚 Kitoblar", web_app=WebAppInfo(url=MINIAPP_URL))
            )
            logging.info(f"Mini App menu button o'rnatildi: {MINIAPP_URL}")
        except Exception as e:
            logging.warning(f"Mini App menu button o'rnatilmadi: {e}")

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
