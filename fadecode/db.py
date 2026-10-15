"""SQLite: пользователи, настройки, повторения (SRS), пройденные уроки, журнал, квоты ИИ и кэш ответов."""
import json
import random
import sqlite3
import time

from flask import current_app, g

DAYS = [0.007, 1, 3, 7, 21]  # интервалы по коробкам, в днях (первая — ~10 минут)
DAY_MS = 86400000
EVENT_CAP = 3000
DEFAULT_SETTINGS = {"order": "small", "rounds": "all", "research": True}

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE COLLATE NOCASE,
    pw_hash TEXT NOT NULL,
    created INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS settings (
    user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    data TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS srs (
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    key TEXT NOT NULL,
    box INTEGER NOT NULL DEFAULT 0,
    seen INTEGER NOT NULL DEFAULT 0,
    lapses INTEGER NOT NULL DEFAULT 0,
    due INTEGER NOT NULL,
    last INTEGER NOT NULL,
    PRIMARY KEY (user_id, key)
);
CREATE TABLE IF NOT EXISTS done (
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    lesson_id TEXT NOT NULL,
    at INTEGER NOT NULL,
    PRIMARY KEY (user_id, lesson_id)
);
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    t INTEGER NOT NULL,
    type TEXT NOT NULL,
    data TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS events_user ON events(user_id, id);
CREATE TABLE IF NOT EXISTS ai_usage (
    day TEXT NOT NULL,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    n INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (day, user_id)
);
CREATE TABLE IF NOT EXISTS ai_cache (
    h TEXT PRIMARY KEY,
    answer TEXT NOT NULL,
    created INTEGER NOT NULL
);
"""


def now_ms():
    return int(time.time() * 1000)


def get_db():
    if "db" not in g:
        con = sqlite3.connect(current_app.config["DATABASE"])
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA foreign_keys = ON")
        con.execute("PRAGMA journal_mode = WAL")
        g.db = con
    return g.db


def close_db(exc=None):
    con = g.pop("db", None)
    if con is not None:
        con.close()


def init_app(app):
    app.teardown_appcontext(close_db)
    with app.app_context():
        get_db().executescript(SCHEMA)


# ---------- пользователи ----------

def create_user(username, pw_hash):
    con = get_db()
    try:
        cur = con.execute(
            "INSERT INTO users(username, pw_hash, created) VALUES (?,?,?)", (username, pw_hash, now_ms())
        )
        con.commit()
        return cur.lastrowid
    except sqlite3.IntegrityError:
        con.rollback()
        return None


def get_user(uid):
    return get_db().execute("SELECT id, username, pw_hash, created FROM users WHERE id=?", (uid,)).fetchone()


def get_user_by_name(username):
    return get_db().execute(
        "SELECT id, username, pw_hash, created FROM users WHERE username=?", (username,)
    ).fetchone()


# ---------- настройки ----------

def get_settings(uid):
    cache = g.setdefault("_settings", {})
    if uid not in cache:
        row = get_db().execute("SELECT data FROM settings WHERE user_id=?", (uid,)).fetchone()
        s = dict(DEFAULT_SETTINGS)
        if row:
            try:
                s.update(json.loads(row["data"]))
            except ValueError:
                pass
        cache[uid] = s
    return cache[uid]


def save_settings(uid, new):
    s = dict(get_settings(uid))
    s.update(new)
    con = get_db()
    con.execute("INSERT OR REPLACE INTO settings(user_id, data) VALUES (?,?)", (uid, json.dumps(s)))
    con.commit()
    g.setdefault("_settings", {})[uid] = s


# ---------- повторения ----------

def srs_all(uid):
    rows = get_db().execute(
        "SELECT key, box, seen, lapses, due, last FROM srs WHERE user_id=?", (uid,)
    ).fetchall()
    return {r["key"]: dict(r) for r in rows}


def srs_update(uid, key, grade):
    con = get_db()
    row = con.execute("SELECT box, seen, lapses FROM srs WHERE user_id=? AND key=?", (uid, key)).fetchone()
    box, seen, lapses = (row["box"], row["seen"], row["lapses"]) if row else (0, 0, 0)
    seen += 1
    if grade == "good":
        box = min(box + 1, 4)
    elif grade == "again":
        box = 0
        lapses += 1
    now = now_ms()
    due = now + int(DAYS[box] * DAY_MS)
    con.execute(
        "INSERT OR REPLACE INTO srs(user_id, key, box, seen, lapses, due, last) VALUES (?,?,?,?,?,?,?)",
        (uid, key, box, seen, lapses, due, now),
    )
    con.commit()


def due_keys(uid):
    rows = get_db().execute(
        "SELECT key FROM srs WHERE user_id=? AND due<=? ORDER BY due", (uid, now_ms())
    ).fetchall()
    return [r["key"] for r in rows]


# ---------- пройденные уроки ----------

def done_map(uid):
    rows = get_db().execute("SELECT lesson_id, at FROM done WHERE user_id=?", (uid,)).fetchall()
    return {r["lesson_id"]: r["at"] for r in rows}


def mark_done(uid, lesson_id):
    con = get_db()
    con.execute("INSERT OR REPLACE INTO done(user_id, lesson_id, at) VALUES (?,?,?)", (uid, lesson_id, now_ms()))
    con.commit()


# ---------- журнал ----------

def log_event(uid, etype, data):
    if not get_settings(uid)["research"]:
        return
    con = get_db()
    con.execute(
        "INSERT INTO events(user_id, t, type, data) VALUES (?,?,?,?)",
        (uid, now_ms(), etype, json.dumps(data, ensure_ascii=False)),
    )
    if random.random() < 0.05:
        con.execute(
            "DELETE FROM events WHERE user_id=? AND id NOT IN "
            "(SELECT id FROM events WHERE user_id=? ORDER BY id DESC LIMIT ?)",
            (uid, uid, EVENT_CAP),
        )
    con.commit()


def _event(row):
    try:
        d = json.loads(row["data"])
    except ValueError:
        d = {}
    return dict({"t": row["t"], "type": row["type"]}, **d)


def events_last(uid, limit=EVENT_CAP):
    rows = get_db().execute(
        "SELECT t, type, data FROM events WHERE user_id=? ORDER BY id DESC LIMIT ?", (uid, limit)
    ).fetchall()
    return [_event(r) for r in reversed(rows)]


def reset_progress(uid):
    con = get_db()
    for table in ("srs", "done", "events"):
        con.execute("DELETE FROM %s WHERE user_id=?" % table, (uid,))
    con.commit()


# ---------- ИИ: квоты и кэш ----------

def ai_counts(day, uid):
    con = get_db()
    row = con.execute("SELECT n FROM ai_usage WHERE day=? AND user_id=?", (day, uid)).fetchone()
    total = con.execute("SELECT COALESCE(SUM(n), 0) AS s FROM ai_usage WHERE day=?", (day,)).fetchone()["s"]
    return (row["n"] if row else 0), total


def ai_bump(day, uid):
    con = get_db()
    cur = con.execute("UPDATE ai_usage SET n = n + 1 WHERE day=? AND user_id=?", (day, uid))
    if cur.rowcount == 0:
        con.execute("INSERT INTO ai_usage(day, user_id, n) VALUES (?,?,1)", (day, uid))
    con.commit()


def cache_get(h):
    row = get_db().execute("SELECT answer FROM ai_cache WHERE h=?", (h,)).fetchone()
    return row["answer"] if row else None


def cache_put(h, answer):
    con = get_db()
    con.execute("INSERT OR REPLACE INTO ai_cache(h, answer, created) VALUES (?,?,?)", (h, answer, now_ms()))
    if random.random() < 0.05:
        con.execute("DELETE FROM ai_cache WHERE created < ?", (now_ms() - 14 * DAY_MS,))
    con.commit()
