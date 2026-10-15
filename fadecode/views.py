"""Страницы: главная, пакеты, этапы урока, повторение, прогресс, настройки."""
import json
import random
import secrets

from flask import (Blueprint, Response, abort, flash, g, redirect, render_template, request, session,
                   url_for)

from . import content, db
from .auth import csrf_token, login_required

bp = Blueprint("views", __name__)

BOXES = 5


@bp.app_context_processor
def inject_globals():
    user = getattr(g, "user", None)
    due = len(_due(user["id"])) if user else 0
    return {"csrf_token": csrf_token, "due_count": due}


def _due(uid):
    return [k for k in db.due_keys(uid) if content.valid_key(k)]


def _lesson_or_404(lid):
    L = content.BY_ID.get(lid)
    if L is None:
        abort(404)
    return L


def _remember(name, lid, value, keep=8):
    """Хранит в сессии небольшой словарь по урокам (порядок методов, оценки), не раздувая cookie."""
    data = dict(session.get(name) or {})
    data[lid] = value
    while len(data) > keep:
        data.pop(next(iter(data)))
    session[name] = data


def _order(L):
    ids = (session.get("ord") or {}).get(L["id"])
    if ids and sorted(ids) == sorted(b["id"] for b in L["blocks"]):
        return ids
    mode = db.get_settings(g.user["id"])["order"]
    return content.order_ids(L, mode, seed=secrets.randbits(32))


# ---------- публичная страница ----------

@bp.get("/about")
def about():
    return render_template("landing.html")


# ---------- каталог ----------

@bp.get("/")
@login_required
def home():
    uid = g.user["id"]
    done = db.done_map(uid)
    packs = []
    for p in content.PACKS:
        finished = sum(1 for it in p["items"] if it["lesson"] and it["lesson"] in done)
        packs.append(dict(p, ready=content.ready_count(p), finished=finished))
    return render_template("home.html", packs=packs, due=len(_due(uid)), active="home")


@bp.get("/pack/<pid>")
@login_required
def pack(pid):
    p = content.get_pack(pid)
    if p is None:
        abort(404)
    done = db.done_map(g.user["id"])
    items = []
    for i, it in enumerate(p["items"]):
        L = content.BY_ID.get(it["lesson"]) if it["lesson"] else None
        items.append(dict(it, n=i + 1, L=L, finished=bool(L and L["id"] in done),
                          lines=content.nlines(content.full_code(L)) if L else 0))
    return render_template("pack.html", pack=p, items=items, ready=content.ready_count(p), active="home")


# ---------- этапы урока ----------

@bp.get("/lesson/<lid>")
@login_required
def lesson(lid):
    L = _lesson_or_404(lid)
    uid = g.user["id"]
    mode = db.get_settings(uid)["order"]
    _remember("ord", lid, content.order_ids(L, mode, seed=secrets.randbits(32)))
    _remember("grades", lid, {})
    db.log_event(uid, "open", {"lesson": lid})
    return render_template("lesson_read.html", L=L, code=content.full_code(L), ai_lesson=lid, active="home")


@bp.get("/lesson/<lid>/copy")
@login_required
def copy(lid):
    L = _lesson_or_404(lid)
    return render_template("lesson_copy.html", L=L, target=content.full_code(L), ai_lesson=lid, active="home")


@bp.get("/lesson/<lid>/recall")
@login_required
def recall(lid):
    L = _lesson_or_404(lid)
    N = len(L["blocks"])
    r = max(1, min(request.args.get("round", 1, type=int), N + 1))
    one = db.get_settings(g.user["id"])["rounds"] == "one"
    order = _order(L)
    whole = r > N
    missing = [] if whole else ([order[r - 1]] if one else order[:r])
    if whole:
        next_url, next_label = url_for("views.done", lid=lid), "Завершить урок"
    else:
        next_url = url_for("views.recall", lid=lid, round=r + 1)
        next_label = "Дальше: весь класс →" if r == N else "Дальше: пропадёт ещё метод →"
    return render_template(
        "lesson_recall.html", L=L, N=N, r=r, one=one, whole=whole, missing=missing,
        names={b["id"]: b["name"] for b in L["blocks"]}, next_url=next_url, next_label=next_label,
        ai_lesson=lid, active="home",
    )


@bp.get("/lesson/<lid>/done")
@login_required
def done(lid):
    L = _lesson_or_404(lid)
    grades = (session.get("grades") or {}).get(lid, {})
    pack = content.pack_for_lesson(lid)
    nxt = None
    if pack:
        ids = [it["lesson"] for it in pack["items"] if it["lesson"]]
        if lid in ids and ids.index(lid) + 1 < len(ids):
            nxt = content.BY_ID[ids[ids.index(lid) + 1]]
    rows = [(b["name"], grades[b["id"]]) for b in L["blocks"] if b["id"] in grades]
    return render_template("lesson_done.html", L=L, rows=rows, pack=pack, nxt=nxt, active="home")


