"""Собирает fadecode/data/algos.json из tools/algo_problems_*.py и проверяет каждую задачу.

Проверка: эталон проходит все тесты (в той же прелюдии, что работает в браузере), а пустая заготовка нет.
Запуск: python tools/build_algos.py [--check]. Повторяем: файл и пак перезаписываются.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from algo_problems_bs import PROBLEMS_BS  # noqa: E402
from algo_problems_tp import PROBLEMS_TP  # noqa: E402

DATA = os.path.join(ROOT, "fadecode", "data")

ALGOS = [
    {
        "id": "bsearch",
        "title": "Бинарный поиск",
        "tag": "алгоритм",
        "desc": "Один шаблон: учишь его наизусть (разбор, копирование, вспоминание), потом решаешь на нём задачи от разминки до hard.",
        "template": "bs_template",
        "variations": ["bs_range", "bs_koko", "bs_rotated", "bs_matrix"],
        "problems": PROBLEMS_BS,
    },
    {
        "id": "twoptr",
        "title": "Два указателя",
        "tag": "алгоритм",
        "desc": "Один шаблон про указатели с краёв и «быстрый-медленный». Выучил, и дальше задачи на списки, строки и массивы.",
        "template": "tp_template",
        "variations": ["tp_3sum", "tp_water", "tp_trap", "tp_cycle"],
        "problems": PROBLEMS_TP,
    },
]

REQUIRED = ("id", "title", "level", "fn", "statement", "examples", "hints", "starter", "reference", "insight",
            "pre", "tests")


def load_runner():
    ns = {}
    path = os.path.join(ROOT, "frontend", "src", "lib", "prelude.py")
    with open(path, encoding="utf-8") as f:
        exec(compile(f.read(), path, "exec"), ns)
    return ns["fc_run"]


def verify():
    run = load_runner()
    seen = set()
    for A in ALGOS:
        for i, P in enumerate(A["problems"]):
            for k in REQUIRED:
                assert k in P, (P.get("id"), "нет поля", k)
            assert P["id"] not in seen, P["id"]
            seen.add(P["id"])
            assert P["level"] in ("easy", "medium", "hard"), P["id"]
            assert len(P["hints"]) == 2 and P["examples"], P["id"]
            good = json.loads(run(P["reference"], P["pre"], P["tests"], "Solution"))
            assert good["status"] == "ok" and good["count"] > 0, (P["id"], good)
            blank = json.loads(run(P["starter"], P["pre"], P["tests"], "Solution"))
            assert blank["status"] != "ok", (P["id"], "заготовка проходит тесты", blank)
            print("ok %-8s %-6s %3d тестов | заготовка: %s" % (P["id"], P["level"], good["count"], blank["status"]))


def main():
    verify()
    if "--check" in sys.argv:
        return
    out = []
    for A in ALGOS:
        a = dict(A, pack="algo")
        a["problems"] = [dict(P, num=P.get("num")) for P in A["problems"]]
        out.append(a)
    with open(os.path.join(DATA, "algos.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
        f.write("\n")
    pp = os.path.join(DATA, "packs.json")
    raw = open(pp, encoding="utf-8").read()
    esc = "\\u04" in raw
    packs = json.loads(raw)
    for p in packs:
        if p["id"] == "algo":
            p["desc"] = "Алгоритмы для собеседований: выучи шаблон, потом решай задачи на нём. Код проверяется тестами прямо в браузере."
            p["items"] = []
    with open(pp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(packs, f, ensure_ascii=esc, indent=1)
        f.write("\n")
    print("written: %d алгоритмов, %d задач" % (len(out), sum(len(a["problems"]) for a in out)))


main()
