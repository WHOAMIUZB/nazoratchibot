import io
import math

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

import database as db
from config import PAGE_CHARS, XP_FOR_DOWNLOAD, XP_FOR_REVIEW, XP_FOR_QUIZ_CORRECT, BOOK_CLUB_CHAT_LINK
from miniapp.auth import get_current_user
from webpanel import telegram_api as tg

router = APIRouter()


# ============================================================
# Helpers
# ============================================================
def book_to_dict(b) -> dict:
    rating = round(b["rating_sum"] / b["rating_count"], 1) if b["rating_count"] else None
    return {
        "book_id": b["book_id"],
        "title": b["title"],
        "author": b["author"],
        "description": b["description"],
        "genre_id": b["genre_id"],
        "year": b["year"],
        "downloads": b["downloads"],
        "rating": rating,
        "rating_count": b["rating_count"],
        "is_premium": bool(b["is_premium"]),
        "has_cover": bool(b["cover_file_id"]),
        "has_text": bool(b["full_text"]),
    }


def genre_to_dict(g) -> dict:
    return {
        "genre_id": g["genre_id"], "name_uz": g["name_uz"], "name_ru": g["name_ru"],
        "name_en": g["name_en"], "parent_id": g["parent_id"],
    }


# ============================================================
# Pydantic payloads
# ============================================================
class LangPayload(BaseModel):
    lang: str


class ShelfPayload(BaseModel):
    status: str


class ReviewPayload(BaseModel):
    rating: int
    text: str | None = None


class QuizAnswerPayload(BaseModel):
    chosen: str


class PromoPayload(BaseModel):
    code: str


class FeedbackPayload(BaseModel):
    text: str


class ReminderPayload(BaseModel):
    enabled: bool
    hour: int | None = None


# ============================================================
# PROFILE
# ============================================================
@router.get("/me")
async def me(user: dict = Depends(get_current_user)):
    await db.get_or_create_user(user["id"], user.get("username"), user.get("first_name"))
    u = await db.get_user(user["id"])
    favorites = await db.list_favorites(user["id"])
    read_books = await db.get_shelf(user["id"], "read")
    club_link = await db.get_setting("book_club_link", BOOK_CLUB_CHAT_LINK)
    bot_username = await tg.get_bot_username()
    return {
        "user_id": u["user_id"], "first_name": u["first_name"], "username": u["username"],
        "language": u["language"], "xp": u["xp"],
        "reminder_enabled": bool(u["reminder_enabled"]), "reminder_hour": u["reminder_hour"],
        "favorites_count": len(favorites), "read_count": len(read_books),
        "club_link": club_link,
        "referral_link": f"https://t.me/{bot_username}?start=ref{u['user_id']}",
    }


@router.post("/language")
async def set_language(payload: LangPayload, user: dict = Depends(get_current_user)):
    await db.set_language(user["id"], payload.lang)
    return {"ok": True}


@router.post("/reminder")
async def set_reminder(payload: ReminderPayload, user: dict = Depends(get_current_user)):
    if payload.hour is not None:
        await db.set_reminder(user["id"], payload.enabled, payload.hour, 0)
    else:
        await db.set_reminder(user["id"], payload.enabled)
    return {"ok": True}


# ============================================================
# GENRES
# ============================================================
@router.get("/genres")
async def genres(parent_id: int | None = None, user: dict = Depends(get_current_user)):
    rows = await db.get_subgenres(parent_id) if parent_id else await db.get_top_genres()
    return [genre_to_dict(g) for g in rows]


@router.get("/genres/{genre_id}/books")
async def genre_books(genre_id: int, user: dict = Depends(get_current_user)):
    rows = await db.books_by_genre(genre_id, limit=100)
    return [book_to_dict(b) for b in rows]


@router.get("/genres/{genre_id}/subscribed")
async def genre_subscribed(genre_id: int, user: dict = Depends(get_current_user)):
    return {"subscribed": await db.is_subscribed_genre(user["id"], genre_id)}


