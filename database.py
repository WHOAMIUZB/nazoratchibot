import time
import aiosqlite
from config import DB_PATH, SUPER_ADMIN_ID

_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    full_name TEXT,
    first_seen INTEGER,
    is_banned_from_bot INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS bot_admins (
    user_id INTEGER PRIMARY KEY,
    added_by INTEGER,
    added_at INTEGER
);

CREATE TABLE IF NOT EXISTS channels (
    channel_id INTEGER PRIMARY KEY,
    owner_id INTEGER,
    title TEXT,
    username TEXT,
    clean_deleted_enabled INTEGER DEFAULT 0,
    stats_enabled INTEGER DEFAULT 0,
    added_at INTEGER
);

CREATE TABLE IF NOT EXISTS channel_members (
    channel_id INTEGER,
    user_id INTEGER,
    joined_at INTEGER,
    PRIMARY KEY (channel_id, user_id)
);

CREATE TABLE IF NOT EXISTS channel_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    channel_id INTEGER,
    event_type TEXT,   -- 'joined' | 'left'
    ts INTEGER
);

CREATE TABLE IF NOT EXISTS groups (
    group_id INTEGER PRIMARY KEY,
    title TEXT,
    added_at INTEGER,
    forward_locked INTEGER DEFAULT 0,
    link_lock_enabled INTEGER DEFAULT 0,
    salom_enabled INTEGER DEFAULT 0,
    tozala_enabled INTEGER DEFAULT 0,
    odam_required INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS warnings (
    group_id INTEGER,
    user_id INTEGER,
    count INTEGER DEFAULT 0,
    updated_at INTEGER,
    PRIMARY KEY (group_id, user_id)
);

CREATE TABLE IF NOT EXISTS mutes (
    group_id INTEGER,
    user_id INTEGER,
    until_ts INTEGER,
    reason TEXT,
    PRIMARY KEY (group_id, user_id)
);

CREATE TABLE IF NOT EXISTS link_violations (
    group_id INTEGER,
    user_id INTEGER,
    day TEXT,
    count INTEGER DEFAULT 0,
    PRIMARY KEY (group_id, user_id, day)
);

CREATE TABLE IF NOT EXISTS odam_progress (
    group_id INTEGER,
    user_id INTEGER,
    invited_count INTEGER DEFAULT 0,
    required_count INTEGER DEFAULT 0,
    restricted INTEGER DEFAULT 0,
    PRIMARY KEY (group_id, user_id)
);

CREATE TABLE IF NOT EXISTS broadcast_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    admin_id INTEGER,
    target_type TEXT,
    sent_count INTEGER,
    failed_count INTEGER,
    ts INTEGER
);
"""


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(_SCHEMA)
        await db.execute(
            "INSERT OR IGNORE INTO bot_admins (user_id, added_by, added_at) VALUES (?, ?, ?)",
            (SUPER_ADMIN_ID, SUPER_ADMIN_ID, int(time.time())),
        )
        await db.commit()


def get_db():
    return aiosqlite.connect(DB_PATH)


# ---------- users ----------
async def upsert_user(user_id: int, username: str | None, full_name: str):
    async with get_db() as db:
        await db.execute(
            """INSERT INTO users (user_id, username, full_name, first_seen)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(user_id) DO UPDATE SET username=excluded.username, full_name=excluded.full_name""",
            (user_id, username, full_name, int(time.time())),
        )
        await db.commit()


async def count_users() -> int:
    async with get_db() as db:
        cur = await db.execute("SELECT COUNT(*) FROM users")
        row = await cur.fetchone()
        return row[0]


async def all_user_ids() -> list[int]:
    async with get_db() as db:
        cur = await db.execute("SELECT user_id FROM users WHERE is_banned_from_bot=0")
        rows = await cur.fetchall()
        return [r[0] for r in rows]


# ---------- bot admins ----------
async def is_bot_admin(user_id: int) -> bool:
    async with get_db() as db:
        cur = await db.execute("SELECT 1 FROM bot_admins WHERE user_id=?", (user_id,))
        return (await cur.fetchone()) is not None


async def add_bot_admin(user_id: int, added_by: int):
    async with get_db() as db:
        await db.execute(
            "INSERT OR IGNORE INTO bot_admins (user_id, added_by, added_at) VALUES (?, ?, ?)",
            (user_id, added_by, int(time.time())),
        )
        await db.commit()


async def remove_bot_admin(user_id: int):
    async with get_db() as db:
        await db.execute("DELETE FROM bot_admins WHERE user_id=?", (user_id,))
        await db.commit()


async def list_bot_admins() -> list[int]:
    async with get_db() as db:
        cur = await db.execute("SELECT user_id FROM bot_admins")
        rows = await cur.fetchall()
        return [r[0] for r in rows]


# ---------- channels ----------
async def add_channel(channel_id: int, owner_id: int, title: str, username: str | None):
    async with get_db() as db:
        await db.execute(
            """INSERT INTO channels (channel_id, owner_id, title, username, added_at)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(channel_id) DO UPDATE SET title=excluded.title, username=excluded.username""",
            (channel_id, owner_id, title, username, int(time.time())),
        )
        await db.commit()


async def remove_channel(channel_id: int, owner_id: int):
    async with get_db() as db:
        await db.execute("DELETE FROM channels WHERE channel_id=? AND owner_id=?", (channel_id, owner_id))
        await db.execute("DELETE FROM channel_members WHERE channel_id=?", (channel_id,))
        await db.commit()


async def get_user_channels(owner_id: int) -> list[dict]:
    async with get_db() as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM channels WHERE owner_id=?", (owner_id,))
        rows = await cur.fetchall()
        return [dict(r) for r in rows]


async def get_channel(channel_id: int) -> dict | None:
    async with get_db() as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM channels WHERE channel_id=?", (channel_id,))
        row = await cur.fetchone()
        return dict(row) if row else None


async def toggle_channel_feature(channel_id: int, feature: str) -> int:
    """feature: 'clean_deleted_enabled' yoki 'stats_enabled'. Yangi holatni qaytaradi."""
    assert feature in ("clean_deleted_enabled", "stats_enabled")
    async with get_db() as db:
        cur = await db.execute(f"SELECT {feature} FROM channels WHERE channel_id=?", (channel_id,))
        row = await cur.fetchone()
        new_val = 0 if row and row[0] else 1
        await db.execute(f"UPDATE channels SET {feature}=? WHERE channel_id=?", (new_val, channel_id))
        await db.commit()
        return new_val


async def all_channels_with_feature(feature: str) -> list[dict]:
    async with get_db() as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(f"SELECT * FROM channels WHERE {feature}=1")
        rows = await cur.fetchall()
        return [dict(r) for r in rows]


async def all_channels() -> list[dict]:
    async with get_db() as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM channels")
        rows = await cur.fetchall()
        return [dict(r) for r in rows]


# ---------- channel members (obunachilarni kuzatish) ----------
async def track_channel_member_joined(channel_id: int, user_id: int):
    async with get_db() as db:
        await db.execute(
            "INSERT OR IGNORE INTO channel_members (channel_id, user_id, joined_at) VALUES (?, ?, ?)",
            (channel_id, user_id, int(time.time())),
        )
        await db.execute(
            "INSERT INTO channel_events (channel_id, event_type, ts) VALUES (?, 'joined', ?)",
            (channel_id, int(time.time())),
        )
        await db.commit()


async def track_channel_member_left(channel_id: int, user_id: int):
    async with get_db() as db:
        await db.execute(
            "DELETE FROM channel_members WHERE channel_id=? AND user_id=?", (channel_id, user_id)
        )
        await db.execute(
            "INSERT INTO channel_events (channel_id, event_type, ts) VALUES (?, 'left', ?)",
            (channel_id, int(time.time())),
        )
        await db.commit()


async def get_tracked_members(channel_id: int) -> list[int]:
    async with get_db() as db:
        cur = await db.execute("SELECT user_id FROM channel_members WHERE channel_id=?", (channel_id,))
        rows = await cur.fetchall()
        return [r[0] for r in rows]


async def get_channel_events_since(channel_id: int, since_ts: int) -> dict:
    async with get_db() as db:
        cur = await db.execute(
            "SELECT event_type, COUNT(*) FROM channel_events WHERE channel_id=? AND ts>=? GROUP BY event_type",
            (channel_id, since_ts),
        )
        rows = await cur.fetchall()
        result = {"joined": 0, "left": 0}
        for event_type, cnt in rows:
            result[event_type] = cnt
        return result


# ---------- groups ----------
async def upsert_group(group_id: int, title: str):
    async with get_db() as db:
        await db.execute(
            """INSERT INTO groups (group_id, title, added_at) VALUES (?, ?, ?)
               ON CONFLICT(group_id) DO UPDATE SET title=excluded.title""",
            (group_id, title, int(time.time())),
        )
        await db.commit()


async def get_group(group_id: int) -> dict | None:
    async with get_db() as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM groups WHERE group_id=?", (group_id,))
        row = await cur.fetchone()
        return dict(row) if row else None


async def set_group_field(group_id: int, field: str, value):
    async with get_db() as db:
        await db.execute(f"UPDATE groups SET {field}=? WHERE group_id=?", (value, group_id))
        await db.commit()


async def all_groups() -> list[dict]:
    async with get_db() as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM groups")
        rows = await cur.fetchall()
        return [dict(r) for r in rows]


# ---------- warnings ----------
async def add_warning(group_id: int, user_id: int) -> int:
    async with get_db() as db:
        cur = await db.execute(
            "SELECT count FROM warnings WHERE group_id=? AND user_id=?", (group_id, user_id)
        )
        row = await cur.fetchone()
        new_count = (row[0] if row else 0) + 1
        await db.execute(
            """INSERT INTO warnings (group_id, user_id, count, updated_at) VALUES (?, ?, ?, ?)
               ON CONFLICT(group_id, user_id) DO UPDATE SET count=?, updated_at=?""",
            (group_id, user_id, new_count, int(time.time()), new_count, int(time.time())),
        )
        await db.commit()
        return new_count


async def reset_warnings(group_id: int, user_id: int):
    async with get_db() as db:
        await db.execute("DELETE FROM warnings WHERE group_id=? AND user_id=?", (group_id, user_id))
        await db.commit()


# ---------- mutes ----------
async def set_mute(group_id: int, user_id: int, until_ts: int, reason: str):
    async with get_db() as db:
        await db.execute(
            """INSERT INTO mutes (group_id, user_id, until_ts, reason) VALUES (?, ?, ?, ?)
               ON CONFLICT(group_id, user_id) DO UPDATE SET until_ts=?, reason=?""",
            (group_id, user_id, until_ts, reason, until_ts, reason),
        )
        await db.commit()


async def clear_mute(group_id: int, user_id: int):
    async with get_db() as db:
        await db.execute("DELETE FROM mutes WHERE group_id=? AND user_id=?", (group_id, user_id))
        await db.commit()


# ---------- link violations ----------
async def add_link_violation(group_id: int, user_id: int, day: str) -> int:
    async with get_db() as db:
        cur = await db.execute(
            "SELECT count FROM link_violations WHERE group_id=? AND user_id=? AND day=?",
            (group_id, user_id, day),
        )
        row = await cur.fetchone()
        new_count = (row[0] if row else 0) + 1
        await db.execute(
            """INSERT INTO link_violations (group_id, user_id, day, count) VALUES (?, ?, ?, ?)
               ON CONFLICT(group_id, user_id, day) DO UPDATE SET count=?""",
            (group_id, user_id, day, new_count, new_count),
        )
        await db.commit()
        return new_count


# ---------- odam (taklif qilish) ----------
async def set_odam_requirement(group_id: int, user_id: int, required: int):
    async with get_db() as db:
        await db.execute(
            """INSERT INTO odam_progress (group_id, user_id, invited_count, required_count, restricted)
               VALUES (?, ?, 0, ?, 1)
               ON CONFLICT(group_id, user_id) DO UPDATE SET required_count=?, restricted=1""",
            (group_id, user_id, required, required),
        )
        await db.commit()


async def increment_odam_invited(group_id: int, inviter_id: int) -> tuple[int, int] | None:
    async with get_db() as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT invited_count, required_count, restricted FROM odam_progress WHERE group_id=? AND user_id=?",
            (group_id, inviter_id),
        )
        row = await cur.fetchone()
        if not row or not row["restricted"]:
            return None
        new_invited = row["invited_count"] + 1
        still_restricted = 1 if new_invited < row["required_count"] else 0
        await db.execute(
            "UPDATE odam_progress SET invited_count=?, restricted=? WHERE group_id=? AND user_id=?",
            (new_invited, still_restricted, group_id, inviter_id),
        )
        await db.commit()
        return new_invited, row["required_count"]


async def get_odam_status(group_id: int, user_id: int) -> dict | None:
    async with get_db() as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM odam_progress WHERE group_id=? AND user_id=?", (group_id, user_id)
        )
        row = await cur.fetchone()
        return dict(row) if row else None


async def clear_odam(group_id: int, user_id: int):
    async with get_db() as db:
        await db.execute("DELETE FROM odam_progress WHERE group_id=? AND user_id=?", (group_id, user_id))
        await db.commit()
