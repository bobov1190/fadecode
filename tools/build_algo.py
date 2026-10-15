"""Собирает пак «Алгоритмы · LeetCode»: проверяет каждое решение случайными тестами и дописывает
fadecode/data/lessons.json и packs.json. Запуск повторяем: старые уроки с теми же id заменяются."""
import bisect
import itertools
import json
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from algo_bs import LESSONS_BS  # noqa: E402
from algo_tp import LESSONS_TP  # noqa: E402

DATA = os.path.join(ROOT, "fadecode", "data")
LESSONS = LESSONS_BS + LESSONS_TP
rnd = random.Random(7)


def indent(code):
    return "\n".join("    " + l if l else l for l in code.split("\n"))


def build(L):
    ns = {}
    src = L["imports"] + "\n\n\n" + L["cls"] + "\n" + "\n\n".join(indent(b["code"]) for b in L["blocks"])
    exec(compile(src, L["id"], "exec"), ns)
    return ns, ns[L["cls"].split()[1].rstrip(":")]()


def t_bs_template(S, ns):
    for _ in range(400):
        a = sorted(rnd.randint(-8, 8) for _ in range(rnd.randint(0, 12)))
        x = rnd.randint(-9, 9)
        assert S.lower_bound(a, x) == bisect.bisect_left(a, x)
        assert S.upper_bound(a, x) == bisect.bisect_right(a, x)
        u = sorted(set(a))
        got = S.search(u, x)
        assert got == (u.index(x) if x in u else -1)


def t_bs_range(S, ns):
    for _ in range(400):
        a = sorted(rnd.randint(0, 6) for _ in range(rnd.randint(0, 12)))
        x = rnd.randint(-1, 7)
        exp = [a.index(x), len(a) - 1 - a[::-1].index(x)] if x in a else [-1, -1]
        assert S.searchRange(a, x) == exp, (a, x)


