"""JSON API: проверка ответов, подсказки, оценки, вопросы «зачем?», ИИ-наставник."""
import random

from flask import Blueprint, current_app, g, jsonify, render_template, request, session

from . import ai, content, core, db
from .auth import login_required

bp = Blueprint("api", __name__)


class ApiError(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.message = message
        self.status = status


@bp.errorhandler(ApiError)
def _api_error(e):
    return jsonify(error=e.message), e.status


@bp.before_request
@login_required
def _guard():
    return None


def _body():
    d = request.get_json(silent=True)
    return d if isinstance(d, dict) else {}


def _int(d, name, lo, hi, default):
    try:
        v = int(d.get(name, default))
    except (TypeError, ValueError):
        v = default
    return max(lo, min(hi, v))


def _lesson(d):
    L = content.BY_ID.get(str(d.get("lesson", "")))
    if L is None:
        raise ApiError("Неизвестный урок.", 404)
    return L


def _lesson_block(d):
    L = _lesson(d)
    bid = str(d.get("block", ""))
    if bid != "whole" and content.find_block(L, bid) is None:
        raise ApiError("Неизвестный метод.", 404)
    return L, bid


def _answer(d):
    value = d.get("value", "")
    if not isinstance(value, str):
        value = ""
    if len(value) > current_app.config["MAX_ANSWER_CHARS"]:
        raise ApiError("Ответ слишком длинный.", 413)
    return value


def _telemetry(d):
    return (_int(d, "attempts", 1, 999, 1), _int(d, "hints", 0, 999, 0), _int(d, "ms", 0, 36000000, 0))


# ---------- проверка ----------

def _parts(r):
    bits = []
    if r["extra"]:
        bits.append("красным отмечено лишнее (%d)" % len(r["extra"]))
    if r["missed"]:
        if r["status"] == "close":
            bits.append("оранжевым вставлено то, чего не хватает (токенов: %d)" % len(r["missed"]))
        else:
            bits.append("оранжевое «…» показывает, где что-то пропущено (токенов: %d)" % len(r["missed"]))
    if not bits:
        return ""
    text = "; ".join(bits)
    return text[0].upper() + text[1:] + "."


def _why_html(L, bid):
    b = content.find_block(L, bid) if bid != "whole" else None
    if not b or not b.get("why"):
        return ""
    why = b["why"]
    order = list(range(len(why["opts"])))
    random.shuffle(order)
    return render_template("partials/why.html", bid=bid, q=why["q"], opts=[(i, why["opts"][i]) for i in order])


def _resolve(L, bid, how, status, d, extra_html=""):
    """Фиксирует исход: оценка -> SRS -> журнал -> оценки урока в сессии."""
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
        if d.get("mode") != "review":
            grades = dict(session.get("grades") or {})
            lg = dict(grades.get(L["id"], {}))
            lg.setdefault(bid, grade)
            grades[L["id"]] = lg
            session["grades"] = grades
    db.log_event(uid, "resolve", {"lesson": L["id"], "block": bid, "how": how, "status": status,
                                  "grade": grade, "attempts": attempts, "hints": hints, "ms": ms})
    if how == "ok":
        if status == "renamed":
            msg = "Верно: названия переменных другие, но логика та же."
        elif hints or attempts > 1:
            msg = "Верно (с подсказкой или не с первой попытки)."
        else:
            msg = "Точно, с первого раза."
        html = render_template("partials/resolved.html", msg=msg)
    elif how == "accepted":
        html = render_template("partials/resolved.html",
                               msg="Засчитано как «с трудом»: метод вернётся в повторение раньше.")
    else:
        html = extra_html
    return {"resolved": True, "failed": how == "revealed", "grade": grade, "html": html,
            "why_html": _why_html(L, bid)}


@bp.post("/check")
def check():
    d = _body()
    L, bid = _lesson_block(d)
    value = _answer(d)
    if not value.strip():
        return jsonify(resolved=False, status="empty", html=render_template("partials/empty.html"))
    attempts, hints, ms = _telemetry(d)
    r = core.compare_code(content.slot_target(L, bid), value)
    db.log_event(g.user["id"], "check", {"lesson": L["id"], "block": bid, "status": r["status"],
                                         "score": round(r["score"], 3), "attempt": attempts, "hints": hints})
    if r["status"] in ("perfect", "renamed"):
        return jsonify(_resolve(L, bid, "ok", r["status"], d))
    close = r["status"] == "close"
    html = render_template(
        "partials/check_result.html", close=close, pct=round(r["score"] * 100), summary=_parts(r),
        hl=core.highlight(value, r["extra"], r["ins"]),
    )
    return jsonify(resolved=False, status=r["status"], html=html)


@bp.post("/accept")
def accept():
    d = _body()
    L, bid = _lesson_block(d)
    value = _answer(d)
    r = core.compare_code(content.slot_target(L, bid), value)
    if r["status"] != "close":
        raise ApiError("Засчитать можно только вариант со статусом «почти».")
    return jsonify(_resolve(L, bid, "accepted", "close", d))


@bp.post("/reveal")
def reveal():
    d = _body()
    L, bid = _lesson_block(d)
    value = _answer(d)
    target = content.slot_target(L, bid)
    r = core.compare_code(target, value) if value.strip() else None
    hl = core.highlight(target, r["missed"] if r else None)
    html = render_template("partials/reference.html", hl=hl)
    return jsonify(_resolve(L, bid, "revealed", r["status"] if r else "empty", d, extra_html=html))


@bp.post("/hint")
def hint():
    d = _body()
    L, bid = _lesson_block(d)
    lines = content.slot_target(L, bid).split("\n")
    n = min(_int(d, "n", 1, 10000, 1), len(lines))
    db.log_event(g.user["id"], "hint", {"lesson": L["id"], "block": bid, "n": n})
    return jsonify(html=render_template("partials/hint.html", lines=lines[:n]), n=n, total=len(lines))


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
    return jsonify(ok=True)


# ---------- ИИ ----------

def _history(d):
    out = []
    for m in (d.get("history") or [])[-6:]:
        if isinstance(m, dict) and m.get("role") in ("user", "assistant") and isinstance(m.get("content"), str):
            out.append({"role": m["role"], "content": m["content"][:1200]})
    return out


@bp.post("/ai/chat")
def ai_chat():
    d = _body()
    L = _lesson(d)
    message = str(d.get("message", "")).strip()[:600]
    if not message:
        raise ApiError("Напиши вопрос.")
    attempt = str(d.get("attempt") or "")[:3000]
    focus = str(d.get("block") or "")
    if focus != "whole" and content.find_block(L, focus) is None:
        focus = ""
    names = [b["name"] for b in L["blocks"] if b["id"] in (d.get("missing") or [])]
    history = _history(d)
    messages = ai.tutor_messages(L, focus, names, attempt, history, message)
    material = ["tutor", L["id"], focus, message, attempt, history, names]
    target = content.slot_target(L, focus) if focus else None
    try:
        res = ai.ask(g.user["id"], material, messages, target)
    except ai.AIError as e:
        raise ApiError(e.message, e.status)
    db.log_event(g.user["id"], "ai", {"lesson": L["id"], "block": focus, "cached": res["cached"]})
    return jsonify(text=res["text"], left=res["left"], cached=res["cached"])


def _progress_summary(uid):
    srs = {k: v for k, v in db.srs_all(uid).items() if content.valid_key(k)}
    if not srs:
        return ""
    now = db.now_ms()
    rows = []
    for key, v in srs.items():
        lid, _, bid = key.partition("::")
        L = content.BY_ID[lid]
        rows.append((v["box"], -v["lapses"], "%s / %s: коробка %d, провалов %d, просмотров %d, %s" % (
            L["title"], content.find_block(L, bid)["name"], v["box"], v["lapses"], v["seen"],
            "пора повторять" if v["due"] <= now else "ещё не пора")))
    rows.sort()
    weak = [r[2] for r in rows[:10]]
    return "Всего методов в изучении: %d.\nСамые слабые:\n- %s" % (len(srs), "\n- ".join(weak))


@bp.post("/ai/advice")
def ai_advice():
    summary = _progress_summary(g.user["id"])
    if not summary:
        raise ApiError("Пока нет данных: пройди хотя бы один урок.")
    try:
        res = ai.ask(g.user["id"], ["advice", summary], ai.advice_messages(summary))
    except ai.AIError as e:
        raise ApiError(e.message, e.status)
    return jsonify(text=res["text"], left=res["left"])
