import aiosqlite
from datetime import datetime, timezone
from config import DB_PATH, DEFAULT_LANGUAGE

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    first_name TEXT,
    language TEXT DEFAULT 'uz',
    xp INTEGER DEFAULT 0,
    is_blocked INTEGER DEFAULT 0,
    joined_at TEXT,
    last_active TEXT,
    reminder_enabled INTEGER DEFAULT 1,
    reminder_hour INTEGER DEFAULT 18,
    reminder_minute INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS genres (
    genre_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name_uz TEXT,
    name_ru TEXT,
    name_en TEXT,
    parent_id INTEGER,
    FOREIGN KEY(parent_id) REFERENCES genres(genre_id)
);

CREATE TABLE IF NOT EXISTS books (
    book_id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    author TEXT,
    genre_id INTEGER,
    description TEXT,
    file_id TEXT,
    file_type TEXT,
    cover_file_id TEXT,
    language TEXT DEFAULT 'uz',
    year INTEGER,
    added_by INTEGER,
    added_at TEXT,
    downloads INTEGER DEFAULT 0,
    views INTEGER DEFAULT 0,
    rating_sum INTEGER DEFAULT 0,
    rating_count INTEGER DEFAULT 0,
    is_premium INTEGER DEFAULT 0,
    is_archived INTEGER DEFAULT 0,
    full_text TEXT,
    FOREIGN KEY(genre_id) REFERENCES genres(genre_id)
);

CREATE TABLE IF NOT EXISTS favorites (
    user_id INTEGER,
    book_id INTEGER,
    added_at TEXT,
    PRIMARY KEY(user_id, book_id)
);

CREATE TABLE IF NOT EXISTS history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    book_id INTEGER,
    action TEXT,
    ts TEXT
);

CREATE TABLE IF NOT EXISTS shelves (
    user_id INTEGER,
    book_id INTEGER,
    status TEXT,
    updated_at TEXT,
    PRIMARY KEY(user_id, book_id)
);

CREATE TABLE IF NOT EXISTS reading_progress (
    user_id INTEGER,
    book_id INTEGER,
    page INTEGER DEFAULT 0,
    updated_at TEXT,
    PRIMARY KEY(user_id, book_id)
);

CREATE TABLE IF NOT EXISTS reviews (
    review_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    book_id INTEGER,
    rating INTEGER,
    text TEXT,
    created_at TEXT
);

CREATE TABLE IF NOT EXISTS promo_codes (
    code TEXT PRIMARY KEY,
    xp_reward INTEGER,
    uses_left INTEGER,
    created_by INTEGER,
    created_at TEXT
);

CREATE TABLE IF NOT EXISTS promo_redemptions (
    code TEXT,
    user_id INTEGER,
    redeemed_at TEXT,
    PRIMARY KEY(code, user_id)
);

CREATE TABLE IF NOT EXISTS feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    text TEXT,
    created_at TEXT,
    status TEXT DEFAULT 'new'
);

CREATE TABLE IF NOT EXISTS quiz_questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id INTEGER,
    question TEXT,
    option_a TEXT,
    option_b TEXT,
    option_c TEXT,
    option_d TEXT,
    correct_option TEXT
);

CREATE TABLE IF NOT EXISTS quiz_answers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    question_id INTEGER,
    is_correct INTEGER,
    answered_at TEXT
);

CREATE TABLE IF NOT EXISTS genre_subscriptions (
    user_id INTEGER,
    genre_id INTEGER,
    PRIMARY KEY(user_id, genre_id)
);

CREATE TABLE IF NOT EXISTS referrals (
    user_id INTEGER PRIMARY KEY,
    referred_by INTEGER,
    joined_at TEXT
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT
);

CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    admin_id INTEGER,
    action TEXT,
    details TEXT,
    ts TEXT
);
"""

def now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("PRAGMA journal_mode=WAL")
        await db.executescript(SCHEMA)
        await db.commit()
        # Seed default genres if empty
        cur = await db.execute("SELECT COUNT(*) FROM genres")
        (count,) = await cur.fetchone()
        if count == 0:
            defaults = [
                ("Badiiy adabiyot", "Художественная литература", "Fiction", None),
                ("Biznes", "Бизнес", "Business", None),
                ("Psixologiya", "Психология", "Psychology", None),
                ("Ilmiy-ommabop", "Научно-популярная", "Popular Science", None),
                ("Tarix", "История", "History", None),
                ("Motivatsiya", "Мотивация", "Self-help", None),
            ]
            for uz, ru, en, parent in defaults:
                await db.execute(
                    "INSERT INTO genres (name_uz, name_ru, name_en, parent_id) VALUES (?,?,?,?)",
                    (uz, ru, en, parent),
                )
            await db.commit()


async def get_conn():
    return await aiosqlite.connect(DB_PATH)


# ---------- USERS ----------
async def get_or_create_user(user_id: int, username: str | None, first_name: str | None, referred_by: int | None = None):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
        row = await cur.fetchone()
        if row is None:
            await db.execute(
                "INSERT INTO users (user_id, username, first_name, language, joined_at, last_active) VALUES (?,?,?,?,?,?)",
                (user_id, username, first_name, DEFAULT_LANGUAGE, now(), now()),
            )
            if referred_by and referred_by != user_id:
                cur2 = await db.execute("SELECT 1 FROM users WHERE user_id=?", (referred_by,))
                exists = await cur2.fetchone()
                if exists:
                    await db.execute(
                        "INSERT OR IGNORE INTO referrals (user_id, referred_by, joined_at) VALUES (?,?,?)",
                        (user_id, referred_by, now()),
                    )
                    await db.execute(
                        "UPDATE users SET xp = xp + 10 WHERE user_id=?", (referred_by,)
                    )
            await db.commit()
            return True
        else:
            await db.execute("UPDATE users SET last_active=? WHERE user_id=?", (now(), user_id))
            await db.commit()
            return False


async def set_language(user_id: int, lang: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET language=? WHERE user_id=?", (lang, user_id))
        await db.commit()


async def get_language(user_id: int) -> str:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT language FROM users WHERE user_id=?", (user_id,))
        row = await cur.fetchone()
        return row[0] if row and row[0] else DEFAULT_LANGUAGE


async def add_xp(user_id: int, amount: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET xp = xp + ? WHERE user_id=?", (amount, user_id))
        await db.commit()


async def get_user(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
        return await cur.fetchone()


async def set_block(user_id: int, blocked: bool):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET is_blocked=? WHERE user_id=?", (1 if blocked else 0, user_id))
        await db.commit()


async def all_user_ids(only_active: bool = False):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT user_id FROM users WHERE is_blocked=0")
        rows = await cur.fetchall()
        return [r[0] for r in rows]


async def recent_users(limit: int = 20):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM users WHERE is_blocked=0 ORDER BY last_active DESC LIMIT ?", (limit,)
        )
        return await cur.fetchall()


async def blocked_users(limit: int = 50):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM users WHERE is_blocked=1 ORDER BY last_active DESC LIMIT ?", (limit,)
        )
        return await cur.fetchall()


async def genre_subscribers(genre_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT user_id FROM genre_subscriptions WHERE genre_id=?", (genre_id,))
        rows = await cur.fetchall()
        return [r[0] for r in rows]


# ---------- GENRES ----------
async def get_top_genres():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM genres WHERE parent_id IS NULL ORDER BY genre_id")
        return await cur.fetchall()


async def get_subgenres(parent_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM genres WHERE parent_id=? ORDER BY genre_id", (parent_id,))
        return await cur.fetchall()


async def get_genre(genre_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM genres WHERE genre_id=?", (genre_id,))
        return await cur.fetchone()


async def add_genre(name_uz, name_ru, name_en, parent_id=None):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "INSERT INTO genres (name_uz, name_ru, name_en, parent_id) VALUES (?,?,?,?)",
            (name_uz, name_ru, name_en, parent_id),
        )
        await db.commit()
        return cur.lastrowid


# ---------- BOOKS ----------
async def add_book(title, author, genre_id, description, file_id, file_type, added_by, year=None, cover_file_id=None, is_premium=0):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            """INSERT INTO books (title, author, genre_id, description, file_id, file_type,
               cover_file_id, year, added_by, added_at, is_premium)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (title, author, genre_id, description, file_id, file_type, cover_file_id, year, added_by, now(), is_premium),
        )
        await db.commit()
        return cur.lastrowid