# ---------- повторение ----------

def _review_state(uid):
    """Текущая карточка повторения: из очереди «повторить всё» либо из того, что пора повторить."""
    rq = session.get("rq")
    if rq is not None:
        rq = [k for k in rq if content.valid_key(k)]
        if rq:
            total = session.get("rq_total", len(rq))
            return rq[0], "%d из %d" % (max(1, total - len(rq) + 1), total), True
        return None, None, True
    keys = _due(uid)
    if keys:
        return keys[0], "осталось %d" % len(keys), False
    return None, None, False


@bp.get("/review")
@login_required
def review():
    uid = g.user["id"]
    key, progress, queued = _review_state(uid)
    if key is None:
        finished = session.pop("rq_done", None)
        if queued:
            session.pop("rq", None)
            session.pop("rq_total", None)
        srs = {k: v for k, v in db.srs_all(uid).items() if content.valid_key(k)}
        nxt = min((v["due"] for v in srs.values()), default=None)
        return render_template("review_empty.html", finished=finished, next_due=nxt, has_cards=bool(srs),
                               active="review")
    lid, _, bid = key.partition("::")
    L = content.BY_ID[lid]
    return render_template("review.html", L=L, bid=bid, progress=progress, ai_lesson=lid, active="review")


@bp.post("/review/all")
@login_required
def review_all():
    keys = [k for k in db.srs_all(g.user["id"]) if content.valid_key(k)]
    if not keys:
        flash("Пока нечего повторять: пройди хотя бы один урок.", "bad")
        return redirect(url_for("views.review"))
    random.shuffle(keys)
    session["rq"] = keys
    session["rq_total"] = len(keys)
    return redirect(url_for("views.review"))


@bp.post("/review/next")
@login_required
def review_next():
    rq = session.get("rq")
    if rq is not None:
        rq = list(rq[1:])
        if rq:
            session["rq"] = rq
        else:
            session.pop("rq", None)
            session["rq_done"] = session.pop("rq_total", 0)
    return redirect(url_for("views.review"))


# ---------- прогресс и настройки ----------

@bp.get("/stats")
@login_required
def stats():
    uid = g.user["id"]
    srs = db.srs_all(uid)
    done = db.done_map(uid)
    events = db.events_last(uid)
    resolved = [e for e in events if e["type"] == "resolve"]
    good = sum(1 for e in resolved if e.get("grade") == "good")
    rows = []
    for L in content.LESSONS:
        items = [srs[k] for k in ("%s::%s" % (L["id"], b["id"]) for b in L["blocks"]) if k in srs]
        boxes = [0] * BOXES
        for it in items:
            boxes[it["box"]] += 1
        rows.append(dict(L=L, learned=len(items), boxes=boxes, finished=L["id"] in done))
    cards = {
        "done": len(done),
        "fixed": sum(1 for v in srs.values() if v["box"] >= 2),
        "accuracy": ("%d%%" % round(good / len(resolved) * 100)) if resolved else "—",
        "due": len(_due(uid)),
    }
    return render_template("stats.html", rows=rows, cards=cards, settings=db.get_settings(uid),
                           has_progress=bool(srs), active="stats")


@bp.post("/settings")
@login_required
def settings():
    order = request.form.get("order", "small")
    rounds = request.form.get("rounds", "all")
    db.save_settings(g.user["id"], {
        "order": order if order in ("small", "random") else "small",
        "rounds": rounds if rounds in ("all", "one") else "all",
        "research": "research" in request.form,
    })
    flash("Настройки сохранены.", "ok")
    return redirect(url_for("views.stats"))


@bp.get("/export.json")
@login_required
def export():
    uid = g.user["id"]
    payload = {"srs": db.srs_all(uid), "done": db.done_map(uid), "log": db.events_last(uid)}
    return Response(
        json.dumps(payload, ensure_ascii=False, indent=2),
        mimetype="application/json",
        headers={"Content-Disposition": "attachment; filename=fadecode-log.json"},
    )


@bp.post("/reset")
@login_required
def reset():
    db.reset_progress(g.user["id"])
    for name in ("ord", "grades", "rq", "rq_total", "rq_done"):
        session.pop(name, None)
    flash("Прогресс и журнал стёрты.", "ok")
    return redirect(url_for("views.stats"))
