import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, Request, Form, UploadFile, File
from fastapi.responses import RedirectResponse, FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

import database as db
from config import SESSION_SECRET, DB_PATH, ADMIN_IDS, BOOK_CLUB_CHAT_LINK, WEBPANEL_PORT
from webpanel.auth import check_credentials, is_logged_in
from webpanel import telegram_api as tg

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = FastAPI(title="Kitoblar Bot — Admin Panel")
app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET)
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))


def ctx(request: Request, **kwargs):
    data = {"request": request, "admin_username": request.session.get("username", "")}
    data.update(kwargs)
    return data


def need_login(request: Request):
    if not is_logged_in(request):
        return RedirectResponse(url="/login", status_code=302)
    return None


# ============================================================
# AUTH
# ============================================================
@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, error: str = ""):
    if is_logged_in(request):
        return RedirectResponse(url="/", status_code=302)
    return templates.TemplateResponse("login.html", ctx(request, error=error))


@app.post("/login")
async def login_submit(request: Request, username: str = Form(...), password: str = Form(...)):
    if check_credentials(username, password):
        request.session["logged_in"] = True
        request.session["username"] = username
        return RedirectResponse(url="/", status_code=302)
    return RedirectResponse(url="/login?error=1", status_code=302)


@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=302)


# ============================================================
# DASHBOARD
# ============================================================
@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    if (r := need_login(request)):
        return r
    users = await db.users_count()
    new_today = await db.today_new_users()
    books = await db.books_count()
    top = await db.top_books(5)
    feedback = await db.list_feedback(5)
    duplicates = await db.find_duplicates()
    return templates.TemplateResponse("dashboard.html", ctx(
        request, users=users, new_today=new_today, books=books,
        top=top, feedback=feedback, duplicates=duplicates,
    ))


# ============================================================
# BOOKS
# ============================================================
@app.get("/books", response_class=HTMLResponse)
async def books_list(request: Request, q: str = ""):
    if (r := need_login(request)):
        return r
    books = await db.search_books_admin(q) if q else await db.all_books_admin()
    return templates.TemplateResponse("books.html", ctx(request, books=books, q=q))


@app.get("/books/new", response_class=HTMLResponse)
async def book_new_form(request: Request):
    if (r := need_login(request)):
        return r
    genres = await db.all_genres_flat()
    return templates.TemplateResponse("book_form.html", ctx(request, book=None, genres=genres))


@app.post("/books/new")
async def book_new_submit(
    request: Request,
    title: str = Form(...), author: str = Form(""), genre_id: int = Form(...),
    description: str = Form(""), year: int = Form(0), is_premium: bool = Form(False),
    file: UploadFile = File(...), cover: UploadFile = File(None),
):
    if (r := need_login(request)):
        return r
    file_bytes = await file.read()
    file_id = await tg.upload_document_get_file_id(file_bytes, file.filename)
    file_type = file.filename.split(".")[-1].lower() if "." in file.filename else ""
    cover_file_id = None
    if cover and cover.filename:
        cover_bytes = await cover.read()
        cover_file_id = await tg.upload_photo_get_file_id(cover_bytes, cover.filename)
    book_id = await db.add_book(
        title=title, author=author, genre_id=genre_id, description=description,
        file_id=file_id, file_type=file_type, added_by=0, year=year or None,
        is_premium=1 if is_premium else 0, cover_file_id=cover_file_id,
    )
    await db.log_audit(0, "add_book", f"web panel: {title} (id={book_id})")
    await tg.close_bot()
    return RedirectResponse(url="/books", status_code=302)


@app.get("/books/{book_id}/edit", response_class=HTMLResponse)
async def book_edit_form(request: Request, book_id: int):
    if (r := need_login(request)):
        return r
    book = await db.get_book_any(book_id)
    genres = await db.all_genres_flat()
    return templates.TemplateResponse("book_form.html", ctx(request, book=book, genres=genres))


