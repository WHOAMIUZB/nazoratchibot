from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message

import database as db
from config import ADMIN_IDS


class MaintenanceMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        user_id = None
        if isinstance(event, Message) and event.from_user:
            user_id = event.from_user.id

        if user_id and user_id not in ADMIN_IDS:
            mode = await db.get_setting("maintenance_mode", "0")
            if mode == "1":
                lang = await db.get_language(user_id)
                text = {
                    "uz": "🔧 Bot hozir texnik tanaffusda. Iltimos, birozdan so‘ng qayta urinib ko‘ring.",
                    "ru": "🔧 Бот сейчас на техническом обслуживании. Попробуйте позже.",
                    "en": "🔧 The bot is under maintenance right now. Please try again later.",
                }.get(lang, "🔧 Bot hozir texnik tanaffusda. Iltimos, birozdan so‘ng qayta urinib ko‘ring.")
                await event.answer(text)
                return None

        return await handler(event, data)
