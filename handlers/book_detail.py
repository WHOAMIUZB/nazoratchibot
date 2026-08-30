import math
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, BufferedInputFile
from aiogram.exceptions import TelegramBadRequest

import database as db
from locales import t
from states import ReviewState
from keyboards import (
    book_detail_kb, reading_kb, rating_kb, shelf_kb, books_list_kb,
)
from config import PAGE_CHARS, XP_FOR_DOWNLOAD, XP_FOR_REVIEW

router = Router()


async def render_book_card(callback_or_message, book_id: int, user_id: int, lang: str, edit: bool = False):
    book = await db.get_book(book_id)
    if not book:
        return
    await db.increment_views(book_id)
    is_fav = await db.is_favorite(user_id, book_id)
    rating = round(book["rating_sum"] / book["rating_count"], 1) if book["rating_count"] else "—"
    text = t(
        "book_card", lang,
        title=book["title"], author=book["author"] or "—",
        rating=rating, downloads=book["downloads"],
        description=(book["description"] or "")[:600],
    )
    kb = book_detail_kb(book_id, lang, is_fav, has_text=bool(book["full_text"]))
    target = callback_or_message.message if isinstance(callback_or_message, CallbackQuery) else callback_or_message
    if edit:
        try:
            await target.edit_text(text, reply_markup=kb)
            return
        except TelegramBadRequest:
            pass
    await target.answer(text, reply_markup=kb)


@router.callback_query(F.data.startswith("book:"))
async def open_book(callback: CallbackQuery):
    lang = await db.get_language(callback.from_user.id)
    book_id = int(callback.data.split(":")[1])
    await db.log_history(callback.from_user.id, book_id, "view")
    await render_book_card(callback, book_id, callback.from_user.id, lang, edit=True)
    await callback.answer()


@router.callback_query(F.data.startswith("fav:"))
async def toggle_favorite(callback: CallbackQuery):
    lang = await db.get_language(callback.from_user.id)
    book_id = int(callback.data.split(":")[1])
    if await db.is_favorite(callback.from_user.id, book_id):
        await db.remove_favorite(callback.from_user.id, book_id)
        await callback.answer(t("removed_favorite", lang))
    else:
        await db.add_favorite(callback.from_user.id, book_id)
        await callback.answer(t("added_favorite", lang))
    await render_book_card(callback, book_id, callback.from_user.id, lang, edit=True)


@router.callback_query(F.data.startswith("similar:"))
async def show_similar(callback: CallbackQuery):
    lang = await db.get_language(callback.from_user.id)
    book_id = int(callback.data.split(":")[1])
    book = await db.get_book(book_id)
    if not book or not book["genre_id"]:
        await callback.answer(t("no_books_genre", lang), show_alert=True)
        return
    similar = await db.similar_books(book["genre_id"], book_id)
    if not similar:
        await callback.answer(t("no_books_genre", lang), show_alert=True)
        return
    await callback.message.answer(
        t("search_results", lang, count=len(similar)),
        reply_markup=books_list_kb(similar, lang),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("shelf:"))
async def choose_shelf(callback: CallbackQuery):
    lang = await db.get_language(callback.from_user.id)
    book_id = int(callback.data.split(":")[1])
    await callback.message.answer(t("choose_shelf", lang), reply_markup=shelf_kb(book_id, lang))
    await callback.answer()


@router.callback_query(F.data.startswith("setshelf:"))
async def set_shelf_cb(callback: CallbackQuery):
    lang = await db.get_language(callback.from_user.id)
    _, book_id, status = callback.data.split(":")
    await db.set_shelf(callback.from_user.id, int(book_id), status)
    await callback.answer(t("shelf_saved", lang))


@router.callback_query(F.data.startswith("rate:"))
async def start_rating(callback: CallbackQuery):
    lang = await db.get_language(callback.from_user.id)
    book_id = int(callback.data.split(":")[1])
    if await db.user_already_reviewed(callback.from_user.id, book_id):
        await callback.answer(t("already_reviewed", lang), show_alert=True)
        return
    await callback.message.answer(t("rate_prompt", lang), reply_markup=rating_kb(book_id))
    await callback.answer()


@router.callback_query(F.data.startswith("setrating:"))
async def set_rating(callback: CallbackQuery, state: FSMContext):
    lang = await db.get_language(callback.from_user.id)
    _, book_id, rating = callback.data.split(":")
    await state.set_state(ReviewState.waiting_review)
    await state.update_data(book_id=int(book_id), rating=int(rating))
    await callback.message.edit_text(t("rate_review_prompt", lang, rating=rating))
    await callback.answer()


@router.message(ReviewState.waiting_review)
async def save_review(message, state: FSMContext):
    lang = await db.get_language(message.from_user.id)
    data = await state.get_data()
    text = None if message.text.strip() == "/skip" else message.text.strip()
    await db.add_review(message.from_user.id, data["book_id"], data["rating"], text)
    await db.add_xp(message.from_user.id, XP_FOR_REVIEW)
    await state.clear()
    await message.answer(t("review_saved", lang, xp=XP_FOR_REVIEW))


@router.callback_query(F.data.startswith("download:"))
async def download_book(callback: CallbackQuery):
    lang = await db.get_language(callback.from_user.id)
    book_id = int(callback.data.split(":")[1])
    book = await db.get_book(book_id)
    if not book:
        await callback.answer()
        return
    if book["is_premium"]:
        await callback.answer(t("premium_locked", lang), show_alert=True)
        return
    if book["file_id"]:
        await callback.message.answer_document(book["file_id"], caption=book["title"])
        await db.increment_downloads(book_id)
        await db.log_history(callback.from_user.id, book_id, "download")
        await db.add_xp(callback.from_user.id, XP_FOR_DOWNLOAD)
    await callback.answer()


# ---------- In-bot paginated reading ----------
@router.callback_query(F.data.startswith("read:"))
async def read_book(callback: CallbackQuery):
    lang = await db.get_language(callback.from_user.id)
    _, book_id, page = callback.data.split(":")
    book_id, page = int(book_id), int(page)
    book = await db.get_book(book_id)
    if not book or not book["full_text"]:
        await callback.answer()
        return
    if book["is_premium"]:
        await callback.answer(t("premium_locked", lang), show_alert=True)
        return

    text = book["full_text"]
    total_pages = max(1, math.ceil(len(text) / PAGE_CHARS))
    page = max(0, min(page, total_pages - 1))
    chunk = text[page * PAGE_CHARS:(page + 1) * PAGE_CHARS]

    await db.set_progress(callback.from_user.id, book_id, page)
    await db.log_history(callback.from_user.id, book_id, "read")

    header = t("reading_page", lang, page=page + 1, total=total_pages)
    body = f"<b>{book['title']}</b>\n{header}\n\n{chunk}"
    try:
        await callback.message.edit_text(body, reply_markup=reading_kb(book_id, page, total_pages))
    except TelegramBadRequest:
        await callback.message.answer(body, reply_markup=reading_kb(book_id, page, total_pages))
    await callback.answer()
