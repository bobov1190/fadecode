"""Задания с лимитом времени: набор карточек-уроков, таймер с нажатия «Начать», автоматический балл.

Балл считает только сервер по журналу assign_log. В журнал попадают события, пока попытка идёт
(таймер не вышел, попытка не завершена) и урок входит в задание. Выход из страницы таймер не останавливает.

Формула на урок (доля от max_score / число карточек):
  20% копирование: 1 - 0.04 * ошибки (лучшая попытка; не копировал = 0)
  80% вспоминание: поровну на каждый метод и на «весь класс»; у слота 1.0 минус
     0.15 за каждую неверную проверку, 0.10 за каждую открытую подсказку, 0.25 если «почти, засчитать»;
     «показать ответ» или не решённый слот = 0.
"""
import json
import secrets

from . import content, db

W_COPY = 0.2
P_WRONG, P_HINT, P_ACCEPT, P_COPY = 0.15, 0.10, 0.25, 0.04
MIN_MS = 60000


# ---------- имя ----------

def get_name(uid):
    row = db.get_db().execute("SELECT full_name FROM profiles WHERE user_id=?", (uid,)).fetchone()
    return row["full_name"] if row else ""


def set_name(uid, name):
    name = " ".join(str(name or "").split())[:80]
    if not name:
        return ""
    con = db.get_db()
    con.execute(
        "INSERT INTO profiles(user_id, full_name) VALUES (?,?) "
        "ON CONFLICT (user_id) DO UPDATE SET full_name = excluded.full_name",
        (uid, name),
    )
    con.commit()
    return name


# ---------- задания и попытки ----------

def _assignment(aid):
    r = db.get_db().execute(
        "SELECT id, title, note, lessons, minutes, max_score, created FROM assignments WHERE id=?", (aid,)
    ).fetchone()
    if r is None:
        return None
    a = dict(r)
    a["lessons"] = [x for x in json.loads(a["lessons"]) if x in content.BY_ID]
    return a


def _attempt(aid, uid):
    r = db.get_db().execute(
        "SELECT assignment_id, user_id, started, finished FROM assign_attempts WHERE assignment_id=? AND user_id=?",
        (aid, uid),
    ).fetchone()
    return dict(r) if r else None


def deadline(a, t):
    return t["started"] + a["minutes"] * MIN_MS


def _settle(a, t, now):
    """Время вышло, а попытка не закрыта: закрываем её моментом дедлайна."""
    if t["finished"] is None and now >= deadline(a, t):
        t["finished"] = deadline(a, t)
        con = db.get_db()
        con.execute("UPDATE assign_attempts SET finished=? WHERE assignment_id=? AND user_id=? AND finished IS NULL",
                    (t["finished"], t["assignment_id"], t["user_id"]))
        con.commit()


def _logs(aid, uid):
    rows = db.get_db().execute(
        "SELECT lesson, block, kind, val FROM assign_log WHERE assignment_id=? AND user_id=? ORDER BY t",
        (aid, uid),
    ).fetchall()
    return [dict(r) for r in rows]


def record(uid, lesson, kind, block="", val=0):
    """Пишет событие во все идущие попытки, где есть этот урок. Вне задания ничего не делает."""
    con = db.get_db()
    now = db.now_ms()
    rows = con.execute(
        "SELECT a.id AS aid, a.lessons AS lessons, a.minutes AS minutes, t.started AS started "
        "FROM assign_attempts t JOIN assignments a ON a.id = t.assignment_id "
        "WHERE t.user_id=? AND t.finished IS NULL", (uid,)
    ).fetchall()
    hit = False
    for r in rows:
        if r["started"] + r["minutes"] * MIN_MS <= now or lesson not in json.loads(r["lessons"]):
            continue
        con.execute(
            "INSERT INTO assign_log(assignment_id, user_id, t, lesson, block, kind, val) VALUES (?,?,?,?,?,?,?)",
            (r["aid"], uid, now, lesson, block, kind, int(val)),
        )
        hit = True
    if hit:
        con.commit()


# ---------- балл ----------

