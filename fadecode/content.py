"""Контент: пакеты и уроки лежат в БД (packs, pack_items, lessons, blocks, block_options).

При старте контент один раз читается из БД в память (load) и дальше живёт в LESSONS, PACKS и BY_ID.
Это те же словари, что раньше давал JSON, поэтому views, api и ai не менялись.
data/*.json остаётся стартовым набором: он заливается в пустую базу сам, а вручную командой `flask seed`.
"""
import json
import os
import random

_DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

# Объекты общие на весь процесс: load() меняет их на месте, поэтому ссылки на них не устаревают.
LESSONS = []
PACKS = []
BY_ID = {}


def _read_json(name):
    with open(os.path.join(_DATA, name), encoding="utf-8") as f:
        return json.load(f)


def seed_from_json(con, force=False):
    """Заливает data/*.json в БД. Без force работает только в пустой базе.

    С force весь контент в БД заменяется содержимым JSON (прогресс пользователей не трогается:
    он ссылается на уроки по текстовым id). Возвращает True, если что-то записано. Коммитит вызывающий.
    """
    if not force and con.execute("SELECT COUNT(*) AS n FROM lessons").fetchone()["n"]:
        return False
    lessons = _read_json("lessons.json")
    packs = _read_json("packs.json")
    ids = {l["id"] for l in lessons}
    for p in packs:
        for it in p["items"]:
            if it["lesson"] and it["lesson"] not in ids:
                raise RuntimeError("В пакете %s ссылка на несуществующий урок %s" % (p["id"], it["lesson"]))

    if force:
        for table in ("problems", "algos", "pack_items", "packs", "block_options", "blocks", "lessons"):
            con.execute("DELETE FROM " + table)

    con.executemany(
        "INSERT INTO lessons(id, position, title, tag, descr, task, imports, cls, change) VALUES (?,?,?,?,?,?,?,?,?)",
        [(l["id"], i, l["title"], l.get("tag", ""), l.get("desc", ""), l.get("task", ""),
          l.get("imports", ""), l["cls"], l.get("change")) for i, l in enumerate(lessons)],
    )
    blocks, options = [], []
    for l in lessons:
        for i, b in enumerate(l["blocks"]):
            w = b["why"]
            blocks.append((l["id"], b["id"], i, b["name"], b.get("note", ""), b["code"], w["q"], w["ok"], w["exp"]))
            options.extend((l["id"], b["id"], j, text) for j, text in enumerate(w["opts"]))
    con.executemany(
        "INSERT INTO blocks(lesson_id, id, position, name, note, code, why_q, why_ok, why_exp) "
        "VALUES (?,?,?,?,?,?,?,?,?)",
        blocks,
    )
    con.executemany("INSERT INTO block_options(lesson_id, block_id, position, text) VALUES (?,?,?,?)", options)
    con.executemany(
        "INSERT INTO packs(id, position, title, descr) VALUES (?,?,?,?)",
        [(p["id"], i, p["title"], p.get("desc", "")) for i, p in enumerate(packs)],
    )
    con.executemany(
        "INSERT INTO pack_items(pack_id, position, name, category, descr, lesson_id) VALUES (?,?,?,?,?,?)",
        [(p["id"], j, it["name"], it.get("category", ""), it.get("desc", ""), it["lesson"] or None)
         for p in packs for j, it in enumerate(p["items"])],
    )
    from . import algos

    algos.seed(con, force=True)
    return True


def load(con):
    """Читает контент из БД в LESSONS, PACKS и BY_ID (на месте)."""
    rows = con.execute(
        "SELECT id, title, tag, descr, task, imports, cls, change FROM lessons ORDER BY position"
    ).fetchall()
    lessons = [
        {"id": r["id"], "title": r["title"], "tag": r["tag"], "desc": r["descr"], "task": r["task"],
         "imports": r["imports"], "cls": r["cls"], "blocks": []}
        for r in rows
    ]
    for l, r in zip(lessons, rows):
        if r["change"] is not None:  # необязательное поле «Что изменилось» у уроков-вариаций
            l["change"] = r["change"]
    by_id = {l["id"]: l for l in lessons}
    by_block = {}
    for r in con.execute(
        "SELECT lesson_id, id, name, note, code, why_q, why_ok, why_exp FROM blocks ORDER BY lesson_id, position"
    ).fetchall():
        b = {"id": r["id"], "name": r["name"], "note": r["note"], "code": r["code"],
             "why": {"q": r["why_q"], "opts": [], "ok": r["why_ok"], "exp": r["why_exp"]}}
        by_id[r["lesson_id"]]["blocks"].append(b)
        by_block[(r["lesson_id"], r["id"])] = b
    for r in con.execute(
        "SELECT lesson_id, block_id, text FROM block_options ORDER BY lesson_id, block_id, position"
    ).fetchall():
        by_block[(r["lesson_id"], r["block_id"])]["why"]["opts"].append(r["text"])

    packs = [
        {"id": r["id"], "title": r["title"], "desc": r["descr"], "items": []}
        for r in con.execute("SELECT id, title, descr FROM packs ORDER BY position").fetchall()
    ]
    by_pack = {p["id"]: p for p in packs}
    for r in con.execute(
        "SELECT pack_id, name, category, descr, lesson_id FROM pack_items ORDER BY pack_id, position"
    ).fetchall():
        by_pack[r["pack_id"]]["items"].append(
            {"name": r["name"], "category": r["category"], "desc": r["descr"], "lesson": r["lesson_id"]}
        )

    for stale in set(BY_ID) - set(by_id):
        del BY_ID[stale]
    BY_ID.update(by_id)
    LESSONS[:] = lessons
    PACKS[:] = packs

    from . import algos

    algos.load(con)


def ensure(con):
    """Старт приложения: пустую базу заполняем из JSON, затем грузим контент в память."""
    seed_from_json(con)
    from . import algos

    algos.seed(con)
    load(con)


def indent(code, n=4):
    pad = " " * n
    return "\n".join(pad + line if line else line for line in code.split("\n"))


def class_body(L):
    return L["cls"] + "\n" + "\n\n".join(indent(b["code"]) for b in L["blocks"])


def full_code(L):
    return L["imports"] + "\n\n\n" + class_body(L)


def find_block(L, bid):
    for b in L["blocks"]:
        if b["id"] == bid:
            return b
    return None


def slot_target(L, bid):
    return class_body(L) if bid == "whole" else find_block(L, bid)["code"]


def nlines(s):
    return len(s.split("\n"))


def slot_rows(L, bid):
    return nlines(slot_target(L, bid))


def order_ids(L, mode, seed=None):
    """Порядок пропадающих методов: от маленьких к большим или вперемешку."""
    ids = [b["id"] for b in sorted(L["blocks"], key=lambda b: len(b["code"]))]
    if mode == "random":
        random.Random(seed).shuffle(ids)
    return ids


def ready_count(pack):
    return sum(1 for it in pack["items"] if it["lesson"])


def get_pack(pid):
    return next((p for p in PACKS if p["id"] == pid), None)


def pack_for_lesson(lid):
    return next((p for p in PACKS if any(it["lesson"] == lid for it in p["items"])), None)


def valid_key(key):
    """Ключ повторения 'урок::метод' указывает на существующий блок."""
    lid, _, bid = key.partition("::")
    L = BY_ID.get(lid)
    return bool(L and find_block(L, bid))