@app.post("/books/{book_id}/edit")
async def book_edit_submit(
    request: Request, book_id: int,
    title: str = Form(...), author: str = Form(""), genre_id: int = Form(...),
    description: str = Form(""), year: int = Form(0), is_premium: bool = Form(False),
    file: UploadFile = File(None), cover: UploadFile = File(None),
):
    if (r := need_login(request)):
        return r
    await db.edit_book_field(book_id, "title", title)
    await db.edit_book_field(book_id, "author", author)
    await db.edit_book_field(book_id, "genre_id", genre_id)
    await db.edit_book_field(book_id, "description", description)
    await db.edit_book_field(book_id, "year", year or None)
    await db.edit_book_field(book_id, "is_premium", 1 if is_premium else 0)
    if file and file.filename:
        file_bytes = await file.read()
        file_id = await tg.upload_document_get_file_id(file_bytes, file.filename)
        file_type = file.filename.split(".")[-1].lower() if "." in file.filename else ""
        await db.edit_book_field(book_id, "file_id", file_id)
        await db.edit_book_field(book_id, "file_type", file_type)
    if cover and cover.filename:
        cover_bytes = await cover.read()
        cover_file_id = await tg.upload_photo_get_file_id(cover_bytes, cover.filename)
        await db.edit_book_field(book_id, "cover_file_id", cover_file_id)
    if (file and file.filename) or (cover and cover.filename):
        await tg.close_bot()
    await db.log_audit(0, "edit_book", f"web panel: book_id={book_id}")
    return RedirectResponse(url="/books", status_code=302)


@app.post("/books/{book_id}/delete")
async def book_delete(request: Request, book_id: int):
    if (r := need_login(request)):
        return r
    await db.delete_book(book_id)
    await db.log_audit(0, "delete_book", f"web panel: book_id={book_id}")
    return RedirectResponse(url="/books", status_code=302)


@app.post("/books/{book_id}/archive")
async def book_archive_toggle(request: Request, book_id: int):
    if (r := need_login(request)):
        return r
    book = await db.get_book_any(book_id)
    new_val = 0 if book["is_archived"] else 1
    await db.edit_book_field(book_id, "is_archived", new_val)
    return RedirectResponse(url="/books", status_code=302)


@app.get("/books/{book_id}/settext", response_class=HTMLResponse)
async def settext_form(request: Request, book_id: int):
    if (r := need_login(request)):
        return r
    book = await db.get_book_any(book_id)
    return templates.TemplateResponse("settext.html", ctx(request, book=book))


@app.post("/books/{book_id}/settext")
async def settext_submit(request: Request, book_id: int, full_text: str = Form(...)):
    if (r := need_login(request)):
        return r
    await db.set_full_text(book_id, full_text)
    return RedirectResponse(url="/books", status_code=302)


# ============================================================
# GENRES
# ============================================================
@app.get("/genres", response_class=HTMLResponse)
async def genres_page(request: Request):
    if (r := need_login(request)):
        return r
    genres = await db.all_genres_flat()
    top_genres = await db.get_top_genres()
    return templates.TemplateResponse("genres.html", ctx(request, genres=genres, top_genres=top_genres))


@app.post("/genres/new")
async def genre_new(
    request: Request, name_uz: str = Form(...), name_ru: str = Form(""),
    name_en: str = Form(""), parent_id: str = Form(""),
):
    if (r := need_login(request)):
        return r
    parent = int(parent_id) if parent_id else None
    await db.add_genre(name_uz, name_ru, name_en, parent)
    return RedirectResponse(url="/genres", status_code=302)


@app.post("/genres/{genre_id}/delete")
async def genre_delete(request: Request, genre_id: int):
    if (r := need_login(request)):
        return r
    await db.delete_genre(genre_id)
    return RedirectResponse(url="/genres", status_code=302)


# ============================================================
# USERS
# ============================================================
@app.get("/users", response_class=HTMLResponse)
async def users_page(request: Request, q: str = ""):
    if (r := need_login(request)):
        return r
    users = await db.search_users(q) if q else await db.all_users_paginated()
    return templates.TemplateResponse("users.html", ctx(request, users=users, q=q))


