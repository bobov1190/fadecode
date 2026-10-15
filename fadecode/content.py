"""Содержимое: уроки и пакеты (data/*.json) и помощники для сборки кода."""
import json
import os
import random

_DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")


def _load(name):
    with open(os.path.join(_DATA, name), encoding="utf-8") as f:
        return json.load(f)


LESSONS = _load("lessons.json")
PACKS = _load("packs.json")
BY_ID = {l["id"]: l for l in LESSONS}

for _p in PACKS:
    for _it in _p["items"]:
        if _it["lesson"] and _it["lesson"] not in BY_ID:
            raise RuntimeError("в пакете %s ссылка на несуществующий урок %s" % (_p["id"], _it["lesson"]))


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
    """Порядок исчезновения методов: от маленького к большому или случайный."""
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
    """Ключ повторения 'урок::метод' ссылается на существующий метод?"""
    lid, _, bid = key.partition("::")
    L = BY_ID.get(lid)
    return bool(L and find_block(L, bid))
