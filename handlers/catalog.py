from aiogram import Router, F
from aiogram.types import Message, CallbackQuery

import database as db
from locales import t
from keyboards import genres_kb, books_list_kb, genre_subscribe_kb

router = Router()


@router.message(F.text.in_({"📂 Janrlar", "📂 Жанры", "📂 Genres"}))
async def show_genres(message: Message):
    lang = await db.get_language(message.from_user.id)
    genres = await db.get_top_genres()
    if not genres:
        await message.answer(t("choose_genre", lang))
        return
    await message.answer(t("choose_genre", lang), reply_markup=genres_kb(genres, lang))


@router.callback_query(F.data.startswith("genre:"))
async def show_genre_books(callback: CallbackQuery):
    lang = await db.get_language(callback.from_user.id)
    genre_id = int(callback.data.split(":")[1])

    # If this genre has subgenres, show them; otherwise show books
    subgenres = await db.get_subgenres(genre_id)
    if subgenres:
        await callback.message.edit_text(
            t("choose_genre", lang), reply_markup=genres_kb(subgenres, lang, back_to="genres:root")
        )
        await callback.answer()
        return

    subscribed = await db.is_subscribed_genre(callback.from_user.id, genre_id)
    await callback.message.answer(
        "📂", reply_markup=genre_subscribe_kb(genre_id, subscribed, lang)
    )

    books = await db.books_by_genre(genre_id)
    if not books:
        await callback.answer(t("no_books_genre", lang), show_alert=True)
        return

    await callback.message.answer(
        t("search_results", lang, count=len(books)),
        reply_markup=books_list_kb(books, lang),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("gsub:"))
async def toggle_genre_sub(callback: CallbackQuery):
    lang = await db.get_language(callback.from_user.id)
    genre_id = int(callback.data.split(":")[1])
    subscribed = await db.is_subscribed_genre(callback.from_user.id, genre_id)
    if subscribed:
        await db.unsubscribe_genre(callback.from_user.id, genre_id)
    else:
        await db.subscribe_genre(callback.from_user.id, genre_id)
    new_state = not subscribed
    await callback.message.edit_reply_markup(reply_markup=genre_subscribe_kb(genre_id, new_state, lang))
    await callback.answer()


@router.callback_query(F.data == "genres:root")
async def back_to_root_genres(callback: CallbackQuery):
    lang = await db.get_language(callback.from_user.id)
    genres = await db.get_top_genres()
    await callback.message.edit_text(t("choose_genre", lang), reply_markup=genres_kb(genres, lang))
    await callback.answer()
