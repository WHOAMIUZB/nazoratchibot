from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

import database as db
from locales import t
from states import FeedbackState, PromoState
from keyboards import books_list_kb, quiz_kb, club_kb, settings_kb
from config import XP_FOR_QUIZ_CORRECT, ADMIN_IDS

router = Router()


# ---------- TOP-10 ----------
@router.message(F.text.in_({"🔥 TOP-10", "🔥 ТОП-10"}))
async def show_top(message: Message):
    lang = await db.get_language(message.from_user.id)
    books = await db.top_books()
    if not books:
        await message.answer(t("no_books_genre", lang))
        return
    await message.answer(t("top_title", lang), reply_markup=books_list_kb(books, lang))


# ---------- Book club ----------
@router.message(F.text.in_({"💬 Kitobxonlar klubi", "💬 Клуб читателей", "💬 Readers Club"}))
async def show_club(message: Message):
    lang = await db.get_language(message.from_user.id)
    await message.answer(t("menu_club", lang), reply_markup=club_kb(lang))


# ---------- Quiz ----------
@router.message(F.text.in_({"🎮 Viktorina", "🎮 Викторина", "🎮 Quiz"}))
async def start_quiz(message: Message):
    lang = await db.get_language(message.from_user.id)
    q = await db.get_random_quiz()
    if not q:
        await message.answer(t("quiz_no_questions", lang))
        return
    options = {"a": q["option_a"], "b": q["option_b"], "c": q["option_c"], "d": q["option_d"]}
    await message.answer(f"❓ {q['question']}", reply_markup=quiz_kb(q["id"], options))


@router.callback_query(F.data.startswith("quizans:"))
async def answer_quiz(callback: CallbackQuery):
    lang = await db.get_language(callback.from_user.id)
    _, qid, chosen = callback.data.split(":")
    qid = int(qid)
    import aiosqlite
    from config import DB_PATH
    async with aiosqlite.connect(DB_PATH) as conn:
        conn.row_factory = aiosqlite.Row
        cur = await conn.execute("SELECT * FROM quiz_questions WHERE id=?", (qid,))
        q_row = await cur.fetchone()
    if not q_row:
        await callback.answer()
        return
    correct = q_row["correct_option"]
    is_correct = chosen == correct
    await db.log_quiz_answer(callback.from_user.id, qid, is_correct)
    if is_correct:
        await db.add_xp(callback.from_user.id, XP_FOR_QUIZ_CORRECT)
        await callback.message.edit_text(t("quiz_correct", lang, xp=XP_FOR_QUIZ_CORRECT))
    else:
        correct_text = q_row[f"option_{correct}"]
        await callback.message.edit_text(t("quiz_wrong", lang, correct=correct_text))
    await callback.answer()


# ---------- Promo codes ----------
@router.message(F.text.in_({"🎁 Promo-kod", "🎁 Промокод", "🎁 Promo code"}))
async def ask_promo(message: Message, state: FSMContext):
    lang = await db.get_language(message.from_user.id)
    await state.set_state(PromoState.waiting_code)
    await message.answer(t("promo_prompt", lang))


@router.message(PromoState.waiting_code)
async def redeem_promo_code(message: Message, state: FSMContext):
    lang = await db.get_language(message.from_user.id)
    await state.clear()
    code = message.text.strip().upper()
    xp, status = await db.redeem_promo(code, message.from_user.id)
    if status == "ok":
        await message.answer(t("promo_ok", lang, xp=xp))
    elif status == "not_found":
        await message.answer(t("promo_not_found", lang))
    elif status == "exhausted":
        await message.answer(t("promo_exhausted", lang))
    else:
        await message.answer(t("promo_already_used", lang))


# ---------- Feedback ----------
@router.message(F.text.in_({"✍️ Fikr bildirish", "✍️ Обратная связь", "✍️ Feedback"}))
async def ask_feedback(message: Message, state: FSMContext):
    lang = await db.get_language(message.from_user.id)
    await state.set_state(FeedbackState.waiting_text)
    await message.answer(t("feedback_prompt", lang))


@router.message(FeedbackState.waiting_text)
async def save_feedback(message: Message, state: FSMContext, bot=None):
    lang = await db.get_language(message.from_user.id)
    await state.clear()
    await db.add_feedback(message.from_user.id, message.text)
    await message.answer(t("feedback_thanks", lang))
    if bot:
        for admin_id in ADMIN_IDS:
            try:
                await bot.send_message(
                    admin_id,
                    f"✍️ Yangi fikr-mulohaza\nUser: {message.from_user.id} (@{message.from_user.username})\n\n{message.text}",
                )
            except Exception:
                pass


# ---------- Settings ----------
@router.message(F.text.in_({"⚙️ Sozlamalar", "⚙️ Настройки", "⚙️ Settings"}))
async def show_settings(message: Message):
    lang = await db.get_language(message.from_user.id)
    user = await db.get_user(message.from_user.id)
    await message.answer(t("settings_menu", lang), reply_markup=settings_kb(lang, bool(user["reminder_enabled"])))


@router.callback_query(F.data == "settings:lang")
async def settings_lang(callback: CallbackQuery):
    from keyboards import language_kb
    lang = await db.get_language(callback.from_user.id)
    await callback.message.answer(t("choose_language", lang), reply_markup=language_kb())
    await callback.answer()


@router.callback_query(F.data == "settings:reminder")
async def toggle_reminder(callback: CallbackQuery):
    lang = await db.get_language(callback.from_user.id)
    user = await db.get_user(callback.from_user.id)
    new_state = not bool(user["reminder_enabled"])
    await db.set_reminder(callback.from_user.id, new_state)
    await callback.answer(t("reminder_on", lang) if new_state else t("reminder_off", lang), show_alert=True)
    user = await db.get_user(callback.from_user.id)
    await callback.message.edit_reply_markup(reply_markup=settings_kb(lang, bool(user["reminder_enabled"])))
