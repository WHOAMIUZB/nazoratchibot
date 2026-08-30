from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

import database as db
from locales import t
from config import ADMIN_IDS
from states import (
    AddBookState, EditBookState, BroadcastState, PromoCreateState,
    QuizAddState, GenreAddState, SetTextState, BlockUserState, SetCoverState,
)
from keyboards import (
    genres_kb, admin_main_kb, admin_back_kb, admin_books_list_kb,
    admin_edit_fields_kb, admin_confirm_kb, admin_users_list_kb,
)

router = Router()


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


async def admin_only_msg(message: Message) -> bool:
    if not is_admin(message.from_user.id):
        lang = await db.get_language(message.from_user.id)
        await message.answer(t("not_admin", lang))
        return False
    return True


async def admin_only_cb(callback: CallbackQuery) -> bool:
    if not is_admin(callback.from_user.id):
        lang = await db.get_language(callback.from_user.id)
        await callback.answer(t("not_admin", lang), show_alert=True)
        return False
    return True


# ---------- ENTRY POINTS ----------
@router.message(Command("admin"))
async def admin_menu_cmd(message: Message, state: FSMContext):
    if not await admin_only_msg(message):
        return
    await state.clear()
    await message.answer("🛠 <b>Admin panel</b>\n\nKerakli bo‘limni tanlang:", reply_markup=admin_main_kb())


@router.message(F.text == "🛠 Admin panel")
async def admin_menu_btn(message: Message, state: FSMContext):
    if not await admin_only_msg(message):
        return
    await state.clear()
    await message.answer("🛠 <b>Admin panel</b>\n\nKerakli bo‘limni tanlang:", reply_markup=admin_main_kb())


@router.callback_query(F.data == "admin:menu")
async def admin_menu_back(callback: CallbackQuery, state: FSMContext):
    if not await admin_only_cb(callback):
        return
    await state.clear()
    await callback.message.edit_text("🛠 <b>Admin panel</b>\n\nKerakli bo‘limni tanlang:", reply_markup=admin_main_kb())
    await callback.answer()


# ============================================================
# ADD BOOK
# ============================================================
@router.callback_query(F.data == "admin:addbook")
async def add_book_start(callback: CallbackQuery, state: FSMContext):
    if not await admin_only_cb(callback):
        return
    genres = await db.get_top_genres()
    if not genres:
        await callback.answer("Avval janr qo‘shing.", show_alert=True)
        return
    await state.set_state(AddBookState.choosing_genre)
    await callback.message.edit_text("Janrni tanlang:", reply_markup=genres_kb(genres, "uz", back_to="admin:menu"))
    await callback.answer()


@router.callback_query(AddBookState.choosing_genre, F.data.startswith("genre:"))
async def add_book_genre_chosen(callback: CallbackQuery, state: FSMContext):
    genre_id = int(callback.data.split(":")[1])
    await state.update_data(genre_id=genre_id)
    await state.set_state(AddBookState.waiting_title)
    await callback.message.edit_text("Kitob nomini yozing:", reply_markup=admin_back_kb())
    await callback.answer()


@router.message(AddBookState.waiting_title)
async def add_book_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text.strip())
    await state.set_state(AddBookState.waiting_author)
    await message.answer("Muallifni yozing:", reply_markup=admin_back_kb())


@router.message(AddBookState.waiting_author)
async def add_book_author(message: Message, state: FSMContext):
    await state.update_data(author=message.text.strip())
    await state.set_state(AddBookState.waiting_year)
    await message.answer("Nashr yilini yozing (yoki 0):", reply_markup=admin_back_kb())


@router.message(AddBookState.waiting_year)
async def add_book_year(message: Message, state: FSMContext):
    try:
        year = int(message.text.strip())
    except ValueError:
        year = None
    await state.update_data(year=year)
    await state.set_state(AddBookState.waiting_description)
    await message.answer("Qisqacha tavsif yozing:", reply_markup=admin_back_kb())


@router.message(AddBookState.waiting_description)
async def add_book_description(message: Message, state: FSMContext):
    await state.update_data(description=message.text.strip())
    await state.set_state(AddBookState.waiting_cover)
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    b = InlineKeyboardBuilder()
    b.button(text="⏭ O‘tkazib yuborish", callback_data="adm_skipcover")
    b.button(text="⬅️ Admin menyu", callback_data="admin:menu")
    b.adjust(1)
    await message.answer("Kitob muqovasi uchun rasm yuboring (yoki o‘tkazib yuboring):", reply_markup=b.as_markup())


