"""Редактор контента (только админ): паки, карточки-уроки и их методы.

Всё лежит в БД (packs, pack_items, lessons, blocks, block_options). Редактор правит таблицы и сразу перечитывает
контент в память (content.load), поэтому новые карточки появляются в «Уроках» без перезапуска.
У каждого пака и карточки есть автор: у старых это Bahodir, у новых имя того, кто создал.
"""
import ast
import json
import re
import secrets

from . import algos, assign, content, db
from .api import ApiError

ID_RE = re.compile(r"^[A-Za-z0-9_]{1,40}$")  # у старых методов id бывают в camelCase (searchRange)
CLASS_RE = re.compile(r"^class\s+\w[^\n]*:$")
MAX_BLOCKS = 40
MAX_ITEMS = 80
MAX_OPTS = 6
RESERVED = {"whole"}  # «whole» = слот «весь класс», у метода такого id быть не может


def _text(d, key, limit, label, required=False):
    v = d.get(key)
    v = "" if v is None else str(v).replace("\r\n", "\n").strip()
    if required and not v:
        raise ApiError("%s: поле не может быть пустым." % label)
    if len(v) > limit:
        raise ApiError("%s: не длиннее %d символов." % (label, limit))
    return v


def _syntax(code, label):
    try:
        ast.parse(code)
    except SyntaxError as e:
        raise ApiError("%s: ошибка синтаксиса в строке %s (%s)." % (label, e.lineno, e.msg))


def _slug(name):
    s = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")[:30] or "m"
    return "m_" + s if s in RESERVED else s


# ---------- проверка присланных данных ----------

def _why(b, label):
    w = b.get("why")
    w = w if isinstance(w, dict) else {}
    q = _text(w, "q", 400, label + ": вопрос")
    raw = w.get("opts") if isinstance(w.get("opts"), list) else []
    opts = [str(x).strip() for x in raw]
    if not q and not any(opts):
        return {"q": "", "opts": [], "ok": 0, "exp": ""}
    if not q:
        raise ApiError("%s: у вариантов ответа должен быть вопрос." % label)
    if not 2 <= len(opts) <= MAX_OPTS or not all(opts):
        raise ApiError("%s: нужно от 2 до %d непустых вариантов ответа." % (label, MAX_OPTS))
    if any(len(o) > 400 for o in opts):
        raise ApiError("%s: вариант ответа длиннее 400 символов." % label)
    try:
        ok = int(w.get("ok"))
    except (TypeError, ValueError):
        ok = -1
    if not 0 <= ok < len(opts):
        raise ApiError("%s: отметь верный вариант ответа." % label)
    return {"q": q, "opts": opts, "ok": ok, "exp": _text(w, "exp", 1200, label + ": пояснение")}


def lesson_data(d):
    """Проверяет и нормализует карточку. Возвращает словарь в том же виде, что и content.LESSONS."""
    cls = _text(d, "cls", 160, "Строка класса", True)
    if not CLASS_RE.match(cls):
        raise ApiError("Строка класса должна быть одной строкой вида «class Name:».")
    L = {
        "title": _text(d, "title", 120, "Название", True),
        "tag": _text(d, "tag", 80, "Тег"),
        "desc": _text(d, "desc", 600, "Описание"),
        "task": _text(d, "task", 3000, "Задача"),
        "imports": _text(d, "imports", 3000, "Импорты"),
        "cls": cls,
        "change": _text(d, "change", 3000, "Что изменилось") or None,
        "author": _text(d, "author", 60, "Автор"),
    }
    raw = d.get("blocks")
    if not isinstance(raw, list) or not raw:
        raise ApiError("Добавь хотя бы один метод.")
    if len(raw) > MAX_BLOCKS:
        raise ApiError("Методов не больше %d." % MAX_BLOCKS)
    if not all(isinstance(b, dict) for b in raw):
        raise ApiError("Некорректный список методов.")

    ids = [str(b.get("id") or "").strip() for b in raw]
    given = [i for i in ids if i]
    for i in given:
        if not ID_RE.match(i) or i in RESERVED:
            raise ApiError("Некорректный id метода: %s." % i)
    if len(given) != len(set(given)):
        raise ApiError("Повторяющийся id метода.")
    used = set(given)

    blocks = []
    for n, (b, bid) in enumerate(zip(raw, ids), 1):
        name = _text(b, "name", 60, "Метод %d: имя" % n, True)
        label = "Метод «%s»" % name
        code = _text(b, "code", 8000, label + ": код", True)
        _syntax(code, label)
        if not bid:
            base, k, bid = _slug(name), 2, _slug(name)
            while bid in used:
                bid = "%s_%d" % (base, k)
                k += 1
            used.add(bid)
        blocks.append({"id": bid, "name": name, "note": _text(b, "note", 600, label + ": пояснение"),
                       "code": code, "why": _why(b, label)})
    L["blocks"] = blocks
    _syntax(content.full_code(L), "Весь класс")
    return L


