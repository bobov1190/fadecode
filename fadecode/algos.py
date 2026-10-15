"""Алгоритмы: шаблон (обычный урок с призраком и вспоминанием) и задачи на него.

Тесты задач выполняются в браузере (Pyodide), сервер код не запускает: он хранит условия, подсказки,
черновики, попытки и точку, где ученик остановился.
"""
import json
import os

from . import content, db

ALGOS = []
BY_ID = {}
PROBLEMS = {}
STAGES = ("lesson-read", "lesson-copy", "lesson-recall", "problem")
DRAFT_MAX = 20000


def seed(con, force=False):
    if force:
        con.execute("DELETE FROM problems")
        con.execute("DELETE FROM algos")
    elif con.execute("SELECT COUNT(*) AS n FROM algos").fetchone()["n"]:
        return False
    path = os.path.join(content._DATA, "algos.json")
    if not os.path.isfile(path):
        return False
    with open(path, encoding="utf-8") as f:
        algos = json.load(f)
    lessons = {r["id"] for r in con.execute("SELECT id FROM lessons").fetchall()}
    for a in algos:
        for lid in [a["template"]] + a["variations"]:
            if lid not in lessons:
                raise RuntimeError("В алгоритме %s нет урока %s" % (a["id"], lid))
    con.executemany(
        "INSERT INTO algos(id, position, title, tag, descr, template_lesson, variations, pack_id) VALUES (?,?,?,?,?,?,?,?)",
        [(a["id"], i, a["title"], a.get("tag", ""), a.get("desc", ""), a["template"],
          json.dumps(a["variations"]), a.get("pack", "algo")) for i, a in enumerate(algos)],
    )
    rows = []
    for a in algos:
        for i, P in enumerate(a["problems"]):
            rows.append((P["id"], a["id"], i, P.get("num"), P["title"], P["level"], P["fn"], P["statement"],
                         json.dumps(P["examples"], ensure_ascii=False), json.dumps(P["hints"], ensure_ascii=False),
                         P["starter"], P["reference"], P["insight"], P.get("pre", ""), P["tests"]))
    con.executemany(
        "INSERT INTO problems(id, algo_id, position, num, title, level, fn, statement, examples, hints, starter, "
        "solution, insight, pre, tests) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        rows,
    )
    return True


def load(con):
    algos = [
        {"id": r["id"], "title": r["title"], "tag": r["tag"], "desc": r["descr"], "template": r["template_lesson"],
         "variations": json.loads(r["variations"]), "pack": r["pack_id"], "problems": []}
        for r in con.execute(
            "SELECT id, title, tag, descr, template_lesson, variations, pack_id FROM algos ORDER BY position"
        ).fetchall()
    ]
    by_id = {a["id"]: a for a in algos}
    problems = {}
    for r in con.execute(
        "SELECT id, algo_id, num, title, level, fn, statement, examples, hints, starter, solution, insight, pre, tests "
        "FROM problems ORDER BY algo_id, position"
    ).fetchall():
        P = {"id": r["id"], "algo": r["algo_id"], "num": r["num"], "title": r["title"], "level": r["level"],
             "fn": r["fn"], "statement": r["statement"], "examples": json.loads(r["examples"]),
             "hints": json.loads(r["hints"]), "starter": r["starter"], "reference": r["solution"],
             "insight": r["insight"], "pre": r["pre"], "tests": r["tests"]}
        by_id[r["algo_id"]]["problems"].append(P)
        problems[P["id"]] = P
    ALGOS[:] = algos
    BY_ID.clear()
    BY_ID.update(by_id)
    PROBLEMS.clear()
    PROBLEMS.update(problems)


def algo_for_lesson(lid):
    for a in ALGOS:
        if lid == a["template"]:
            return {"id": a["id"], "title": a["title"], "role": "template"}
        if lid in a["variations"]:
            return {"id": a["id"], "title": a["title"], "role": "variation"}
    return None


def states(uid):
    rows = db.get_db().execute(
        "SELECT problem_id, status, attempts, hints FROM problem_state WHERE user_id=?", (uid,)
    ).fetchall()
    return {r["problem_id"]: dict(r) for r in rows}


