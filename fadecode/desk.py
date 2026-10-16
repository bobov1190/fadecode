import secrets

from . import db

MAX_TITLE = 120
MAX_NOTE = 2000
STATUSES = ("idea", "doing", "done")
COLS = "id, title, note, status, est_min, spent_sec, timer_at, created, done_at"


def tasks(uid):
    rows = db.get_db().execute(
        "SELECT " + COLS + " FROM desk_tasks WHERE user_id=? ORDER BY created, id", (uid,)
    ).fetchall()
    return [dict(r) for r in rows]


def _find(uid, tid):
    r = db.get_db().execute("SELECT " + COLS + " FROM desk_tasks WHERE user_id=? AND id=?", (uid, tid)).fetchone()
    return dict(r) if r else None


def _elapsed(row, now):
    return max(0, (now - row["timer_at"]) // 1000) if row["timer_at"] else 0


def _stop_all(uid, keep=None):
    con = db.get_db()
    now = db.now_ms()
    rows = con.execute(
        "SELECT id, spent_sec, timer_at FROM desk_tasks WHERE user_id=? AND timer_at IS NOT NULL", (uid,)
    ).fetchall()
    for r in rows:
        if r["id"] != keep:
            con.execute("UPDATE desk_tasks SET spent_sec=?, timer_at=NULL WHERE id=?",
                        (r["spent_sec"] + _elapsed(r, now), r["id"]))


def _est(value):
    try:
        n = int(value)
    except (TypeError, ValueError):
        return None
    return n if 1 <= n <= 1440 else None


def register(bp):
    from flask import g, jsonify

    from .api import ApiError, _body

    def guard():
        if not db.is_admin(g.user["id"]):
            raise ApiError("Только для админа.", 403)
        return g.user["id"]

    def out(status=200):
        return jsonify(tasks=tasks(g.user["id"]), now=db.now_ms()), status

    def get(uid, tid):
        row = _find(uid, tid)
        if row is None:
            raise ApiError("Задание не найдено.", 404)
        return row

    @bp.get("/desk")
    def desk_list():
        guard()
        return out()

    @bp.post("/desk")
    def desk_add():
        uid = guard()
        d = _body()
        title = str(d.get("title", "")).strip()[:MAX_TITLE]
        if not title:
            raise ApiError("Название не может быть пустым.")
        est = _est(d.get("est_min", 30))
        if est is None:
            raise ApiError("Цена в минутах: от 1 до 1440.")
        status = d.get("status") if d.get("status") in ("idea", "doing") else "idea"
        con = db.get_db()
        con.execute(
            "INSERT INTO desk_tasks(id, user_id, title, note, status, est_min, spent_sec, created) VALUES (?,?,?,?,?,?,0,?)",
            (secrets.token_hex(6), uid, title, str(d.get("note") or "")[:MAX_NOTE], status, est, db.now_ms()),
        )
        con.commit()
        return out(201)

    @bp.put("/desk/<tid>")
    def desk_update(tid):
        uid = guard()
        d = _body()
        row = get(uid, tid)
        now = db.now_ms()
        title, note, est = row["title"], row["note"], row["est_min"]
        status, spent, timer, done_at = row["status"], row["spent_sec"], row["timer_at"], row["done_at"]
        if "title" in d:
            title = str(d["title"]).strip()[:MAX_TITLE]
            if not title:
                raise ApiError("Название не может быть пустым.")
        if "note" in d:
            note = str(d["note"] or "")[:MAX_NOTE]
        if "est_min" in d:
            est = _est(d["est_min"])
            if est is None:
                raise ApiError("Цена в минутах: от 1 до 1440.")
        if "status" in d:
            if d["status"] not in STATUSES:
                raise ApiError("Неизвестный статус.")
            if d["status"] != status:
                spent += _elapsed(row, now)
                timer = None
                status = d["status"]
                done_at = now if status == "done" else None
        con = db.get_db()
        con.execute(
            "UPDATE desk_tasks SET title=?, note=?, est_min=?, status=?, spent_sec=?, timer_at=?, done_at=? "
            "WHERE user_id=? AND id=?",
            (title, note, est, status, spent, timer, done_at, uid, tid),
        )
        con.commit()
        return out()

    @bp.post("/desk/<tid>/start")
    def desk_start(tid):
        uid = guard()
        row = get(uid, tid)
        if row["status"] == "done":
            raise ApiError("Задание уже выполнено.")
        _stop_all(uid, keep=tid)
        con = db.get_db()
        if not row["timer_at"]:
            con.execute("UPDATE desk_tasks SET timer_at=?, status='doing' WHERE user_id=? AND id=?",
                        (db.now_ms(), uid, tid))
        else:
            con.execute("UPDATE desk_tasks SET status='doing' WHERE user_id=? AND id=?", (uid, tid))
        con.commit()
        return out()

    @bp.post("/desk/<tid>/stop")
    def desk_stop(tid):
        uid = guard()
        row = get(uid, tid)
        con = db.get_db()
        con.execute("UPDATE desk_tasks SET spent_sec=?, timer_at=NULL WHERE user_id=? AND id=?",
                    (row["spent_sec"] + _elapsed(row, db.now_ms()), uid, tid))
        con.commit()
        return out()

    @bp.delete("/desk/<tid>")
    def desk_delete(tid):
        uid = guard()
        get(uid, tid)
        con = db.get_db()
        con.execute("DELETE FROM desk_tasks WHERE user_id=? AND id=?", (uid, tid))
        con.commit()
        return out()