def pack_data(d):
    items = []
    raw = d.get("items") or []
    if not isinstance(raw, list) or len(raw) > MAX_ITEMS:
        raise ApiError("В паке не больше %d пунктов." % MAX_ITEMS)
    for i, it in enumerate(raw, 1):
        if not isinstance(it, dict):
            raise ApiError("Некорректный пункт %d." % i)
        lid = str(it.get("lesson") or "").strip() or None
        if lid and lid not in content.BY_ID:
            raise ApiError("Пункт %d: такой карточки нет." % i)
        name = _text(it, "name", 120, "Пункт %d: название" % i) or (content.BY_ID[lid]["title"] if lid else "")
        if not name:
            raise ApiError("Пункт %d: впиши название." % i)
        items.append({"name": name, "category": _text(it, "category", 80, "Пункт %d: категория" % i),
                      "desc": _text(it, "desc", 600, "Пункт %d: описание" % i), "lesson": lid})
    ids = [x["lesson"] for x in items if x["lesson"]]
    if len(ids) != len(set(ids)):
        raise ApiError("Одна карточка не может стоять в паке дважды.")
    return {"title": _text(d, "title", 80, "Название пака", True), "desc": _text(d, "desc", 600, "Описание"),
            "author": _text(d, "author", 60, "Автор"), "items": items}


# ---------- запись в БД ----------

def _next_pos(con, table, where="", params=()):
    r = con.execute("SELECT COALESCE(MAX(position), -1) + 1 AS p FROM %s %s" % (table, where), params).fetchone()
    return r["p"]


def _write_blocks(con, lid, blocks):
    con.executemany(
        "INSERT INTO blocks(lesson_id, id, position, name, note, code, why_q, why_ok, why_exp) VALUES (?,?,?,?,?,?,?,?,?)",
        [(lid, b["id"], i, b["name"], b["note"], b["code"], b["why"]["q"], b["why"]["ok"], b["why"]["exp"])
         for i, b in enumerate(blocks)],
    )
    con.executemany(
        "INSERT INTO block_options(lesson_id, block_id, position, text) VALUES (?,?,?,?)",
        [(lid, b["id"], j, text) for b in blocks for j, text in enumerate(b["why"]["opts"])],
    )


def _write_lesson(con, lid, L, new):
    if new:
        con.execute(
            "INSERT INTO lessons(id, position, title, tag, descr, task, imports, cls, change, author) "
            "VALUES (?,?,?,?,?,?,?,?,?,?)",
            (lid, _next_pos(con, "lessons"), L["title"], L["tag"], L["desc"], L["task"], L["imports"], L["cls"],
             L["change"], L["author"]),
        )
    else:
        con.execute(
            "UPDATE lessons SET title=?, tag=?, descr=?, task=?, imports=?, cls=?, change=?, author=? WHERE id=?",
            (L["title"], L["tag"], L["desc"], L["task"], L["imports"], L["cls"], L["change"], L["author"], lid),
        )
        con.execute("DELETE FROM block_options WHERE lesson_id=?", (lid,))
        con.execute("DELETE FROM blocks WHERE lesson_id=?", (lid,))
    _write_blocks(con, lid, L["blocks"])