def compute(a, logs):
    """-> (итог, разбор по урокам). Всё считается из журнала, клиенту верить не нужно."""
    ids = a["lessons"]
    if not ids:
        return 0.0, []
    per = a["max_score"] / len(ids)
    total, out = 0.0, []
    for lid in ids:
        L = content.BY_ID[lid]
        mine = [e for e in logs if e["lesson"] == lid]
        copies = [e["val"] for e in mine if e["kind"] == "copy"]
        copy_err = min(copies) if copies else None
        copy_score = 0.0 if copy_err is None else max(0.0, 1 - P_COPY * copy_err)
        names = [(b["id"], b["name"]) for b in L["blocks"]] + [("whole", "весь класс")]
        slots = []
        for sid, name in names:
            ev = [e for e in mine if e["block"] == sid]
            kinds = [e["kind"] for e in ev]
            wrong = kinds.count("wrong")
            hints = max([e["val"] for e in ev if e["kind"] == "hint"] or [0])
            accepted, revealed = "accepted" in kinds, "revealed" in kinds
            solved = "ok" in kinds or accepted
            if revealed or not solved:
                s = 0.0
            else:
                s = max(0.0, 1 - P_WRONG * wrong - P_HINT * hints - (P_ACCEPT if accepted else 0))
            slots.append({"id": sid, "name": name, "wrong": wrong, "hints": hints, "accepted": accepted,
                          "revealed": revealed, "solved": solved and not revealed, "score": round(s, 3)})
        recall = sum(s["score"] for s in slots) / len(slots)
        sc = per * (W_COPY * copy_score + (1 - W_COPY) * recall)
        total += sc
        out.append({"id": lid, "title": L["title"], "max": round(per, 1), "score": round(sc, 1),
                    "copy_errors": copy_err, "copy_score": round(copy_score, 3), "slots": slots})
    return round(total, 1), out