def _get(uid, pid):
    r = db.get_db().execute(
        "SELECT status, attempts, hints, code FROM problem_state WHERE user_id=? AND problem_id=?", (uid, pid)
    ).fetchone()
    return dict(r) if r else {"status": "new", "attempts": 0, "hints": 0, "code": ""}


def _put(uid, pid, row):
    con = db.get_db()
    status = "open" if row["status"] == "new" else row["status"]
    con.execute(
        "INSERT INTO problem_state(user_id, problem_id, status, attempts, hints, code, at) VALUES (?,?,?,?,?,?,?) "
        "ON CONFLICT (user_id, problem_id) DO UPDATE SET status = excluded.status, attempts = excluded.attempts, "
        "hints = excluded.hints, code = excluded.code, at = excluded.at",
        (uid, pid, status, row["attempts"], row["hints"], row["code"], db.now_ms()),
    )
    con.commit()


def get_resume(uid, aid):
    r = db.get_db().execute("SELECT stage, ref FROM algo_state WHERE user_id=? AND algo_id=?", (uid, aid)).fetchone()
    return {"stage": r["stage"], "ref": r["ref"]} if r else None


def set_resume(uid, aid, stage, ref):
    con = db.get_db()
    con.execute(
        "INSERT INTO algo_state(user_id, algo_id, stage, ref, at) VALUES (?,?,?,?,?) "
        "ON CONFLICT (user_id, algo_id) DO UPDATE SET stage = excluded.stage, ref = excluded.ref, at = excluded.at",
        (uid, aid, stage, ref, db.now_ms()),
    )
    con.commit()


def pack_algos(pid, uid, done):
    if not any(a["pack"] == pid for a in ALGOS):
        return []
    st = states(uid)
    out = []
    for a in ALGOS:
        if a["pack"] != pid:
            continue
        solved = sum(1 for P in a["problems"] if st.get(P["id"], {}).get("status") == "solved")
        out.append({"id": a["id"], "title": a["title"], "tag": a["tag"], "desc": a["desc"],
                    "template_done": a["template"] in done, "solved": solved, "total": len(a["problems"])})
    return out


def pack_counts(p, uid, done):
    al = pack_algos(p["id"], uid, done)
    if al:
        return {"total": len(al), "ready": len(al),
                "finished": sum(1 for a in al if a["total"] and a["solved"] == a["total"])}
    return {"total": len(p["items"]), "ready": content.ready_count(p),
            "finished": sum(1 for it in p["items"] if it["lesson"] and it["lesson"] in done)}


