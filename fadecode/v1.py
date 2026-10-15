"""JSON API v1 для SPA (Vue): токен в заголовке Authorization, ответы без HTML и без cookie-сессии.

Сервер ничего не помнит между запросами, кроме БД: порядок пропадающих методов, оценки за урок и очередь
повторения клиент держит у себя. Тексты сообщений интерфейса тоже на стороне клиента, API отдаёт только
коды и данные (status, how, grade, индексы токенов для подсветки).
"""
import random
import secrets
import time

from flask import Blueprint, g, jsonify, request
from werkzeug.security import check_password_hash, generate_password_hash

from . import api, auth, content, core, db
from .api import ApiError

bp = Blueprint("v1", __name__)

BOXES = 5
PUBLIC = {"v1.register", "v1.login"}

_body, _int, _answer, _telemetry = api._body, api._int, api._answer, api._telemetry
_lesson, _lesson_block = api._lesson, api._lesson_block


@bp.errorhandler(ApiError)
def _api_error(e):
    return jsonify(error=e.message), e.status


@bp.before_request
def _guard():
    if request.method == "OPTIONS" or request.endpoint in PUBLIC:
        return None
    if g.user is None:
        return jsonify(error="Нужно войти."), 401
    return None


def _user(u):
    return {"id": u["id"], "username": u["username"]}


def _due(uid):
    return [k for k in db.due_keys(uid) if content.valid_key(k)]


# ---------- вход ----------

@bp.post("/auth/register")
def register():
    d = _body()
    username = str(d.get("username", "")).strip()
    password = str(d.get("password", ""))
    if not auth.USERNAME_RE.match(username):
        raise ApiError("Логин: 3-32 символа, только латиница, цифры и _ . -")
    if len(password) < 6:
        raise ApiError("Пароль должен быть не короче 6 символов.")
    if len(password) > 200:
        raise ApiError("Пароль слишком длинный.")
    uid = db.create_user(username, generate_password_hash(password, method=auth.HASH_METHOD))
    if uid is None:
        raise ApiError("Такой логин уже занят.", 409)
    user = db.get_user(uid)
    return jsonify(token=auth.make_token(user), user=_user(user)), 201


@bp.post("/auth/login")
def login():
    d = _body()
    ip = request.remote_addr or "?"
    if auth._blocked(ip):
        raise ApiError("Слишком много неудачных попыток. Попробуйте через несколько минут.", 429)
    user = db.get_user_by_name(str(d.get("username", "")).strip())
    if user and check_password_hash(user["pw_hash"], str(d.get("password", ""))):
        auth._fails.pop(ip, None)
        return jsonify(token=auth.make_token(user), user=_user(user))
    auth._fails.setdefault(ip, []).append(time.time())
    raise ApiError("Неверный логин или пароль.", 401)


@bp.get("/me")
def me():
    return jsonify(user=_user(g.user), due=len(_due(g.user["id"])))


# ---------- каталог ----------

@bp.get("/packs")
def packs():
    uid = g.user["id"]
    done = db.done_map(uid)
    out = [
        {"id": p["id"], "title": p["title"], "desc": p["desc"], "total": len(p["items"]),
         "ready": content.ready_count(p),
         "finished": sum(1 for it in p["items"] if it["lesson"] and it["lesson"] in done)}
        for p in content.PACKS
    ]
    return jsonify(packs=out, due=len(_due(uid)))


@bp.get("/packs/<pid>")
def pack(pid):
    p = content.get_pack(pid)
    if p is None:
        raise ApiError("Неизвестный пакет.", 404)
    done = db.done_map(g.user["id"])
    items = []
    for i, it in enumerate(p["items"]):
        L = content.BY_ID.get(it["lesson"]) if it["lesson"] else None
        items.append({"n": i + 1, "name": it["name"], "category": it["category"], "desc": it["desc"],
                      "lesson": L["id"] if L else None, "title": L["title"] if L else None,
                      "finished": bool(L and L["id"] in done),
                      "lines": content.nlines(content.full_code(L)) if L else 0})
    return jsonify(id=p["id"], title=p["title"], desc=p["desc"], ready=content.ready_count(p), items=items)


# ---------- урок ----------

def _next_lesson(lid):
    p = content.pack_for_lesson(lid)
    if not p:
        return None, None
    ids = [it["lesson"] for it in p["items"] if it["lesson"]]
    nxt = None
    if lid in ids and ids.index(lid) + 1 < len(ids):
        nl = content.BY_ID[ids[ids.index(lid) + 1]]
        nxt = {"id": nl["id"], "title": nl["title"]}
    return {"id": p["id"], "title": p["title"]}, nxt