@app.get("/users/{user_id}", response_class=HTMLResponse)
async def user_detail(request: Request, user_id: int):
    if (r := need_login(request)):
        return r
    user = await db.get_user(user_id)
    favorites = await db.list_favorites(user_id)
    history = await db.get_history(user_id, limit=25)
    return templates.TemplateResponse("user_detail.html", ctx(
        request, user=user, favorites=favorites, history=history,
    ))


@app.post("/users/{user_id}/block")
async def user_block(request: Request, user_id: int):
    if (r := need_login(request)):
        return r
    await db.set_block(user_id, True)
    return RedirectResponse(url=f"/users/{user_id}", status_code=302)


@app.post("/users/{user_id}/unblock")
async def user_unblock(request: Request, user_id: int):
    if (r := need_login(request)):
        return r
    await db.set_block(user_id, False)
    return RedirectResponse(url=f"/users/{user_id}", status_code=302)


@app.post("/users/{user_id}/xp")
async def user_set_xp(request: Request, user_id: int, xp: int = Form(...)):
    if (r := need_login(request)):
        return r
    await db.set_xp(user_id, xp)
    return RedirectResponse(url=f"/users/{user_id}", status_code=302)


@app.post("/users/{user_id}/message")
async def user_send_message(request: Request, user_id: int, text: str = Form(...)):
    if (r := need_login(request)):
        return r
    await tg.send_message_to_user(user_id, text)
    await tg.close_bot()
    return RedirectResponse(url=f"/users/{user_id}", status_code=302)


# ============================================================
# BROADCAST
# ============================================================
@app.get("/broadcast", response_class=HTMLResponse)
async def broadcast_page(request: Request):
    if (r := need_login(request)):
        return r
    users = await db.users_count()
    return templates.TemplateResponse("broadcast.html", ctx(request, users=users))


@app.post("/broadcast")
async def broadcast_submit(request: Request, text: str = Form(...), photo: UploadFile = File(None)):
    if (r := need_login(request)):
        return r
    user_ids = await db.all_user_ids()
    photo_bytes = await photo.read() if (photo and photo.filename) else None
    filename = photo.filename if photo else "image.jpg"
    sent, failed = await tg.broadcast_text(user_ids, text, photo_bytes, filename)
    await tg.close_bot()
    await db.log_audit(0, "broadcast", f"sent={sent} failed={failed}")
    return templates.TemplateResponse("broadcast.html", ctx(request, users=len(user_ids), result=(sent, failed)))


# ============================================================
# PROMO CODES
# ============================================================
@app.get("/promo", response_class=HTMLResponse)
async def promo_page(request: Request):
    if (r := need_login(request)):
        return r
    promos = await db.all_promos()
    return templates.TemplateResponse("promo.html", ctx(request, promos=promos))


@app.post("/promo/new")
async def promo_new(request: Request, code: str = Form(...), xp_reward: int = Form(...), uses: int = Form(...)):
    if (r := need_login(request)):
        return r
    await db.create_promo(code.strip().upper(), xp_reward, uses, 0)
    return RedirectResponse(url="/promo", status_code=302)


# ============================================================
# QUIZ
# ============================================================
@app.get("/quiz", response_class=HTMLResponse)
async def quiz_page(request: Request):
    if (r := need_login(request)):
        return r
    questions = await db.all_quiz_questions()
    books = await db.all_books_admin(include_archived=False)
    return templates.TemplateResponse("quiz.html", ctx(request, questions=questions, books=books))


@app.post("/quiz/new")
async def quiz_new(
    request: Request, book_id: str = Form(""), question: str = Form(...),
    option_a: str = Form(...), option_b: str = Form(...),
    option_c: str = Form(""), option_d: str = Form(""), correct: str = Form(...),
):
    if (r := need_login(request)):
        return r
    bid = int(book_id) if book_id else None
    await db.add_quiz_question(bid, question, option_a, option_b, option_c or None, option_d or None, correct)
    return RedirectResponse(url="/quiz", status_code=302)