def _write_items(con, pid, items):
    con.execute("DELETE FROM pack_items WHERE pack_id=?", (pid,))
    con.executemany(
        "INSERT INTO pack_items(pack_id, position, name, category, descr, lesson_id) VALUES (?,?,?,?,?,?)",
        [(pid, i, it["name"], it["category"], it["desc"], it["lesson"]) for i, it in enumerate(items)],
    )


def _reload(con):
    con.commit()
    content.load(con)


def _new_id(prefix, taken):
    while True:
        x = prefix + secrets.token_hex(4)
        if x not in taken:
            return x


def _full(L):
    """Карточка целиком, вместе с верными ответами (только для админа)."""
    return {
        "id": L["id"], "title": L["title"], "tag": L["tag"], "desc": L["desc"], "task": L["task"],
        "imports": L["imports"], "cls": L["cls"], "change": L.get("change") or "", "author": L.get("author", ""),
        "blocks": [{"id": b["id"], "name": b["name"], "note": b["note"], "code": b["code"],
                    "why": {"q": b["why"]["q"], "opts": list(b["why"]["opts"]), "ok": b["why"]["ok"],
                            "exp": b["why"]["exp"]}} for b in L["blocks"]],
    }


def _blockers(con, lid):
    """Где карточка используется: удалять такую нельзя."""
    out = ["паке «%s»" % p["title"] for p in content.PACKS if any(it["lesson"] == lid for it in p["items"])]
    out += ["алгоритме «%s»" % a["title"] for a in algos.ALGOS if lid == a["template"] or lid in a["variations"]]
    for r in con.execute("SELECT title, lessons FROM assignments").fetchall():
        try:
            if lid in json.loads(r["lessons"]):
                out.append("задании «%s»" % r["title"])
        except ValueError:
            pass
    return out