def t_bs_koko(S, ns):
    for _ in range(300):
        p = [rnd.randint(1, 30) for _ in range(rnd.randint(1, 8))]
        h = rnd.randint(len(p), len(p) + 40)
        k = next(k for k in range(1, max(p) + 1) if sum((x + k - 1) // k for x in p) <= h)
        assert S.minEatingSpeed(p, h) == k, (p, h)


def t_bs_rotated(S, ns):
    for _ in range(400):
        n = rnd.randint(1, 10)
        a = sorted(rnd.sample(range(-20, 20), n))
        r = rnd.randint(0, n - 1)
        a = a[r:] + a[:r]
        assert a[S.find_min_index(a)] == min(a)
        x = rnd.randint(-21, 20)
        assert S.search(a, x) == (a.index(x) if x in a else -1), (a, x)


def t_bs_matrix(S, ns):
    for _ in range(300):
        r, c = rnd.randint(1, 5), rnd.randint(1, 5)
        flat = sorted(rnd.sample(range(-30, 30), r * c))
        m = [flat[i * c:(i + 1) * c] for i in range(r)]
        x = rnd.randint(-31, 30)
        assert S.searchMatrix(m, x) == (x in flat), (m, x)


def t_tp_template(S, ns):
    for _ in range(400):
        s = "".join(rnd.choice("aAb c,") for _ in range(rnd.randint(0, 9)))
        t = [ch.lower() for ch in s if ch.isalnum()]
        assert S.is_palindrome(s) == (t == t[::-1]), s
        a = sorted(rnd.randint(-5, 9) for _ in range(rnd.randint(2, 8)))
        x = rnd.randint(-8, 16)
        r = S.two_sum_sorted(a, x)
        has = any(a[i] + a[j] == x for i in range(len(a)) for j in range(i + 1, len(a)))
        if has:
            assert len(r) == 2 and r[0] < r[1] and a[r[0] - 1] + a[r[1] - 1] == x, (a, x, r)
        else:
            assert r == []
        b = sorted(rnd.randint(0, 5) for _ in range(rnd.randint(0, 10)))
        exp = sorted(set(b))
        k = S.remove_duplicates(b)
        assert k == len(exp) and b[:k] == exp, (b, k)


def t_tp_3sum(S, ns):
    for _ in range(300):
        a = [rnd.randint(-5, 5) for _ in range(rnd.randint(0, 10))]
        exp = {tuple(sorted(c)) for c in itertools.combinations(a, 3) if sum(c) == 0}
        got = S.threeSum(list(a))
        assert len(got) == len(exp) and {tuple(sorted(g)) for g in got} == exp, (a, got)


def t_tp_water(S, ns):
    for _ in range(300):
        h = [rnd.randint(0, 12) for _ in range(rnd.randint(2, 10))]
        exp = max(min(h[i], h[j]) * (j - i) for i in range(len(h)) for j in range(i + 1, len(h)))
        assert S.maxArea(h) == exp, h
        assert S.area(h, 0, len(h) - 1) == min(h[0], h[-1]) * (len(h) - 1)


def t_tp_trap(S, ns):
    for _ in range(300):
        h = [rnd.randint(0, 6) for _ in range(rnd.randint(0, 10))]
        exp = sum(max(0, min(max(h[:i + 1]), max(h[i:])) - h[i]) for i in range(len(h)))
        assert S.trap(h) == exp, h
        assert S.trap_prefix(h) == exp, h


def t_tp_cycle(S, ns):
    Node = ns["ListNode"]
    for _ in range(300):
        n = rnd.randint(1, 10)
        nodes = [Node(i) for i in range(n)]
        for i in range(n - 1):
            nodes[i].next = nodes[i + 1]
        pos = rnd.randint(-1, n - 1)
        if pos >= 0:
            nodes[-1].next = nodes[pos]
        head = nodes[0]
        mp = S.meeting_point(head)
        got = S.detectCycle(head)
        if pos < 0:
            assert mp is None and got is None
        else:
            assert got is nodes[pos], (n, pos)
            assert mp in nodes[pos:], (n, pos)
    assert S.detectCycle(None) is None


TESTS = {
    "bs_template": t_bs_template, "bs_range": t_bs_range, "bs_koko": t_bs_koko, "bs_rotated": t_bs_rotated,
    "bs_matrix": t_bs_matrix, "tp_template": t_tp_template, "tp_3sum": t_tp_3sum, "tp_water": t_tp_water,
    "tp_trap": t_tp_trap, "tp_cycle": t_tp_cycle,
}

ITEMS = [
    ("Бинарный поиск: шаблоны", "бинарный поиск", "Классический поиск, lower_bound и upper_bound.", "bs_template"),
    ("Первая и последняя позиции", "бинарный поиск", "LeetCode 34: две границы одним помощником.", "bs_range"),
    ("Кока и бананы", "бинарный поиск", "LeetCode 875: бинарный поиск по ответу.", "bs_koko"),
    ("Поиск в повёрнутом массиве", "бинарный поиск", "LeetCode 33: найти сдвиг, потом искать.", "bs_rotated"),
    ("Поиск в матрице", "бинарный поиск", "LeetCode 74: матрица как один длинный массив.", "bs_matrix"),
    ("Два указателя: шаблоны", "два указателя", "LeetCode 125, 167, 26: с краёв и «быстрый-медленный».", "tp_template"),
    ("Три числа с нулевой суммой", "два указателя", "LeetCode 15: сортировка, фиксируем первое, два указателя.", "tp_3sum"),
    ("Контейнер с водой", "два указателя", "LeetCode 11: двигаем более низкую стенку.", "tp_water"),
    ("Дождевая вода", "два указателя", "LeetCode 42: префиксы и два указателя за O(1) памяти.", "tp_trap"),
    ("Начало цикла в списке", "два указателя", "LeetCode 142: быстрый и медленный указатели.", "tp_cycle"),
]


def dump(path, obj, esc):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=esc, indent=1)
        f.write("\n")


def main():
    for L in LESSONS:
        ns, S = build(L)
        TESTS[L["id"]](S, ns)
        print("ok", L["id"])
    if "--check" in sys.argv:
        return
    lp, pp = os.path.join(DATA, "lessons.json"), os.path.join(DATA, "packs.json")
    raw = open(lp, encoding="utf-8").read()
    esc = "\\u04" in raw
    ids = {L["id"] for L in LESSONS}
    lessons = [l for l in json.loads(raw) if l["id"] not in ids] + LESSONS
    packs = [p for p in json.load(open(pp, encoding="utf-8")) if p["id"] != "algo"]
    packs.append({
        "id": "algo",
        "title": "Алгоритмы · LeetCode",
        "desc": "Бинарный поиск и два указателя: по пять задач с LeetCode. Решение разбито на шаблон и вспомогательные методы, которые пропадают по раундам.",
        "items": [{"name": n, "category": c, "desc": d, "lesson": l} for n, c, d, l in ITEMS],
    })
    dump(lp, lessons, esc)
    dump(pp, packs, esc)
    print("written:", len(lessons), "lessons,", len(packs), "packs")


main()