def _state(a, t, now, detail=True):
    """Вид попытки для ученика/админа: статус, время, итог (пока идёт, балл не показываем)."""
    if t is None:
        return {"status": "new"}
    _settle(a, t, now)
    running = t["finished"] is None
    end = now if running else t["finished"]
    st = {"status": "running" if running else "finished", "started": t["started"],
          "deadline": deadline(a, t), "finished": t["finished"],
          "spent_sec": max(0, (end - t["started"]) // 1000)}
    if not running:
        score, br = compute(a, _logs(a["id"], t["user_id"]))
        st["score"] = score
        if detail:
            st["breakdown"] = br
    return st


def _pub(a):
    return {"id": a["id"], "title": a["title"], "note": a["note"], "minutes": a["minutes"],
            "max_score": a["max_score"], "lessons": a["lessons"], "created": a["created"]}


def _cards(a):
    return [{"id": x, "title": content.BY_ID[x]["title"], "tag": content.BY_ID[x]["tag"],
             "methods": len(content.BY_ID[x]["blocks"])} for x in a["lessons"]]


def active_for(uid):
    """Идущая попытка с ближайшим дедлайном (или None)."""
    now = db.now_ms()
    rows = db.get_db().execute(
        "SELECT assignment_id FROM assign_attempts WHERE user_id=? AND finished IS NULL", (uid,)
    ).fetchall()
    best = None
    for r in rows:
        a = _assignment(r["assignment_id"])
        t = _attempt(r["assignment_id"], uid)
        if a is None or t is None:
            continue
        _settle(a, t, now)
        if t["finished"] is None and (best is None or deadline(a, t) < best["deadline"]):
            best = {"id": a["id"], "title": a["title"], "started": t["started"], "deadline": deadline(a, t)}
    return best


# ---------- HTTP ----------

def register(bp):
    from flask import g, jsonify

    from .api import ApiError, _body

    def admin():
        if not db.is_admin(g.user["id"]):
            raise ApiError("Только для админа.", 403)
        return g.user["id"]

    def need(aid):
        a = _assignment(aid)
        if a is None:
            raise ApiError("Задание не найдено.", 404)
        return a

    def num(v, lo, hi, what):
        try:
            n = int(v)
        except (TypeError, ValueError):
            n = None
        if n is None or not lo <= n <= hi:
            raise ApiError("%s: от %d до %d." % (what, lo, hi))
        return n

    def fields(d):
        title = str(d.get("title", "")).strip()[:120]
        if not title:
            raise ApiError("Название не может быть пустым.")
        ids = []
        for x in d.get("lessons") or []:
            if isinstance(x, str) and x in content.BY_ID and x not in ids:
                ids.append(x)
        if not 1 <= len(ids) <= 12:
            raise ApiError("Выбери от 1 до 12 карточек.")
        return (title, str(d.get("note") or "")[:2000], json.dumps(ids),
                num(d.get("minutes"), 1, 600, "Время в минутах"), num(d.get("max_score", 100), 1, 1000, "Максимум баллов"))

    # --- ученик ---

    @bp.get("/assign/active")
    def assign_active():
        return jsonify(active=active_for(g.user["id"]), now=db.now_ms())

    @bp.get("/assign/<aid>")
    def assign_get(aid):
        a = need(aid)
        uid = g.user["id"]
        now = db.now_ms()
        return jsonify(assignment=dict(_pub(a), cards=_cards(a)), attempt=_state(a, _attempt(aid, uid), now),
                       name=get_name(uid), now=now)

    @bp.post("/assign/<aid>/start")
    def assign_start(aid):
        a = need(aid)
        uid = g.user["id"]
        d = _body()
        if d.get("name"):
            set_name(uid, d["name"])
        if not get_name(uid):
            raise ApiError("Укажи имя и фамилию: по ним учитель найдёт твой балл.")
        now = db.now_ms()
        t = _attempt(aid, uid)
        if t is None:
            other = active_for(uid)
            if other and other["id"] != aid:
                raise ApiError("Сначала заверши другое задание: «%s»." % other["title"], 409)
            con = db.get_db()
            con.execute("INSERT INTO assign_attempts(assignment_id, user_id, started) VALUES (?,?,?)", (aid, uid, now))
            con.commit()
            t = _attempt(aid, uid)
        return jsonify(assignment=dict(_pub(a), cards=_cards(a)), attempt=_state(a, t, now), name=get_name(uid), now=now)

    @bp.post("/assign/<aid>/finish")
    def assign_finish(aid):
        a = need(aid)
        uid = g.user["id"]
        t = _attempt(aid, uid)
        if t is None:
            raise ApiError("Ты ещё не начинал это задание.")
        now = db.now_ms()
        if t["finished"] is None:
            con = db.get_db()
            end = min(now, deadline(a, t))
            con.execute("UPDATE assign_attempts SET finished=? WHERE assignment_id=? AND user_id=? AND finished IS NULL",
                        (end, aid, uid))
            con.commit()
            t = _attempt(aid, uid)
        return jsonify(assignment=dict(_pub(a), cards=_cards(a)), attempt=_state(a, t, now), name=get_name(uid), now=now)

    @bp.put("/profile")
    def profile_put():
        name = set_name(g.user["id"], _body().get("name"))
        if not name:
            raise ApiError("Имя не может быть пустым.")
        return jsonify(name=name)

    # --- админ ---

    @bp.get("/admin/assign")
    def admin_list():
        admin()
        con = db.get_db()
        rows = con.execute(
            "SELECT id, title, note, lessons, minutes, max_score, created FROM assignments ORDER BY created DESC"
        ).fetchall()
        cnt = {}
        for r in con.execute("SELECT assignment_id, COUNT(*) AS n, COUNT(finished) AS f FROM assign_attempts "
                             "GROUP BY assignment_id").fetchall():
            cnt[r["assignment_id"]] = (r["n"], r["f"])
        items = []
        for r in rows:
            a = dict(r)
            a["lessons"] = json.loads(a["lessons"])
            n, f = cnt.get(a["id"], (0, 0))
            items.append(dict(_pub(a), started=n, finished=f))
        catalog = [{"id": L["id"], "title": L["title"], "tag": L["tag"]} for L in content.LESSONS]
        return jsonify(items=items, catalog=catalog)

    @bp.post("/admin/assign")
    def admin_create():
        uid = admin()
        title, note, ids, minutes, mx = fields(_body())
        aid = secrets.token_urlsafe(6).replace("-", "x").replace("_", "y")
        con = db.get_db()
        con.execute(
            "INSERT INTO assignments(id, title, note, lessons, minutes, max_score, created, owner) VALUES (?,?,?,?,?,?,?,?)",
            (aid, title, note, ids, minutes, mx, db.now_ms(), uid),
        )
        con.commit()
        return jsonify(id=aid), 201

    @bp.put("/admin/assign/<aid>")
    def admin_update(aid):
        admin()
        need(aid)
        title, note, ids, minutes, mx = fields(_body())
        con = db.get_db()
        con.execute("UPDATE assignments SET title=?, note=?, lessons=?, minutes=?, max_score=? WHERE id=?",
                    (title, note, ids, minutes, mx, aid))
        con.commit()
        return jsonify(ok=True)

    @bp.delete("/admin/assign/<aid>")
    def admin_delete(aid):
        admin()
        need(aid)
        con = db.get_db()
        con.execute("DELETE FROM assign_log WHERE assignment_id=?", (aid,))
        con.execute("DELETE FROM assign_attempts WHERE assignment_id=?", (aid,))
        con.execute("DELETE FROM assignments WHERE id=?", (aid,))
        con.commit()
        return jsonify(ok=True)

    @bp.get("/admin/assign/<aid>")
    def admin_results(aid):
        admin()
        a = need(aid)
        now = db.now_ms()
        rows = db.get_db().execute(
            "SELECT t.user_id AS uid, u.username AS username, p.full_name AS full_name "
            "FROM assign_attempts t JOIN users u ON u.id = t.user_id "
            "LEFT JOIN profiles p ON p.user_id = t.user_id WHERE t.assignment_id=? ORDER BY t.started", (aid,)
        ).fetchall()
        results = []
        for r in rows:
            st = _state(a, _attempt(aid, r["uid"]), now)
            results.append(dict(st, user_id=r["uid"], username=r["username"], name=r["full_name"] or ""))
        return jsonify(assignment=dict(_pub(a), cards=_cards(a)), results=results, now=now)

    @bp.delete("/admin/assign/<aid>/attempt/<int:uid>")
    def admin_reset(aid, uid):
        admin()
        need(aid)
        con = db.get_db()
        con.execute("DELETE FROM assign_log WHERE assignment_id=? AND user_id=?", (aid, uid))
        con.execute("DELETE FROM assign_attempts WHERE assignment_id=? AND user_id=?", (aid, uid))
        con.commit()
        return jsonify(ok=True)