def register(bp):
    from flask import g, jsonify

    from . import ai, api
    from .api import ApiError, _body, _int

    def _algo(aid):
        A = BY_ID.get(aid)
        if A is None:
            raise ApiError("Неизвестный алгоритм.", 404)
        return A

    def _prob(pid):
        P = PROBLEMS.get(str(pid))
        if P is None:
            raise ApiError("Неизвестная задача.", 404)
        return P

    def _lesson_ref(lid, done):
        L = content.BY_ID[lid]
        return {"id": lid, "title": L["title"], "tag": L["tag"], "desc": L["desc"], "methods": len(L["blocks"]),
                "done": lid in done}

    @bp.get("/algos/<aid>")
    def algo(aid):
        A = _algo(aid)
        uid = g.user["id"]
        done = db.done_map(uid)
        st = states(uid)
        problems = [{"id": P["id"], "num": P["num"], "title": P["title"], "level": P["level"],
                     "status": st.get(P["id"], {}).get("status", "new"),
                     "attempts": st.get(P["id"], {}).get("attempts", 0)} for P in A["problems"]]
        return jsonify(id=A["id"], title=A["title"], tag=A["tag"], desc=A["desc"],
                       template=_lesson_ref(A["template"], done),
                       variations=[_lesson_ref(x, done) for x in A["variations"] if x in content.BY_ID],
                       problems=problems, resume=get_resume(uid, aid), pack=A["pack"])

    @bp.put("/algos/<aid>/state")
    def algo_state(aid):
        A = _algo(aid)
        d = _body()
        stage = str(d.get("stage", ""))
        ref = str(d.get("ref", ""))[:60]
        if stage not in STAGES:
            raise ApiError("Неизвестный этап.")
        if stage == "problem":
            if _prob(ref)["algo"] != aid:
                raise ApiError("Эта задача из другого алгоритма.")
        elif ref not in [A["template"]] + A["variations"]:
            raise ApiError("Этот урок из другого алгоритма.")
        set_resume(g.user["id"], aid, stage, ref)
        return jsonify(ok=True)

    @bp.get("/problems/<pid>")
    def problem(pid):
        P = _prob(pid)
        row = _get(g.user["id"], pid)
        ids = [x["id"] for x in BY_ID[P["algo"]]["problems"]]
        i = ids.index(pid)
        return jsonify(
            id=P["id"], num=P["num"], title=P["title"], level=P["level"], fn=P["fn"], statement=P["statement"],
            examples=P["examples"], starter=P["starter"], pre=P["pre"], tests=P["tests"],
            hints=P["hints"][:row["hints"]], hints_total=len(P["hints"]), draft=row["code"],
            status=row["status"], attempts=row["attempts"],
            algo={"id": P["algo"], "title": BY_ID[P["algo"]]["title"]},
            prev=ids[i - 1] if i > 0 else None, next=ids[i + 1] if i + 1 < len(ids) else None,
        )

    @bp.put("/problems/<pid>/draft")
    def problem_draft(pid):
        P = _prob(pid)
        d = _body()
        uid = g.user["id"]
        row = _get(uid, pid)
        row["code"] = str(d.get("code", ""))[:DRAFT_MAX]
        _put(uid, pid, row)
        set_resume(uid, P["algo"], "problem", pid)
        return jsonify(ok=True)

    @bp.post("/problems/<pid>/result")
    def problem_result(pid):
        _prob(pid)
        d = _body()
        status = d.get("status")
        if status not in ("ok", "fail", "error"):
            raise ApiError("Неизвестный результат.")
        uid = g.user["id"]
        row = _get(uid, pid)
        row["attempts"] += 1
        if status == "ok":
            row["status"] = "solved"
        _put(uid, pid, row)
        db.log_event(uid, "problem", {"problem": pid, "status": status, "attempts": row["attempts"],
                                      "hints": row["hints"]})
        return jsonify(solved=row["status"] == "solved", attempts=row["attempts"])

    @bp.post("/problems/<pid>/hint")
    def problem_hint(pid):
        P = _prob(pid)
        d = _body()
        uid = g.user["id"]
        n = _int(d, "n", 1, len(P["hints"]), 1)
        row = _get(uid, pid)
        row["hints"] = max(row["hints"], n)
        _put(uid, pid, row)
        db.log_event(uid, "problem_hint", {"problem": pid, "n": n})
        return jsonify(hints=P["hints"][:row["hints"]], total=len(P["hints"]))

    @bp.post("/problems/<pid>/solution")
    def problem_solution(pid):
        P = _prob(pid)
        uid = g.user["id"]
        row = _get(uid, pid)
        if row["status"] != "solved":
            row["status"] = "given_up"
            _put(uid, pid, row)
        db.log_event(uid, "problem_solution", {"problem": pid, "status": row["status"]})
        return jsonify(reference=P["reference"], insight=P["insight"], status=row["status"])

    @bp.post("/ai/problem")
    def ai_problem():
        d = _body()
        P = _prob(d.get("problem", ""))
        message = str(d.get("message", "")).strip()[:600]
        if not message:
            raise ApiError("Пустой вопрос.")
        attempt = str(d.get("attempt") or "")[:4000]
        error = str(d.get("error") or "")[:800]
        history = api._history(d)
        messages = ai.problem_messages(P, attempt, error, history, message)
        material = ["problem", P["id"], message, attempt, error, history]
        try:
            res = ai.ask(g.user["id"], material, messages, P["reference"])
        except ai.AIError as e:
            raise ApiError(e.message, e.status)
        db.log_event(g.user["id"], "ai", {"problem": P["id"], "cached": res["cached"]})
        return jsonify(text=res["text"], left=res["left"], cached=res["cached"])