async def edit_book_field(book_id: int, field: str, value):
    allowed = {"title", "author", "genre_id", "description", "file_id", "file_type",
               "cover_file_id", "year", "is_premium", "is_archived"}
    if field not in allowed:
        raise ValueError("Field not editable")
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(f"UPDATE books SET {field}=? WHERE book_id=?", (value, book_id))
        await db.commit()


async def delete_book(book_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM books WHERE book_id=?", (book_id,))
        await db.commit()


async def get_book(book_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM books WHERE book_id=? AND is_archived=0", (book_id,))
        return await cur.fetchone()


async def search_books(query: str, limit: int = 15):
    like = f"%{query}%"
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            """SELECT * FROM books WHERE is_archived=0 AND (title LIKE ? OR author LIKE ?)
               ORDER BY downloads DESC LIMIT ?""",
            (like, like, limit),
        )
        return await cur.fetchall()


async def check_duplicate(title: str, author: str) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT 1 FROM books WHERE lower(title)=lower(?) AND lower(author)=lower(?) AND is_archived=0",
            (title, author),
        )
        return (await cur.fetchone()) is not None


async def books_by_genre(genre_id: int, limit: int = 20, offset: int = 0):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM books WHERE genre_id=? AND is_archived=0 ORDER BY added_at DESC LIMIT ? OFFSET ?",
            (genre_id, limit, offset),
        )
        return await cur.fetchall()


async def similar_books(genre_id: int, exclude_book_id: int, limit: int = 5):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            """SELECT * FROM books WHERE genre_id=? AND book_id!=? AND is_archived=0
               ORDER BY (rating_sum * 1.0 / MAX(rating_count,1)) DESC, downloads DESC LIMIT ?""",
            (genre_id, exclude_book_id, limit),
        )
        return await cur.fetchall()


async def top_books(limit: int = 10):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM books WHERE is_archived=0 ORDER BY downloads DESC LIMIT ?", (limit,)
        )
        return await cur.fetchall()