@router.post("/genres/{genre_id}/subscribe")
async def genre_subscribe_toggle(genre_id: int, user: dict = Depends(get_current_user)):
    subscribed = await db.is_subscribed_genre(user["id"], genre_id)
    if subscribed:
        await db.unsubscribe_genre(user["id"], genre_id)
    else:
        await db.subscribe_genre(user["id"], genre_id)
    return {"subscribed": not subscribed}


# ============================================================
# SEARCH
# ============================================================
@router.get("/search")
async def search(q: str, user: dict = Depends(get_current_user)):
    q = q.strip()
    if not q:
        return []
    await db.log_history(user["id"], None, f"search:{q}")
    rows = await db.search_books(q, limit=40)
    return [book_to_dict(b) for b in rows]


# ============================================================
# BOOKS
# ============================================================
@router.get("/books/{book_id}")
async def book_detail(book_id: int, user: dict = Depends(get_current_user)):
    book = await db.get_book(book_id)
    if not book:
        raise HTTPException(404, "Kitob topilmadi")
    await db.increment_views(book_id)
    await db.log_history(user["id"], book_id, "view")
    data = book_to_dict(book)
    data["is_favorite"] = await db.is_favorite(user["id"], book_id)
    data["progress_page"] = await db.get_progress(user["id"], book_id)
    data["already_reviewed"] = await db.user_already_reviewed(user["id"], book_id)
    return data


@router.get("/books/{book_id}/text")
async def book_text(book_id: int, page: int = 0, user: dict = Depends(get_current_user)):
    book = await db.get_book(book_id)
    if not book or not book["full_text"]:
        raise HTTPException(404, "Matn topilmadi")
    if book["is_premium"]:
        raise HTTPException(403, "premium")
    text = book["full_text"]
    total_pages = max(1, math.ceil(len(text) / PAGE_CHARS))
    page = max(0, min(page, total_pages - 1))
    chunk = text[page * PAGE_CHARS:(page + 1) * PAGE_CHARS]
    await db.set_progress(user["id"], book_id, page)
    await db.log_history(user["id"], book_id, "read")
    return {"page": page, "total_pages": total_pages, "text": chunk, "title": book["title"]}


@router.get("/books/{book_id}/cover")
async def book_cover(book_id: int, user: dict = Depends(get_current_user)):
    book = await db.get_book_any(book_id)
    if not book or not book["cover_file_id"]:
        raise HTTPException(404, "Muqova yo'q")
    data, path = await tg.get_file_bytes(book["cover_file_id"])
    ext = path.rsplit(".", 1)[-1].lower() if "." in path else "jpg"
    mime_map = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp"}
    media_type = mime_map.get(ext, "image/jpeg")
    return StreamingResponse(io.BytesIO(data), media_type=media_type)


@router.get("/books/{book_id}/download")
async def book_download(book_id: int, user: dict = Depends(get_current_user)):
    book = await db.get_book(book_id)
    if not book:
        raise HTTPException(404, "Kitob topilmadi")
    if book["is_premium"]:
        raise HTTPException(403, "premium")
    if not book["file_id"]:
        raise HTTPException(404, "Fayl mavjud emas")
    data, _ = await tg.get_file_bytes(book["file_id"])
    await db.increment_downloads(book_id)
    await db.log_history(user["id"], book_id, "download")
    await db.add_xp(user["id"], XP_FOR_DOWNLOAD)
    ext = book["file_type"] or "pdf"
    safe_title = "".join(c for c in book["title"] if c.isalnum() or c in " -_").strip() or "kitob"
    return StreamingResponse(
        io.BytesIO(data), media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{safe_title}.{ext}"'},
    )


@router.get("/books/{book_id}/similar")
async def similar(book_id: int, user: dict = Depends(get_current_user)):
    book = await db.get_book(book_id)
    if not book or not book["genre_id"]:
        return []
    rows = await db.similar_books(book["genre_id"], book_id)
    return [book_to_dict(b) for b in rows]


