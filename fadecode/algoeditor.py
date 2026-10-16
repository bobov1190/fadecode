"""Редактор алгоритмов и задач (только админ): алгоритм = шаблон-карточка + вариации + задачи с тестами.

Задачи хранятся в таблице problems. Тесты исполняются в браузере (Pyodide), сервер код не запускает: он проверяет только
синтаксис и что в заготовке и эталоне есть class Solution с нужным методом. Прогон эталона на тестах делает редактор в браузере.
"""
import ast
import json
import re
import secrets

from . import algos, content, db
from .api import ApiError
from .editor import ID_RE, _next_pos, _reload, _syntax, _text

LEVELS = ("easy", "medium", "hard")
FN_RE = re.compile(r"^[A-Za-z_]\w{0,40}$")
MAX_PROBLEMS = 40
MAX_VARIATIONS = 12


def _method(code, fn, label):
    for node in ast.parse(code).body:
        if isinstance(node, ast.ClassDef) and node.name == "Solution":
            if any(isinstance(n, ast.FunctionDef) and n.name == fn for n in node.body):
                return
    raise ApiError("%s: нужен class Solution с методом %s." % (label, fn))


def _strs(raw, n_max, limit, label):
    if raw is None:
        return []
    if not isinstance(raw, list) or len(raw) > n_max:
        raise ApiError("%s: не больше %d строк." % (label, n_max))
    out = [str(x).replace("\r\n", "\n").strip() for x in raw]
    out = [x for x in out if x]
    if any(len(x) > limit for x in out):
        raise ApiError("%s: строка длиннее %d символов." % (label, limit))
    return out


def problem_data(p, n):
    if not isinstance(p, dict):
        raise ApiError("Некорректная задача %d." % n)
    title = _text(p, "title", 120, "Задача %d: название" % n, True)
    label = "Задача «%s»" % title
    level = str(p.get("level") or "")
    if level not in LEVELS:
        raise ApiError("%s: сложность easy, medium или hard." % label)
    fn = str(p.get("fn") or "").strip()
    if not FN_RE.match(fn):
        raise ApiError("%s: имя метода (fn) только латиница, цифры и _." % label)
    num = p.get("num")
    try:
        num = int(num) if num not in (None, "") else None
    except (TypeError, ValueError):
        raise ApiError("%s: номер должен быть числом." % label)
    out = {
        "id": str(p.get("id") or "").strip(), "num": num, "title": title, "level": level, "fn": fn,
        "statement": _text(p, "statement", 4000, label + ": условие", True),
        "examples": _strs(p.get("examples"), 8, 400, label + ": примеры"),
        "hints": _strs(p.get("hints"), 5, 600, label + ": подсказки"),
        "starter": _text(p, "starter", 6000, label + ": заготовка", True),
        "reference": _text(p, "reference", 8000, label + ": эталон", True),
        "insight": _text(p, "insight", 2000, label + ": разбор"),
        "pre": _text(p, "pre", 8000, label + ": pre"),
        "tests": _text(p, "tests", 12000, label + ": тесты", True),
    }
    if out["id"] and not ID_RE.match(out["id"]):
        raise ApiError("%s: некорректный id." % label)
    for key, name in (("starter", "заготовка"), ("reference", "эталон"), ("pre", "pre"), ("tests", "тесты")):
        if out[key]:
            _syntax(out[key], "%s: %s" % (label, name))
    _method(out["starter"], fn, label + ": заготовка")
    _method(out["reference"], fn, label + ": эталон")
    return out


def algo_data(d):
    title = _text(d, "title", 120, "Название", True)
    template = str(d.get("template") or "").strip()
    if template not in content.BY_ID:
        raise ApiError("Выбери карточку-шаблон.")
    raw = d.get("variations") or []
    if not isinstance(raw, list) or len(raw) > MAX_VARIATIONS:
        raise ApiError("Вариаций не больше %d." % MAX_VARIATIONS)
    variations = [str(x) for x in raw]
    if any(v not in content.BY_ID for v in variations):
        raise ApiError("Среди вариаций есть несуществующая карточка.")
    if template in variations or len(set(variations)) != len(variations):
        raise ApiError("Шаблон и вариации не должны повторяться.")
    pack = str(d.get("pack") or "").strip()
    if content.get_pack(pack) is None:
        raise ApiError("Выбери пак для алгоритма.")
    rawp = d.get("problems")
    if rawp is None:
        rawp = []
    if not isinstance(rawp, list) or len(rawp) > MAX_PROBLEMS:
        raise ApiError("Задач не больше %d." % MAX_PROBLEMS)
    problems = [problem_data(p, i) for i, p in enumerate(rawp, 1)]
    given = [p["id"] for p in problems if p["id"]]
    if len(given) != len(set(given)):
        raise ApiError("Повторяющийся id задачи.")
    return {"title": title, "tag": _text(d, "tag", 80, "Тег"), "desc": _text(d, "desc", 600, "Описание"),
            "template": template, "variations": variations, "pack": pack, "problems": problems}