async def increment_downloads(book_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE books SET downloads = downloads + 1 WHERE book_id=?", (book_id,))
        await db.commit()


async def increment_views(book_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE books SET views = views + 1 WHERE book_id=?", (book_id,))
        await db.commit()


async def set_full_text(book_id: int, text: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE books SET full_text=? WHERE book_id=?", (text, book_id))
        await db.commit()


async def books_count():
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT COUNT(*) FROM books WHERE is_archived=0")
        (c,) = await cur.fetchone()
        return c


async def list_books(limit: int = 30, offset: int = 0):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM books WHERE is_archived=0 ORDER BY added_at DESC LIMIT ? OFFSET ?",
            (limit, offset),
        )
        return await cur.fetchall()


async def users_count():
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT COUNT(*) FROM users")
        (c,) = await cur.fetchone()
        return c


async def today_new_users():
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT COUNT(*) FROM users WHERE date(joined_at)=date('now')"
        )
        (c,) = await cur.fetchone()
        return c


# ---------- FAVORITES ----------
async def add_favorite(user_id: int, book_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO favorites (user_id, book_id, added_at) VALUES (?,?,?)",
            (user_id, book_id, now()),
        )
        await db.commit()


async def remove_favorite(user_id: int, book_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM favorites WHERE user_id=? AND book_id=?", (user_id, book_id))
        await db.commit()


async def is_favorite(user_id: int, book_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT 1 FROM favorites WHERE user_id=? AND book_id=?", (user_id, book_id))
        return (await cur.fetchone()) is not None


async def list_favorites(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            """SELECT b.* FROM favorites f JOIN books b ON b.book_id=f.book_id
               WHERE f.user_id=? AND b.is_archived=0 ORDER BY f.added_at DESC""",
            (user_id,),
        )
        return await cur.fetchall()


# ---------- HISTORY ----------
async def log_history(user_id: int, book_id: int | None, action: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO history (user_id, book_id, action, ts) VALUES (?,?,?,?)",
            (user_id, book_id, action, now()),
        )
        await db.commit()


async def get_history(user_id: int, limit: int = 15):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            """SELECT h.action, h.ts, b.book_id, b.title, b.author FROM history h
               LEFT JOIN books b ON b.book_id=h.book_id
               WHERE h.user_id=? ORDER BY h.ts DESC LIMIT ?""",
            (user_id, limit),
        )
        return await cur.fetchall()


# ---------- SHELVES ----------
async def set_shelf(user_id: int, book_id: int, status: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO shelves (user_id, book_id, status, updated_at) VALUES (?,?,?,?)
               ON CONFLICT(user_id, book_id) DO UPDATE SET status=excluded.status, updated_at=excluded.updated_at""",
            (user_id, book_id, status, now()),
        )
        await db.commit()


async def get_shelf(user_id: int, status: str):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            """SELECT b.* FROM shelves s JOIN books b ON b.book_id=s.book_id
               WHERE s.user_id=? AND s.status=? AND b.is_archived=0 ORDER BY s.updated_at DESC""",
            (user_id, status),
        )
        return await cur.fetchall()


# ---------- READING PROGRESS ----------
async def set_progress(user_id: int, book_id: int, page: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO reading_progress (user_id, book_id, page, updated_at) VALUES (?,?,?,?)
               ON CONFLICT(user_id, book_id) DO UPDATE SET page=excluded.page, updated_at=excluded.updated_at""",
            (user_id, book_id, page, now()),
        )
        await db.commit()


async def get_progress(user_id: int, book_id: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT page FROM reading_progress WHERE user_id=? AND book_id=?", (user_id, book_id)
        )
        row = await cur.fetchone()
        return row[0] if row else 0


# ---------- REVIEWS ----------
async def add_review(user_id: int, book_id: int, rating: int, text: str | None):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO reviews (user_id, book_id, rating, text, created_at) VALUES (?,?,?,?,?)",
            (user_id, book_id, rating, text, now()),
        )
        await db.execute(
            "UPDATE books SET rating_sum = rating_sum + ?, rating_count = rating_count + 1 WHERE book_id=?",
            (rating, book_id),
        )
        await db.commit()


async def get_reviews(book_id: int, limit: int = 10):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            """SELECT r.*, u.first_name, u.username FROM reviews r JOIN users u ON u.user_id=r.user_id
               WHERE r.book_id=? ORDER BY r.created_at DESC LIMIT ?""",
            (book_id, limit),
        )
        return await cur.fetchall()