def _lesson_json(L):
    pack, nxt = _next_lesson(L["id"])
    blocks = []
    for b in L["blocks"]:
        why = b.get("why")
        blocks.append({
            "id": b["id"], "name": b["name"], "note": b["note"], "code": b["code"],
            "rows": content.nlines(b["code"]),
            # правильный ответ и пояснение отдаёт только POST /why
            "why": {"q": why["q"], "opts": list(why["opts"])} if why else None,
        })
    out = {k: L[k] for k in ("id", "title", "tag", "desc", "task", "imports", "cls")}
    if "change" in L:
        out["change"] = L["change"]
    out.update(code=content.full_code(L), body=content.class_body(L),
               rows_whole=content.nlines(content.class_body(L)), blocks=blocks, pack=pack, next=nxt)
    return out


@bp.get("/lessons/<lid>")
def lesson(lid):
    L = content.BY_ID.get(lid)
    if L is None:
        raise ApiError("Неизвестный урок.", 404)
    return jsonify(_lesson_json(L))


@bp.post("/lessons/<lid>/open")
def lesson_open(lid):
    """Начало прохождения: пишет событие и отдаёт порядок пропадающих методов по настройкам."""
    L = content.BY_ID.get(lid)
    if L is None:
        raise ApiError("Неизвестный урок.", 404)
    uid = g.user["id"]
    s = db.get_settings(uid)
    db.log_event(uid, "open", {"lesson": lid})
    return jsonify(order=content.order_ids(L, s["order"], seed=secrets.randbits(32)), settings=s)


# ---------- проверка ответов ----------

def _resolve(L, bid, how, status, d, **extra):
    """Закрывает слот: оценка -> SRS -> журнал. Текст сообщения выбирает клиент по how/status/grade."""
    uid = g.user["id"]
    attempts, hints, ms = _telemetry(d)
    if how == "revealed":
        grade = "again"
    elif how == "ok" and attempts == 1 and hints == 0:
        grade = "good"
    else:
        grade = "hard"
    if bid != "whole":
        db.srs_update(uid, "%s::%s" % (L["id"], bid), grade)
    db.log_event(uid, "resolve", {"lesson": L["id"], "block": bid, "how": how, "status": status,
                                  "grade": grade, "attempts": attempts, "hints": hints, "ms": ms})
    return dict({"resolved": True, "how": how, "status": status, "grade": grade, "failed": how == "revealed"},
                **extra)


@bp.post("/check")
def check():
    d = _body()
    L, bid = _lesson_block(d)
    value = _answer(d)
    if not value.strip():
        return jsonify(resolved=False, status="empty")
    attempts, hints, ms = _telemetry(d)
    r = core.compare_code(content.slot_target(L, bid), value)
    db.log_event(g.user["id"], "check", {"lesson": L["id"], "block": bid, "status": r["status"],
                                         "score": round(r["score"], 3), "attempt": attempts, "hints": hints})
    if r["status"] in ("perfect", "renamed"):
        return jsonify(_resolve(L, bid, "ok", r["status"], d))
    # extra: индексы лишних токенов ответа; ins: [[позиция, подсказка]] о пропущенном. Подсвечивает клиент (core.js).
    return jsonify(resolved=False, status=r["status"], score=round(r["score"] * 100), extra=sorted(r["extra"]),
                   missed_count=len(r["missed"]), ins=sorted([k, v] for k, v in r["ins"].items()))


@bp.post("/accept")
def accept():
    d = _body()
    L, bid = _lesson_block(d)
    r = core.compare_code(content.slot_target(L, bid), _answer(d))
    if r["status"] != "close":
        raise ApiError("Засчитать можно только ответ со статусом «почти».")
    return jsonify(_resolve(L, bid, "accepted", "close", d))


@bp.post("/reveal")
def reveal():
    d = _body()
    L, bid = _lesson_block(d)
    value = _answer(d)
    target = content.slot_target(L, bid)
    r = core.compare_code(target, value) if value.strip() else None
    return jsonify(_resolve(L, bid, "revealed", r["status"] if r else "empty", d, target=target,
                            missed=sorted(r["missed"]) if r else []))