@app.post("/quiz/{question_id}/delete")
async def quiz_delete(request: Request, question_id: int):
    if (r := need_login(request)):
        return r
    await db.delete_quiz_question(question_id)
    return RedirectResponse(url="/quiz", status_code=302)


# ============================================================
# FEEDBACK
# ============================================================
@app.get("/feedback", response_class=HTMLResponse)
async def feedback_page(request: Request):
    if (r := need_login(request)):
        return r
    items = await db.list_feedback(100)
    return templates.TemplateResponse("feedback.html", ctx(request, items=items))


@app.post("/feedback/{feedback_id}/resolve")
async def feedback_resolve(request: Request, feedback_id: int):
    if (r := need_login(request)):
        return r
    await db.resolve_feedback(feedback_id)
    return RedirectResponse(url="/feedback", status_code=302)


# ============================================================
# REVIEWS
# ============================================================
@app.get("/reviews", response_class=HTMLResponse)
async def reviews_page(request: Request):
    if (r := need_login(request)):
        return r
    reviews = await db.all_reviews(100)
    return templates.TemplateResponse("reviews.html", ctx(request, reviews=reviews))


@app.post("/reviews/{review_id}/delete")
async def review_delete(request: Request, review_id: int):
    if (r := need_login(request)):
        return r
    await db.delete_review(review_id)
    return RedirectResponse(url="/reviews", status_code=302)


# ============================================================
# ANALYTICS
# ============================================================
@app.get("/analytics", response_class=HTMLResponse)
async def analytics_page(request: Request):
    if (r := need_login(request)):
        return r
    import json
    growth = await db.user_growth(30)
    active = await db.dau(30)
    top = await db.top_books(10)
    searches = await db.search_analytics(20)
    duplicates = await db.find_duplicates()
    growth_json = json.dumps([{"day": row["day"], "cnt": row["cnt"]} for row in growth])
    active_json = json.dumps([{"day": row["day"], "cnt": row["cnt"]} for row in active])
    return templates.TemplateResponse("analytics.html", ctx(
        request, growth=growth, active=active, top=top, searches=searches, duplicates=duplicates,
        growth_json=growth_json, active_json=active_json,
    ))


# ============================================================
# SETTINGS
# ============================================================
@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    if (r := need_login(request)):
        return r
    club_link = await db.get_setting("book_club_link", BOOK_CLUB_CHAT_LINK)
    maintenance = await db.get_setting("maintenance_mode", "0")
    reminder_hour = await db.get_setting("default_reminder_hour", "18")
    return templates.TemplateResponse("settings.html", ctx(
        request, club_link=club_link, maintenance=maintenance, reminder_hour=reminder_hour,
    ))


@app.post("/settings")
async def settings_submit(
    request: Request, club_link: str = Form(...), reminder_hour: int = Form(...),
    maintenance: str = Form("0"),
):
    if (r := need_login(request)):
        return r
    await db.set_setting("book_club_link", club_link)
    await db.set_setting("default_reminder_hour", str(reminder_hour))
    await db.set_setting("maintenance_mode", maintenance)
    return RedirectResponse(url="/settings", status_code=302)


# ============================================================
# BACKUP & AUDIT LOG
# ============================================================
@app.get("/backup")
async def backup_download(request: Request):
    if (r := need_login(request)):
        return r
    return FileResponse(DB_PATH, filename="books_backup.db", media_type="application/octet-stream")


@app.get("/audit-log", response_class=HTMLResponse)
async def audit_log_page(request: Request):
    if (r := need_login(request)):
        return r
    logs = await db.get_audit_log(100)
    return templates.TemplateResponse("audit_log.html", ctx(request, logs=logs))


# ============================================================
# ENTRYPOINT (uvicorn server run as an asyncio task from main.py)
# ============================================================
async def run_webpanel():
    import uvicorn
    from config import WEBPANEL_PORT
    await db.init_db()
    config = uvicorn.Config(app, host="0.0.0.0", port=WEBPANEL_PORT, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()


if __name__ == "__main__":
    import asyncio
    asyncio.run(run_webpanel())