async def user_already_reviewed(user_id: int, book_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT 1 FROM reviews WHERE user_id=? AND book_id=?", (user_id, book_id))
        return (await cur.fetchone()) is not None


# ---------- PROMO CODES ----------
async def create_promo(code: str, xp_reward: int, uses: int, created_by: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO promo_codes (code, xp_reward, uses_left, created_by, created_at) VALUES (?,?,?,?,?)",
            (code, xp_reward, uses, created_by, now()),
        )
        await db.commit()


async def redeem_promo(code: str, user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT xp_reward, uses_left FROM promo_codes WHERE code=?", (code,))
        row = await cur.fetchone()
        if not row:
            return None, "not_found"
        xp_reward, uses_left = row
        if uses_left <= 0:
            return None, "exhausted"
        cur2 = await db.execute("SELECT 1 FROM promo_redemptions WHERE code=? AND user_id=?", (code, user_id))
        if await cur2.fetchone():
            return None, "already_used"
        await db.execute(
            "INSERT INTO promo_redemptions (code, user_id, redeemed_at) VALUES (?,?,?)",
            (code, user_id, now()),
        )
        await db.execute("UPDATE promo_codes SET uses_left = uses_left - 1 WHERE code=?", (code,))
        await db.execute("UPDATE users SET xp = xp + ? WHERE user_id=?", (xp_reward, user_id))
        await db.commit()
        return xp_reward, "ok"


# ---------- FEEDBACK ----------
async def add_feedback(user_id: int, text: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO feedback (user_id, text, created_at) VALUES (?,?,?)", (user_id, text, now())
        )
        await db.commit()


async def list_feedback(limit: int = 20):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM feedback ORDER BY created_at DESC LIMIT ?", (limit,)
        )
        return await cur.fetchall()


# ---------- QUIZ ----------
async def add_quiz_question(book_id, question, a, b, c, d, correct):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO quiz_questions (book_id, question, option_a, option_b, option_c, option_d, correct_option)
               VALUES (?,?,?,?,?,?,?)""",
            (book_id, question, a, b, c, d, correct),
        )
        await db.commit()


async def get_quiz_for_book(book_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM quiz_questions WHERE book_id=? ORDER BY RANDOM() LIMIT 1", (book_id,))
        return await cur.fetchone()


async def get_quiz_question(question_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM quiz_questions WHERE id=?", (question_id,))
        return await cur.fetchone()


async def get_random_quiz():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM quiz_questions ORDER BY RANDOM() LIMIT 1")
        return await cur.fetchone()


async def log_quiz_answer(user_id, question_id, is_correct: bool):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO quiz_answers (user_id, question_id, is_correct, answered_at) VALUES (?,?,?,?)",
            (user_id, question_id, 1 if is_correct else 0, now()),
        )
        await db.commit()


# ---------- GENRE SUBSCRIPTIONS ----------
async def subscribe_genre(user_id: int, genre_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO genre_subscriptions (user_id, genre_id) VALUES (?,?)", (user_id, genre_id)
        )
        await db.commit()


async def unsubscribe_genre(user_id: int, genre_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM genre_subscriptions WHERE user_id=? AND genre_id=?", (user_id, genre_id)
        )
        await db.commit()


async def is_subscribed_genre(user_id: int, genre_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT 1 FROM genre_subscriptions WHERE user_id=? AND genre_id=?", (user_id, genre_id)
        )
        return (await cur.fetchone()) is not None


# ---------- LEADERBOARD ----------
async def xp_leaderboard(limit: int = 10):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT user_id, first_name, username, xp FROM users ORDER BY xp DESC LIMIT ?", (limit,)
        )
        return await cur.fetchall()


async def users_with_reminder():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT user_id, reminder_hour, reminder_minute FROM users WHERE reminder_enabled=1 AND is_blocked=0"
        )
        return await cur.fetchall()


async def set_reminder(user_id: int, enabled: bool, hour: int = None, minute: int = None):
    async with aiosqlite.connect(DB_PATH) as db:
        if hour is not None and minute is not None:
            await db.execute(
                "UPDATE users SET reminder_enabled=?, reminder_hour=?, reminder_minute=? WHERE user_id=?",
                (1 if enabled else 0, hour, minute, user_id),
            )
        else:
            await db.execute(
                "UPDATE users SET reminder_enabled=? WHERE user_id=?", (1 if enabled else 0, user_id)
            )
        await db.commit()


# ---------- SETTINGS (key-value) ----------
async def get_setting(key: str, default=None):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT value FROM settings WHERE key=?", (key,))
        row = await cur.fetchone()
        return row[0] if row else default


async def set_setting(key: str, value: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO settings (key, value) VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value),
        )
        await db.commit()


# ---------- AUDIT LOG ----------
async def log_audit(admin_id: int, action: str, details: str = ""):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO audit_log (admin_id, action, details, ts) VALUES (?,?,?,?)",
            (admin_id, action, details, now()),
        )
        await db.commit()


async def get_audit_log(limit: int = 50):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM audit_log ORDER BY ts DESC LIMIT ?", (limit,))
        return await cur.fetchall()


# ---------- WEB PANEL HELPERS ----------
async def search_users(query: str, limit: int = 30):
    like = f"%{query}%"
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            """SELECT * FROM users WHERE CAST(user_id AS TEXT) LIKE ? OR username LIKE ? OR first_name LIKE ?
               ORDER BY joined_at DESC LIMIT ?""",
            (like, like, like, limit),
        )
        return await cur.fetchall()


async def all_users_paginated(limit: int = 30, offset: int = 0):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM users ORDER BY joined_at DESC LIMIT ? OFFSET ?", (limit, offset)
        )
        return await cur.fetchall()


async def set_xp(user_id: int, xp: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET xp=? WHERE user_id=?", (xp, user_id))
        await db.commit()


async def all_books_admin(limit: int = 500, include_archived: bool = True):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        if include_archived:
            cur = await db.execute("SELECT * FROM books ORDER BY added_at DESC LIMIT ?", (limit,))
        else:
            cur = await db.execute(
                "SELECT * FROM books WHERE is_archived=0 ORDER BY added_at DESC LIMIT ?", (limit,)
            )
        return await cur.fetchall()


async def search_books_admin(query: str, limit: int = 100):
    like = f"%{query}%"
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM books WHERE title LIKE ? OR author LIKE ? ORDER BY added_at DESC LIMIT ?",
            (like, like, limit),
        )
        return await cur.fetchall()


async def get_book_any(book_id: int):
    """Archived bo'lsa ham (admin uchun) kitobni qaytaradi."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM books WHERE book_id=?", (book_id,))
        return await cur.fetchone()


async def find_duplicates():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            """SELECT lower(title) t, lower(author) a, COUNT(*) c, GROUP_CONCAT(book_id) ids
               FROM books WHERE is_archived=0 GROUP BY t, a HAVING c > 1"""
        )
        return await cur.fetchall()


