from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

import database as db
from locales import t
from states import SearchState
from keyboards import books_list_kb

router = Router()


@router.message(F.text.in_({"🔎 Qidirish", "🔎 Поиск", "🔎 Search"}))
async def ask_search(message: Message, state: FSMContext):
    lang = await db.get_language(message.from_user.id)
    await state.set_state(SearchState.waiting_query)
    await message.answer(t("search_prompt", lang))


@router.message(SearchState.waiting_query)
async def do_search(message: Message, state: FSMContext):
    lang = await db.get_language(message.from_user.id)
    query = message.text.strip()
    await state.clear()
    await db.log_history(message.from_user.id, None, f"search:{query}")
    results = await db.search_books(query)
    if not results:
        await message.answer(t("search_not_found", lang))
        return
    await message.answer(
        t("search_results", lang, count=len(results)),
        reply_markup=books_list_kb(results, lang),
    )