@bp.post("/hint")
def hint():
    d = _body()
    L, bid = _lesson_block(d)
    lines = content.slot_target(L, bid).split("\n")
    n = min(_int(d, "n", 1, 10000, 1), len(lines))
    db.log_event(g.user["id"], "hint", {"lesson": L["id"], "block": bid, "n": n})
    return jsonify(lines=lines[:n], n=n, total=len(lines))


@bp.post("/why")
def why():
    d = _body()
    L, bid = _lesson_block(d)
    b = content.find_block(L, bid)
    if not b or not b.get("why"):
        raise ApiError("У этого метода нет вопроса.", 404)
    i = _int(d, "i", 0, len(b["why"]["opts"]) - 1, 0)
    right = i == b["why"]["ok"]
    db.log_event(g.user["id"], "why", {"lesson": L["id"], "block": bid, "right": right})
    return jsonify(right=right, ok=b["why"]["ok"], exp=b["why"]["exp"])


@bp.post("/copy_done")
def copy_done():
    d = _body()
    L = _lesson(d)
    db.log_event(g.user["id"], "copy", {"lesson": L["id"], "errors": _int(d, "errors", 0, 100000, 0)})
    return jsonify(ok=True)


@bp.post("/lesson_done")
def lesson_done():
    d = _body()
    L = _lesson(d)
    db.mark_done(g.user["id"], L["id"])
    db.log_event(g.user["id"], "lesson_done", {"lesson": L["id"]})
    pack, nxt = _next_lesson(L["id"])
    return jsonify(ok=True, pack=pack, next=nxt)


# ---------- повторение ----------

@bp.get("/review")
def review():
    """Очередь повторения: что пора (или все карточки вперемешку при ?all=1). Очередь дальше ведёт клиент."""
    uid = g.user["id"]
    srs = {k: v for k, v in db.srs_all(uid).items() if content.valid_key(k)}
    if request.args.get("all") == "1":
        keys = list(srs)
        random.shuffle(keys)
    else:
        keys = _due(uid)
    items = []
    for key in keys:
        lid, _, bid = key.partition("::")
        L = content.BY_ID[lid]
        items.append({"lesson": lid, "block": bid, "title": L["title"],
                      "name": content.find_block(L, bid)["name"]})
    return jsonify(items=items, due=len(_due(uid)), has_cards=bool(srs),
                   next_due=min((v["due"] for v in srs.values()), default=None))


# ---------- прогресс и настройки ----------

@bp.get("/stats")
def stats():
    uid = g.user["id"]
    srs = db.srs_all(uid)
    done = db.done_map(uid)
    resolved = [e for e in db.events_last(uid) if e["type"] == "resolve"]
    good = sum(1 for e in resolved if e.get("grade") == "good")
    rows = []
    for L in content.LESSONS:
        items = [srs[k] for k in ("%s::%s" % (L["id"], b["id"]) for b in L["blocks"]) if k in srs]
        boxes = [0] * BOXES
        for it in items:
            boxes[it["box"]] += 1
        rows.append({"id": L["id"], "title": L["title"], "total": len(L["blocks"]), "learned": len(items),
                     "boxes": boxes, "finished": L["id"] in done})
    cards = {
        "done": len(done),
        "fixed": sum(1 for v in srs.values() if v["box"] >= 2),
        "accuracy": round(good / len(resolved) * 100) if resolved else None,
        "due": len(_due(uid)),
    }
    return jsonify(rows=rows, cards=cards, settings=db.get_settings(uid), has_progress=bool(srs))


@bp.get("/settings")
def get_settings():
    return jsonify(settings=db.get_settings(g.user["id"]))


@bp.put("/settings")
def put_settings():
    d = _body()
    order, rounds = d.get("order"), d.get("rounds")
    uid = g.user["id"]
    db.save_settings(uid, {
        "order": order if order in ("small", "random") else "small",
        "rounds": rounds if rounds in ("all", "one") else "all",
        "research": bool(d.get("research", True)),
    })
    return jsonify(settings=db.get_settings(uid))


@bp.post("/reset")
def reset():
    db.reset_progress(g.user["id"])
    return jsonify(ok=True)


@bp.get("/export")
def export():
    uid = g.user["id"]
    return jsonify(srs=db.srs_all(uid), done=db.done_map(uid), log=db.events_last(uid))


# ---------- ИИ-наставник (та же логика, что в старом API) ----------

@bp.post("/ai/chat")
def ai_chat():
    return api.ai_chat()


@bp.post("/ai/advice")
def ai_advice():
    return api.ai_advice()