async def all_genres_flat():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM genres ORDER BY parent_id IS NULL DESC, parent_id, genre_id")
        return await cur.fetchall()


async def delete_genre(genre_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE books SET genre_id=NULL WHERE genre_id=?", (genre_id,))
        await db.execute("DELETE FROM genres WHERE genre_id=?", (genre_id,))
        await db.commit()


async def search_analytics(limit: int = 20):
    """So'nggi qidiruv so'zlari va ular necha marta qidirilgani."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            """SELECT substr(action, 8) AS query, COUNT(*) AS cnt FROM history
               WHERE action LIKE 'search:%' GROUP BY query ORDER BY cnt DESC LIMIT ?""",
            (limit,),
        )
        return await cur.fetchall()


async def user_growth(days: int = 14):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            """SELECT date(joined_at) AS day, COUNT(*) AS cnt FROM users
               WHERE joined_at >= date('now', ?) GROUP BY day ORDER BY day""",
            (f"-{days} days",),
        )
        return await cur.fetchall()


async def dau(days: int = 14):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            """SELECT date(last_active) AS day, COUNT(*) AS cnt FROM users
               WHERE last_active >= date('now', ?) GROUP BY day ORDER BY day""",
            (f"-{days} days",),
        )
        return await cur.fetchall()


async def all_reviews(limit: int = 50):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            """SELECT r.*, b.title AS book_title, u.first_name, u.username FROM reviews r
               JOIN books b ON b.book_id = r.book_id
               JOIN users u ON u.user_id = r.user_id
               ORDER BY r.created_at DESC LIMIT ?""",
            (limit,),
        )
        return await cur.fetchall()


async def delete_review(review_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT book_id, rating FROM reviews WHERE review_id=?", (review_id,))
        row = await cur.fetchone()
        if row:
            book_id, rating = row
            await db.execute(
                "UPDATE books SET rating_sum = rating_sum - ?, rating_count = rating_count - 1 WHERE book_id=?",
                (rating, book_id),
            )
        await db.execute("DELETE FROM reviews WHERE review_id=?", (review_id,))
        await db.commit()


async def resolve_feedback(feedback_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE feedback SET status='resolved' WHERE id=?", (feedback_id,))
        await db.commit()


async def all_promos():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM promo_codes ORDER BY created_at DESC")
        return await cur.fetchall()


async def all_quiz_questions(limit: int = 100):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            """SELECT q.*, b.title AS book_title FROM quiz_questions q
               LEFT JOIN books b ON b.book_id = q.book_id ORDER BY q.id DESC LIMIT ?""",
            (limit,),
        )
        return await cur.fetchall()


async def delete_quiz_question(question_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM quiz_questions WHERE id=?", (question_id,))
        await db.commit()