def _full(A):
    return {"id": A["id"], "title": A["title"], "tag": A["tag"], "desc": A["desc"], "template": A["template"],
            "variations": list(A["variations"]), "pack": A["pack"],
            "problems": [{k: P[k] for k in ("id", "num", "title", "level", "fn", "statement", "examples", "hints",
                                            "starter", "reference", "insight", "pre", "tests")} for P in A["problems"]]}


def _write_problems(con, aid, problems):
    owned = {P["id"] for P in algos.BY_ID[aid]["problems"]} if aid in algos.BY_ID else set()
    taken = set(algos.PROBLEMS) - owned
    keep = set()
    for i, p in enumerate(problems):
        pid = p["id"]
        if pid and pid in taken:
            raise ApiError("Задача с id %s уже есть в другом алгоритме." % pid)
        if not pid:
            while True:
                pid = "pr_" + secrets.token_hex(4)
                if pid not in taken and pid not in keep:
                    break
        keep.add(pid)
        row = (aid, i, p["num"], p["title"], p["level"], p["fn"], p["statement"],
               json.dumps(p["examples"], ensure_ascii=False), json.dumps(p["hints"], ensure_ascii=False),
               p["starter"], p["reference"], p["insight"], p["pre"], p["tests"])
        if pid in owned:
            con.execute(
                "UPDATE problems SET algo_id=?, position=?, num=?, title=?, level=?, fn=?, statement=?, examples=?, "
                "hints=?, starter=?, solution=?, insight=?, pre=?, tests=? WHERE id=?", row + (pid,))
        else:
            con.execute(
                "INSERT INTO problems(id, algo_id, position, num, title, level, fn, statement, examples, hints, "
                "starter, solution, insight, pre, tests) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (pid,) + row)
    for pid in owned - keep:
        con.execute("DELETE FROM problem_state WHERE problem_id=?", (pid,))
        con.execute("DELETE FROM problems WHERE id=?", (pid,))


def register(bp, guard):
    from flask import jsonify

    from .api import _body

    def algo_or_404(aid):
        A = algos.BY_ID.get(aid)
        if A is None:
            raise ApiError("Алгоритм не найден.", 404)
        return A

    @bp.get("/admin/algos")
    def ed_algos():
        guard()
        return jsonify(algos=[{"id": A["id"], "title": A["title"], "tag": A["tag"], "pack": A["pack"],
                               "template": A["template"], "problems": len(A["problems"])} for A in algos.ALGOS])

    @bp.get("/admin/algos/<aid>")
    def ed_algo_get(aid):
        guard()
        return jsonify(algo=_full(algo_or_404(aid)))

    @bp.post("/admin/algos")
    def ed_algo_create():
        uid = guard()
        D = algo_data(_body())
        con = db.get_db()
        aid = "a_" + secrets.token_hex(4)
        while aid in algos.BY_ID:
            aid = "a_" + secrets.token_hex(4)
        con.execute(
            "INSERT INTO algos(id, position, title, tag, descr, template_lesson, variations, pack_id) VALUES (?,?,?,?,?,?,?,?)",
            (aid, _next_pos(con, "algos"), D["title"], D["tag"], D["desc"], D["template"],
             json.dumps(D["variations"]), D["pack"]))
        _write_problems(con, aid, D["problems"])
        db.log_event(uid, "editor", {"op": "algo_create", "algo": aid})
        _reload(con)
        return jsonify(algo=_full(algos.BY_ID[aid])), 201

    @bp.put("/admin/algos/<aid>")
    def ed_algo_update(aid):
        uid = guard()
        algo_or_404(aid)
        D = algo_data(_body())
        con = db.get_db()
        con.execute("UPDATE algos SET title=?, tag=?, descr=?, template_lesson=?, variations=?, pack_id=? WHERE id=?",
                    (D["title"], D["tag"], D["desc"], D["template"], json.dumps(D["variations"]), D["pack"], aid))
        _write_problems(con, aid, D["problems"])
        db.log_event(uid, "editor", {"op": "algo_update", "algo": aid})
        _reload(con)
        return jsonify(algo=_full(algos.BY_ID[aid]))

    @bp.delete("/admin/algos/<aid>")
    def ed_algo_delete(aid):
        uid = guard()
        A = algo_or_404(aid)
        con = db.get_db()
        for P in A["problems"]:
            con.execute("DELETE FROM problem_state WHERE problem_id=?", (P["id"],))
        con.execute("DELETE FROM problems WHERE algo_id=?", (aid,))
        con.execute("DELETE FROM algo_state WHERE algo_id=?", (aid,))
        con.execute("DELETE FROM algos WHERE id=?", (aid,))
        db.log_event(uid, "editor", {"op": "algo_delete", "algo": aid})
        _reload(con)
        return jsonify(ok=True)