@router.get("/books/{book_id}/reviews")
async def book_reviews(book_id: int, user: dict = Depends(get_current_user)):
    rows = await db.get_reviews(book_id)
    return [
        {"user": r["first_name"] or r["username"] or "Anonim", "rating": r["rating"],
         "text": r["text"], "created_at": r["created_at"]}
        for r in rows
    ]


@router.post("/books/{book_id}/review")
async def add_review(book_id: int, payload: ReviewPayload, user: dict = Depends(get_current_user)):
    if await db.user_already_reviewed(user["id"], book_id):
        raise HTTPException(400, "already_reviewed")
    if not (1 <= payload.rating <= 5):
        raise HTTPException(400, "rating 1-5 oralig'ida bo'lishi kerak")
    await db.add_review(user["id"], book_id, payload.rating, payload.text)
    await db.add_xp(user["id"], XP_FOR_REVIEW)
    return {"ok": True, "xp": XP_FOR_REVIEW}


@router.post("/books/{book_id}/favorite")
async def toggle_favorite(book_id: int, user: dict = Depends(get_current_user)):
    if await db.is_favorite(user["id"], book_id):
        await db.remove_favorite(user["id"], book_id)
        return {"is_favorite": False}
    await db.add_favorite(user["id"], book_id)
    return {"is_favorite": True}


@router.post("/books/{book_id}/shelf")
async def set_shelf(book_id: int, payload: ShelfPayload, user: dict = Depends(get_current_user)):
    if payload.status not in ("reading", "read", "planned"):
        raise HTTPException(400, "noto'g'ri holat")
    await db.set_shelf(user["id"], book_id, payload.status)
    return {"ok": True}


# ============================================================
# LISTS
# ============================================================
@router.get("/favorites")
async def favorites(user: dict = Depends(get_current_user)):
    rows = await db.list_favorites(user["id"])
    return [book_to_dict(b) for b in rows]


@router.get("/shelf")
async def shelf(status: str, user: dict = Depends(get_current_user)):
    rows = await db.get_shelf(user["id"], status)
    return [book_to_dict(b) for b in rows]


@router.get("/history")
async def history(user: dict = Depends(get_current_user)):
    rows = await db.get_history(user["id"], limit=40)
    return [
        {"action": h["action"], "ts": h["ts"], "book_id": h["book_id"], "title": h["title"]}
        for h in rows
    ]


@router.get("/top")
async def top(user: dict = Depends(get_current_user)):
    rows = await db.top_books(10)
    return [book_to_dict(b) for b in rows]


# ============================================================
# QUIZ
# ============================================================
@router.get("/quiz/random")
async def quiz_random(user: dict = Depends(get_current_user)):
    q = await db.get_random_quiz()
    if not q:
        return None
    options = {k: q[f"option_{k}"] for k in ("a", "b", "c", "d") if q[f"option_{k}"]}
    return {"id": q["id"], "question": q["question"], "options": options}


@router.post("/quiz/{question_id}/answer")
async def quiz_answer(question_id: int, payload: QuizAnswerPayload, user: dict = Depends(get_current_user)):
    q = await db.get_quiz_question(question_id)
    if not q:
        raise HTTPException(404, "Savol topilmadi")
    is_correct = payload.chosen == q["correct_option"]
    await db.log_quiz_answer(user["id"], question_id, is_correct)
    if is_correct:
        await db.add_xp(user["id"], XP_FOR_QUIZ_CORRECT)
    return {
        "correct": is_correct, "xp": XP_FOR_QUIZ_CORRECT if is_correct else 0,
        "correct_option": q["correct_option"], "correct_text": q[f"option_{q['correct_option']}"],
    }


# ============================================================
# PROMO CODES
# ============================================================
@router.post("/promo/redeem")
async def promo_redeem(payload: PromoPayload, user: dict = Depends(get_current_user)):
    xp, status = await db.redeem_promo(payload.code.strip().upper(), user["id"])
    return {"status": status, "xp": xp}


# ============================================================
# FEEDBACK
# ============================================================
@router.post("/feedback")
async def feedback(payload: FeedbackPayload, user: dict = Depends(get_current_user)):
    await db.add_feedback(user["id"], payload.text)
    return {"ok": True}