def register(bp):
    from flask import g, jsonify

    from .api import _body

    def guard():
        if not db.is_admin(g.user["id"]):
            raise ApiError("Только для админа.", 403)
        return g.user["id"]

    def author_for(uid):
        return assign.get_name(uid) or g.user["username"]

    def lesson_or_404(lid):
        L = content.BY_ID.get(lid)
        if L is None:
            raise ApiError("Карточка не найдена.", 404)
        return L

    def pack_or_404(pid):
        p = content.get_pack(pid)
        if p is None:
            raise ApiError("Пак не найден.", 404)
        return p

    @bp.get("/admin/content")
    def ed_content():
        guard()
        packs = [{"id": p["id"], "title": p["title"], "desc": p["desc"], "author": p.get("author", ""),
                  "algos": sum(1 for a in algos.ALGOS if a["pack"] == p["id"]),
                  "items": [dict(it) for it in p["items"]]} for p in content.PACKS]
        lessons = [{"id": L["id"], "title": L["title"], "tag": L["tag"], "desc": L["desc"],
                    "author": L.get("author", ""), "methods": len(L["blocks"]),
                    "packs": [p["title"] for p in content.PACKS if any(it["lesson"] == L["id"] for it in p["items"])]}
                   for L in content.LESSONS]
        return jsonify(packs=packs, lessons=lessons)

    # ----- карточки -----

    @bp.get("/admin/lessons/<lid>")
    def ed_lesson_get(lid):
        guard()
        return jsonify(lesson=_full(lesson_or_404(lid)))

    @bp.post("/admin/lessons")
    def ed_lesson_create():
        uid = guard()
        d = _body()
        L = lesson_data(d)
        L["author"] = L["author"] or author_for(uid)
        pid = str(d.get("pack") or "").strip()
        if pid:
            pack_or_404(pid)
        con = db.get_db()
        lid = _new_id("l", content.BY_ID)
        _write_lesson(con, lid, L, True)
        if pid:
            con.execute(
                "INSERT INTO pack_items(pack_id, position, name, category, descr, lesson_id) VALUES (?,?,?,?,?,?)",
                (pid, _next_pos(con, "pack_items", "WHERE pack_id=?", (pid,)), L["title"], L["tag"], L["desc"], lid),
            )
        db.log_event(uid, "editor", {"op": "lesson_create", "lesson": lid})
        _reload(con)
        return jsonify(lesson=_full(content.BY_ID[lid])), 201

    @bp.put("/admin/lessons/<lid>")
    def ed_lesson_update(lid):
        uid = guard()
        old = lesson_or_404(lid)
        L = lesson_data(_body())
        L["author"] = L["author"] or old.get("author") or author_for(uid)
        con = db.get_db()
        _write_lesson(con, lid, L, False)
        db.log_event(uid, "editor", {"op": "lesson_update", "lesson": lid})
        _reload(con)
        return jsonify(lesson=_full(content.BY_ID[lid]))

    @bp.delete("/admin/lessons/<lid>")
    def ed_lesson_delete(lid):
        uid = guard()
        lesson_or_404(lid)
        con = db.get_db()
        where = _blockers(con, lid)
        if where:
            raise ApiError("Карточка используется в %s. Сначала убери её оттуда." % ", ".join(where), 409)
        prefix = lid + "::"
        con.execute("DELETE FROM block_options WHERE lesson_id=?", (lid,))
        con.execute("DELETE FROM blocks WHERE lesson_id=?", (lid,))
        con.execute("DELETE FROM lessons WHERE id=?", (lid,))
        con.execute("DELETE FROM done WHERE lesson_id=?", (lid,))
        con.execute("DELETE FROM srs WHERE substr(key, 1, ?) = ?", (len(prefix), prefix))
        db.log_event(uid, "editor", {"op": "lesson_delete", "lesson": lid})
        _reload(con)
        return jsonify(ok=True)

    # ----- паки -----

    @bp.post("/admin/packs")
    def ed_pack_create():
        uid = guard()
        P = pack_data(_body())
        P["author"] = P["author"] or author_for(uid)
        con = db.get_db()
        pid = _new_id("p", {p["id"] for p in content.PACKS})
        con.execute("INSERT INTO packs(id, position, title, descr, author) VALUES (?,?,?,?,?)",
                    (pid, _next_pos(con, "packs"), P["title"], P["desc"], P["author"]))
        _write_items(con, pid, P["items"])
        db.log_event(uid, "editor", {"op": "pack_create", "pack": pid})
        _reload(con)
        return jsonify(id=pid), 201

    @bp.put("/admin/packs/<pid>")
    def ed_pack_update(pid):
        uid = guard()
        old = pack_or_404(pid)
        P = pack_data(_body())
        P["author"] = P["author"] or old.get("author") or author_for(uid)
        con = db.get_db()
        con.execute("UPDATE packs SET title=?, descr=?, author=? WHERE id=?", (P["title"], P["desc"], P["author"], pid))
        _write_items(con, pid, P["items"])
        db.log_event(uid, "editor", {"op": "pack_update", "pack": pid})
        _reload(con)
        return jsonify(ok=True)

    @bp.delete("/admin/packs/<pid>")
    def ed_pack_delete(pid):
        uid = guard()
        pack_or_404(pid)
        if any(a["pack"] == pid for a in algos.ALGOS):
            raise ApiError("В паке есть алгоритмы с задачами, их пока нельзя удалить из редактора.", 409)
        con = db.get_db()
        con.execute("DELETE FROM pack_items WHERE pack_id=?", (pid,))
        con.execute("DELETE FROM packs WHERE id=?", (pid,))
        db.log_event(uid, "editor", {"op": "pack_delete", "pack": pid})
        _reload(con)
        return jsonify(ok=True)

    @bp.put("/admin/pack-order")
    def ed_pack_order():
        guard()
        ids = _body().get("ids")
        if not isinstance(ids, list) or sorted(map(str, ids)) != sorted(p["id"] for p in content.PACKS):
            raise ApiError("Список паков не совпадает с текущим.")
        con = db.get_db()
        con.executemany("UPDATE packs SET position=? WHERE id=?", [(i, str(x)) for i, x in enumerate(ids)])
        _reload(con)
        return jsonify(ok=True)

    from . import aimaker

    aimaker.register(bp, guard)
