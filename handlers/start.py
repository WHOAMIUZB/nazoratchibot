from aiogram import Router, F
from aiogram.filters import CommandStart, CommandObject
from aiogram.types import Message, CallbackQuery

import database as db
from locales import t
from keyboards import main_menu, language_kb
from config import ADMIN_IDS

router = Router()


@router.message(CommandStart(deep_link=True))
async def start_with_ref(message: Message, command: CommandObject):
    ref = None
    if command.args and command.args.startswith("ref"):
        try:
            ref = int(command.args.replace("ref", ""))
        except ValueError:
            ref = None
    is_new = await db.get_or_create_user(
        message.from_user.id, message.from_user.username, message.from_user.first_name, referred_by=ref
    )
    await _greet(message, is_new)


@router.message(CommandStart())
async def start(message: Message):
    is_new = await db.get_or_create_user(
        message.from_user.id, message.from_user.username, message.from_user.first_name
    )
    await _greet(message, is_new)


async def _greet(message: Message, is_new: bool):
    if is_new:
        await message.answer(t("choose_language", "uz"), reply_markup=language_kb())
    else:
        lang = await db.get_language(message.from_user.id)
        await message.answer(
            t("welcome", lang, name=message.from_user.first_name),
            reply_markup=main_menu(lang, is_admin=message.from_user.id in ADMIN_IDS),
        )


@router.callback_query(F.data.startswith("lang:"))
async def set_language_cb(callback: CallbackQuery):
    lang = callback.data.split(":")[1]
    await db.set_language(callback.from_user.id, lang)
    await callback.message.delete()
    await callback.message.answer(
        t("language_set", lang) + "\n\n" + t("welcome", lang, name=callback.from_user.first_name),
        reply_markup=main_menu(lang, is_admin=callback.from_user.id in ADMIN_IDS),
    )
    await callback.answer()