@router.message(AddBookState.waiting_cover, F.photo)
async def add_book_cover_photo(message: Message, state: FSMContext):
    await state.update_data(cover_file_id=message.photo[-1].file_id)
    await state.set_state(AddBookState.waiting_file)
    await message.answer("✅ Muqova saqlandi. Endi kitob faylini (PDF/EPUB) yuboring:", reply_markup=admin_back_kb())


@router.callback_query(AddBookState.waiting_cover, F.data == "adm_skipcover")
async def add_book_cover_skip(callback: CallbackQuery, state: FSMContext):
    await state.update_data(cover_file_id=None)
    await state.set_state(AddBookState.waiting_file)
    await callback.message.edit_text("Endi kitob faylini (PDF/EPUB) yuboring:", reply_markup=admin_back_kb())
    await callback.answer()


@router.message(AddBookState.waiting_file, F.document)
async def add_book_file(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    is_dup = await db.check_duplicate(data["title"], data["author"])
    if is_dup:
        await message.answer("⚠️ Diqqat: bu nom+muallif bilan kitob allaqachon mavjud. Baribir qo‘shilmoqda...")
    file_id = message.document.file_id
    file_type = (message.document.file_name or "").split(".")[-1].lower()
    book_id = await db.add_book(
        title=data["title"], author=data["author"], genre_id=data["genre_id"],
        description=data["description"], file_id=file_id, file_type=file_type,
        added_by=message.from_user.id, year=data.get("year"),
        cover_file_id=data.get("cover_file_id"),
    )
    await state.clear()
    await message.answer(
        f"✅ Kitob qo‘shildi! ID: {book_id}\n\n"
        f"Onlayn o‘qish uchun matnli variantini ham qo‘shmoqchi bo‘lsangiz, "
        f"Admin panel → 📄 Onlayn o‘qish matni bo‘limidan foydalaning.",
        reply_markup=admin_main_kb(),
    )
    from scheduler import new_book_notify
    await new_book_notify(bot, book_id, data["genre_id"])


# ============================================================
# SET FULL TEXT (in-bot reading)
# ============================================================
@router.callback_query(F.data == "admin:settext")
async def settext_start(callback: CallbackQuery, state: FSMContext):
    if not await admin_only_cb(callback):
        return
    books = await db.list_books()
    if not books:
        await callback.answer("Hozircha kitoblar yo‘q.", show_alert=True)
        return
    await callback.message.edit_text(
        "Qaysi kitobga onlayn o‘qish matnini qo‘shamiz?",
        reply_markup=admin_books_list_kb(books, "textsel"),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("adm_textsel:"))
async def settext_book_chosen(callback: CallbackQuery, state: FSMContext):
    book_id = int(callback.data.split(":")[1])
    await state.update_data(settext_book_id=book_id)
    await state.set_state(SetTextState.waiting_text)
    await callback.message.edit_text("Endi kitob matnini (oddiy matn holida) yuboring:", reply_markup=admin_back_kb())
    await callback.answer()


@router.message(SetTextState.waiting_text)
async def settext_save(message: Message, state: FSMContext):
    data = await state.get_data()
    book_id = data.get("settext_book_id")
    if book_id:
        await db.set_full_text(book_id, message.text)
        await message.answer("✅ Onlayn o‘qish matni saqlandi.", reply_markup=admin_main_kb())
    await state.clear()


# ============================================================
# SET COVER IMAGE (for existing books)
# ============================================================
@router.callback_query(F.data == "admin:setcover")
async def setcover_start(callback: CallbackQuery, state: FSMContext):
    if not await admin_only_cb(callback):
        return
    books = await db.list_books()
    if not books:
        await callback.answer("Hozircha kitoblar yo‘q.", show_alert=True)
        return
    await callback.message.edit_text(
        "Qaysi kitobga muqova rasm qo‘yamiz?",
        reply_markup=admin_books_list_kb(books, "coversel"),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("adm_coversel:"))
async def setcover_book_chosen(callback: CallbackQuery, state: FSMContext):
    book_id = int(callback.data.split(":")[1])
    await state.update_data(cover_book_id=book_id)
    await state.set_state(SetCoverState.waiting_photo)
    await callback.message.edit_text("Endi muqova rasmini yuboring:", reply_markup=admin_back_kb())
    await callback.answer()


@router.message(SetCoverState.waiting_photo, F.photo)
async def setcover_save(message: Message, state: FSMContext):
    data = await state.get_data()
    book_id = data.get("cover_book_id")
    if book_id:
        await db.edit_book_field(book_id, "cover_file_id", message.photo[-1].file_id)
        await message.answer("✅ Muqova rasm saqlandi.", reply_markup=admin_main_kb())
    await state.clear()


# ============================================================
# EDIT BOOK
# ============================================================
@router.callback_query(F.data == "admin:editbook")
async def edit_book_start(callback: CallbackQuery, state: FSMContext):
    if not await admin_only_cb(callback):
        return
    books = await db.list_books()
    if not books:
        await callback.answer("Hozircha kitoblar yo‘q.", show_alert=True)
        return
    await callback.message.edit_text("Qaysi kitobni tahrirlaymiz?", reply_markup=admin_books_list_kb(books, "editsel"))
    await callback.answer()


@router.callback_query(F.data.startswith("adm_editsel:"))
async def edit_book_selected(callback: CallbackQuery, state: FSMContext):
    book_id = int(callback.data.split(":")[1])
    book = await db.get_book(book_id)
    if not book:
        await callback.answer("Topilmadi.", show_alert=True)
        return
    await state.update_data(book_id=book_id)
    await callback.message.edit_text(
        f"📖 <b>{book['title']}</b>\nQaysi maydonni o‘zgartiramiz?",
        reply_markup=admin_edit_fields_kb(book_id),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("adm_field:"))
async def edit_book_field_chosen(callback: CallbackQuery, state: FSMContext):
    _, book_id, field = callback.data.split(":")
    await state.update_data(book_id=int(book_id), field=field)
    await state.set_state(EditBookState.waiting_value)
    labels = {"title": "Yangi nomni", "author": "Yangi muallifni", "description": "Yangi tavsifni", "year": "Yangi yilni"}
    await callback.message.edit_text(f"{labels.get(field, 'Yangi qiymatni')} kiriting:", reply_markup=admin_back_kb())
    await callback.answer()


@router.message(EditBookState.waiting_value)
async def edit_book_value(message: Message, state: FSMContext):
    data = await state.get_data()
    value = message.text.strip()
    try:
        await db.edit_book_field(data["book_id"], data["field"], value)
        await message.answer("✅ Yangilandi.", reply_markup=admin_main_kb())
    except ValueError:
        await message.answer("❌ Bu maydonni o‘zgartirib bo‘lmaydi.", reply_markup=admin_main_kb())
    await state.clear()


@router.callback_query(F.data.startswith("adm_toggle:"))
async def toggle_book_field(callback: CallbackQuery):
    _, book_id, field = callback.data.split(":")
    book_id = int(book_id)
    import aiosqlite
    from config import DB_PATH
    async with aiosqlite.connect(DB_PATH) as conn:
        conn.row_factory = aiosqlite.Row
        cur = await conn.execute(f"SELECT {field} FROM books WHERE book_id=?", (book_id,))
        row = await cur.fetchone()
    if row is None:
        await callback.answer("Topilmadi.", show_alert=True)
        return
    new_value = 0 if row[field] else 1
    await db.edit_book_field(book_id, field, new_value)
    label = "yoqildi ✅" if new_value else "o‘chirildi ❌"
    await callback.answer(f"{field} {label}", show_alert=True)
    await callback.message.edit_reply_markup(reply_markup=admin_edit_fields_kb(book_id))


# ============================================================
# DELETE BOOK
# ============================================================
@router.callback_query(F.data == "admin:delbook")
async def del_book_start(callback: CallbackQuery):
    if not await admin_only_cb(callback):
        return
    books = await db.list_books()
    if not books:
        await callback.answer("Hozircha kitoblar yo‘q.", show_alert=True)
        return
    await callback.message.edit_text("Qaysi kitobni o‘chiramiz?", reply_markup=admin_books_list_kb(books, "delsel"))
    await callback.answer()


@router.callback_query(F.data.startswith("adm_delsel:"))
async def del_book_selected(callback: CallbackQuery):
    book_id = int(callback.data.split(":")[1])
    book = await db.get_book(book_id)
    title = book["title"] if book else str(book_id)
    await callback.message.edit_text(
        f"🗑 <b>{title}</b>\nRostdan ham o‘chirilsinmi?",
        reply_markup=admin_confirm_kb("adm_delconfirm", str(book_id)),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("adm_delconfirm:"))
async def del_book_confirm(callback: CallbackQuery):
    _, book_id, answer = callback.data.split(":")
    if answer == "yes":
        await db.delete_book(int(book_id))
        await callback.message.edit_text("🗑 Kitob o‘chirildi.", reply_markup=admin_main_kb())
    else:
        await callback.message.edit_text("Bekor qilindi.", reply_markup=admin_main_kb())
    await callback.answer()


# ============================================================
# ADD GENRE
# ============================================================
@router.callback_query(F.data == "admin:addgenre")
async def add_genre_start(callback: CallbackQuery, state: FSMContext):
    if not await admin_only_cb(callback):
        return
    await state.set_state(GenreAddState.waiting_name_uz)
    await callback.message.edit_text("Janr nomi (o‘zbekcha):", reply_markup=admin_back_kb())
    await callback.answer()


@router.message(GenreAddState.waiting_name_uz)
async def add_genre_uz(message: Message, state: FSMContext):
    await state.update_data(name_uz=message.text.strip())
    await state.set_state(GenreAddState.waiting_name_ru)
    await message.answer("Janr nomi (ruscha):", reply_markup=admin_back_kb())


@router.message(GenreAddState.waiting_name_ru)
async def add_genre_ru(message: Message, state: FSMContext):
    await state.update_data(name_ru=message.text.strip())
    await state.set_state(GenreAddState.waiting_name_en)
    await message.answer("Janr nomi (inglizcha):", reply_markup=admin_back_kb())


@router.message(GenreAddState.waiting_name_en)
async def add_genre_en(message: Message, state: FSMContext):
    data = await state.get_data()
    genre_id = await db.add_genre(data["name_uz"], data["name_ru"], message.text.strip())
    await state.clear()
    await message.answer(f"✅ Janr qo‘shildi! ID: {genre_id}", reply_markup=admin_main_kb())


# ============================================================
# BROADCAST
# ============================================================
@router.callback_query(F.data == "admin:broadcast")
async def broadcast_start(callback: CallbackQuery, state: FSMContext):
    if not await admin_only_cb(callback):
        return
    await state.set_state(BroadcastState.waiting_content)
    await callback.message.edit_text(
        "Barchaga yuboriladigan xabarni yuboring (matn, rasm yoki video):", reply_markup=admin_back_kb()
    )
    await callback.answer()


@router.message(BroadcastState.waiting_content)
async def broadcast_content(message: Message, state: FSMContext):
    await state.update_data(chat_id=message.chat.id, message_id=message.message_id)
    await state.set_state(BroadcastState.waiting_confirm)
    await message.answer("Yuborishni tasdiqlaysizmi?", reply_markup=admin_confirm_kb("adm_bcconfirm", "go"))


@router.callback_query(BroadcastState.waiting_confirm, F.data.startswith("adm_bcconfirm:"))
async def broadcast_confirm(callback: CallbackQuery, state: FSMContext, bot: Bot):
    answer = callback.data.split(":")[2]
    if answer != "yes":
        await state.clear()
        await callback.message.edit_text("Bekor qilindi.", reply_markup=admin_main_kb())
        await callback.answer()
        return
    data = await state.get_data()
    user_ids = await db.all_user_ids()
    sent, failed = 0, 0
    for uid in user_ids:
        try:
            await bot.copy_message(chat_id=uid, from_chat_id=data["chat_id"], message_id=data["message_id"])
            sent += 1
        except Exception:
            failed += 1
    await state.clear()
    await callback.message.edit_text(f"✅ Yuborildi: {sent} ta\n❌ Xato: {failed} ta", reply_markup=admin_main_kb())
    await callback.answer()


# ============================================================
# PROMO CODES
# ============================================================
@router.callback_query(F.data == "admin:addpromo")
async def add_promo_start(callback: CallbackQuery, state: FSMContext):
    if not await admin_only_cb(callback):
        return
    await state.set_state(PromoCreateState.waiting_code)
    await callback.message.edit_text("Promo-kod matnini kiriting (masalan: KITOB2026):", reply_markup=admin_back_kb())
    await callback.answer()


@router.message(PromoCreateState.waiting_code)
async def add_promo_code(message: Message, state: FSMContext):
    await state.update_data(code=message.text.strip().upper())
    await state.set_state(PromoCreateState.waiting_reward)
    await message.answer("Necha XP beriladi? (raqam kiriting)", reply_markup=admin_back_kb())


@router.message(PromoCreateState.waiting_reward)
async def add_promo_reward(message: Message, state: FSMContext):
    if not message.text.strip().isdigit():
        await message.answer("Raqam kiriting.", reply_markup=admin_back_kb())
        return
    await state.update_data(reward=int(message.text.strip()))
    await state.set_state(PromoCreateState.waiting_uses)
    await message.answer("Nechta foydalanuvchi ishlata oladi? (raqam kiriting)", reply_markup=admin_back_kb())


@router.message(PromoCreateState.waiting_uses)
async def add_promo_uses(message: Message, state: FSMContext):
    if not message.text.strip().isdigit():
        await message.answer("Raqam kiriting.", reply_markup=admin_back_kb())
        return
    data = await state.get_data()
    await db.create_promo(data["code"], data["reward"], int(message.text.strip()), message.from_user.id)
    await state.clear()
    await message.answer(f"✅ Promo-kod yaratildi: {data['code']}", reply_markup=admin_main_kb())


# ============================================================
# QUIZ QUESTIONS
# ============================================================
@router.callback_query(F.data == "admin:addquiz")
async def add_quiz_start(callback: CallbackQuery, state: FSMContext):
    if not await admin_only_cb(callback):
        return
    books = await db.list_books()
    await state.set_state(QuizAddState.waiting_book_id)
    if books:
        await callback.message.edit_text(
            "Qaysi kitobga tegishli savol?",
            reply_markup=admin_books_list_kb(books, "quizbook"),
        )
    else:
        await callback.message.edit_text("Kitob ID sini kiriting (umumiy uchun 0):", reply_markup=admin_back_kb())
    await callback.answer()


@router.callback_query(F.data.startswith("adm_quizbook:"))
async def add_quiz_book_from_list(callback: CallbackQuery, state: FSMContext):
    book_id = int(callback.data.split(":")[1])
    await state.update_data(book_id=book_id)
    await state.set_state(QuizAddState.waiting_question)
    await callback.message.edit_text("Savol matnini yozing:", reply_markup=admin_back_kb())
    await callback.answer()


@router.message(QuizAddState.waiting_book_id)
async def add_quiz_book_id(message: Message, state: FSMContext):
    if not message.text.strip().isdigit():
        await message.answer("Raqam kiriting.", reply_markup=admin_back_kb())
        return
    await state.update_data(book_id=int(message.text.strip()) or None)
    await state.set_state(QuizAddState.waiting_question)
    await message.answer("Savol matnini yozing:", reply_markup=admin_back_kb())


@router.message(QuizAddState.waiting_question)
async def add_quiz_question_text(message: Message, state: FSMContext):
    await state.update_data(question=message.text.strip())
    await state.set_state(QuizAddState.waiting_options)
    await message.answer(
        "Variantlarni shu formatda yozing:\nA) ...\nB) ...\nC) ...\nD) ...", reply_markup=admin_back_kb()
    )


@router.message(QuizAddState.waiting_options)
async def add_quiz_options(message: Message, state: FSMContext):
    lines = [l.strip() for l in message.text.strip().split("\n") if l.strip()]
    opts = {}
    for line in lines:
        if line[:2].upper() in ("A)", "B)", "C)", "D)"):
            opts[line[0].lower()] = line[2:].strip(" .")
    if len(opts) < 2:
        await message.answer("Kamida 2 ta variant kerak. Qaytadan yuboring.", reply_markup=admin_back_kb())
        return
    await state.update_data(options=opts)
    await state.set_state(QuizAddState.waiting_correct)
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    b = InlineKeyboardBuilder()
    for key in opts:
        b.button(text=key.upper(), callback_data=f"adm_quizcorrect:{key}")
    b.adjust(4)
    await message.answer("To‘g‘ri javobni tanlang:", reply_markup=b.as_markup())


@router.callback_query(QuizAddState.waiting_correct, F.data.startswith("adm_quizcorrect:"))
async def add_quiz_correct(callback: CallbackQuery, state: FSMContext):
    correct = callback.data.split(":")[1]
    data = await state.get_data()
    opts = data["options"]
    await db.add_quiz_question(
        data.get("book_id"), data["question"],
        opts.get("a"), opts.get("b"), opts.get("c"), opts.get("d"), correct,
    )
    await state.clear()
    await callback.message.edit_text("✅ Viktorina savoli qo‘shildi.", reply_markup=admin_main_kb())
    await callback.answer()


# ============================================================
# STATS
# ============================================================
@router.callback_query(F.data == "admin:stats")
async def show_stats(callback: CallbackQuery):
    if not await admin_only_cb(callback):
        return
    users = await db.users_count()
    new_today = await db.today_new_users()
    books = await db.books_count()
    top = await db.top_books(5)
    top_lines = "\n".join(f"  {i+1}. {b['title']} — {b['downloads']} ta" for i, b in enumerate(top))
    await callback.message.edit_text(
        f"📊 <b>Statistika</b>\n\n"
        f"👥 Foydalanuvchilar: {users}\n"
        f"🆕 Bugun qo‘shilgan: {new_today}\n"
        f"📚 Kitoblar soni: {books}\n\n"
        f"🔥 TOP-5 yuklab olingan:\n{top_lines or '  —'}",
        reply_markup=admin_back_kb(),
    )
    await callback.answer()


# ============================================================
# FEEDBACK LIST
# ============================================================
@router.callback_query(F.data == "admin:feedbacks")
async def show_feedbacks(callback: CallbackQuery):
    if not await admin_only_cb(callback):
        return
    items = await db.list_feedback()
    if not items:
        await callback.message.edit_text("Fikr-mulohazalar yo‘q.", reply_markup=admin_back_kb())
        await callback.answer()
        return
    lines = [f"#{f['id']} | {f['user_id']} | {f['created_at'][:16]}\n{f['text']}" for f in items]
    text = "\n\n".join(lines)[:3900]
    await callback.message.edit_text(text, reply_markup=admin_back_kb())
    await callback.answer()


# ============================================================
# BLOCK / UNBLOCK
# ============================================================
@router.callback_query(F.data == "admin:block")
async def block_start(callback: CallbackQuery):
    if not await admin_only_cb(callback):
        return
    users = await db.recent_users()
    if not users:
        await callback.answer("Foydalanuvchilar topilmadi.", show_alert=True)
        return
    await callback.message.edit_text(
        "Kimni bloklaymiz? (oxirgi faol foydalanuvchilar)",
        reply_markup=admin_users_list_kb(users, "block"),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("adm_block:"))
async def block_user_cb(callback: CallbackQuery):
    user_id = int(callback.data.split(":")[1])
    await db.set_block(user_id, True)
    await callback.message.edit_text(f"🚫 Foydalanuvchi ({user_id}) bloklandi.", reply_markup=admin_main_kb())
    await callback.answer()


@router.callback_query(F.data == "adm_blockmanual")
async def block_manual_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(BlockUserState.waiting_id)
    await state.update_data(action="block")
    await callback.message.edit_text("Bloklanadigan foydalanuvchi ID sini yuboring:", reply_markup=admin_back_kb())
    await callback.answer()


@router.callback_query(F.data == "admin:unblock")
async def unblock_start(callback: CallbackQuery):
    if not await admin_only_cb(callback):
        return
    users = await db.blocked_users()
    if not users:
        await callback.message.edit_text("Bloklangan foydalanuvchilar yo‘q.", reply_markup=admin_back_kb())
        await callback.answer()
        return
    await callback.message.edit_text(
        "Kimni blokdan chiqaramiz?",
        reply_markup=admin_users_list_kb(users, "unblock"),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("adm_unblock:"))
async def unblock_user_cb(callback: CallbackQuery):
    user_id = int(callback.data.split(":")[1])
    await db.set_block(user_id, False)
    await callback.message.edit_text(f"✅ Foydalanuvchi ({user_id}) blokdan chiqarildi.", reply_markup=admin_main_kb())
    await callback.answer()


@router.callback_query(F.data == "adm_unblockmanual")
async def unblock_manual_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(BlockUserState.waiting_id)
    await state.update_data(action="unblock")
    await callback.message.edit_text("Blokdan chiqariladigan foydalanuvchi ID sini yuboring:", reply_markup=admin_back_kb())
    await callback.answer()


@router.message(BlockUserState.waiting_id)
async def block_manual_id(message: Message, state: FSMContext):
    if not message.text.strip().isdigit():
        await message.answer("ID raqam bo‘lishi kerak.", reply_markup=admin_back_kb())
        return
    data = await state.get_data()
    user_id = int(message.text.strip())
    if data.get("action") == "block":
        await db.set_block(user_id, True)
        await message.answer(f"🚫 Foydalanuvchi ({user_id}) bloklandi.", reply_markup=admin_main_kb())
    else:
        await db.set_block(user_id, False)
        await message.answer(f"✅ Foydalanuvchi ({user_id}) blokdan chiqarildi.", reply_markup=admin_main_kb())
    await state.clear()
