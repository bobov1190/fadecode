(function(){let e=`https://cdn.jsdelivr.net/pyodide/v0.26.4/full/`,t=null,n=null;async function r(){importScripts(e+`pyodide.js`),t=await self.loadPyodide({indexURL:e}),t.runPython(`"""Прелюдия запуска задач. Одна и та же в браузере (Pyodide) и в tools/build_algos.py (CPython).

fc_run(решение, pre, tests, имя_класса) -> JSON-строка {status: ok|fail|error, message, count, stdout}.
Тесты задачи (tests) исполняются в том же пространстве имён, что и решение, и вызывают check(...).
"""
import bisect
import collections
import copy
import functools
import io
import itertools
import json
import math
import random
import sys
from typing import Any, Dict, List, Optional, Set, Tuple

_COUNT = [0]


class Fail(Exception):
    pass


def _short(x, n=200):
    s = repr(x)
    return s if len(s) <= n else s[:n] + "..."


def _line(e):
    tb, line = e.__traceback__, None
    while tb is not None:
        if tb.tb_frame.f_code.co_filename == "<solution>":
            line = tb.tb_lineno
        tb = tb.tb_next
    return line


def _what(e):
    line = _line(e)
    return "%s: %s" % (type(e).__name__, e) + (" (строка %d)" % line if line else "")


def lim(n):
    """Допустимое число обращений к массиву для поиска за O(log n)."""
    return 8 * max(1, n).bit_length() + 8


class Guard(list):
    """Список, который не даёт перебирать себя целиком и считает обращения по индексу."""

    def __init__(self, items=(), limit=10 ** 9):
        super().__init__(items)
        self._limit = limit
        self._n = 0

    def __getitem__(self, i):
        if isinstance(i, slice):
            raise Fail("Срезы массива здесь запрещены: обращайся к элементам по индексу.")
        self._n += 1
        if self._n > self._limit:
            raise Fail("Слишком много обращений к массиву (больше %d): здесь нужен бинарный поиск за O(log n)." % self._limit)
        return list.__getitem__(self, i)

    def _no(self, *a, **k):
        raise Fail("Перебор всего массива запрещён: здесь нужен бинарный поиск за O(log n).")

    __iter__ = __reversed__ = __contains__ = index = count = _no


def check(S, fn, gen, brute, same=None, call=None, n=150, seed=11):
    """Гоняет решение на n случайных входах и сверяет с перебором brute."""
    rnd = random.Random(seed)
    for _ in range(n):
        args = gen(rnd)
        exp = brute(*copy.deepcopy(args))
        mine = copy.deepcopy(args)
        try:
            got = call(S, *mine) if call else getattr(S, fn)(*mine)
        except Fail as e:
            raise Fail("Вход: %s\\n%s" % (_short(args), e))
        except Exception as e:  # noqa: BLE001 - любая ошибка решения должна дойти до ученика
            raise Fail("Вход: %s\\nОшибка: %s" % (_short(args), _what(e)))
        ok = same(got, exp, mine) if same else got == exp
        if not ok:
            raise Fail("Вход: %s\\nОжидалось: %s\\nПолучено: %s" % (_short(args), _short(exp), _short(got)))
        _COUNT[0] += 1
    return n


_BASE = {k: v for k, v in list(globals().items()) if not k.startswith("__")}


def fc_run(user_code, pre, tests, cls_name):
    out, old = io.StringIO(), sys.stdout
    sys.stdout = out
    res = {"status": "ok", "message": "", "count": 0}
    try:
        ns = dict(_BASE)
        ns["__name__"] = "__fc__"
        _COUNT[0] = 0
        exec(compile(pre or "", "<pre>", "exec"), ns)
        exec(compile(user_code, "<solution>", "exec"), ns)
        if cls_name not in ns:
            raise Fail("Не найден класс %s: оставь его имя как в заготовке." % cls_name)
        ns["S"] = ns[cls_name]()
        exec(compile(tests, "<tests>", "exec"), ns)
        res["count"] = _COUNT[0]
    except Fail as e:
        res.update(status="fail", message=str(e), count=_COUNT[0])
    except SyntaxError as e:
        res.update(status="error", message="Синтаксическая ошибка, строка %s: %s" % (e.lineno, e.msg))
    except Exception as e:  # noqa: BLE001
        res.update(status="error", message=_what(e))
    finally:
        sys.stdout = old
    res["stdout"] = out.getvalue()[:2000]
    return json.dumps(res, ensure_ascii=False)
`)}function i(){return n||=r().catch(e=>{throw n=null,t=null,e}),n}let a=e=>({status:`error`,message:e,count:0,stdout:``});self.onmessage=async e=>{let n=e.data;try{t||self.postMessage({type:`loading`}),await i()}catch(e){self.postMessage({type:`done`,id:n.id,result:a(`Не удалось загрузить Python (нужен интернет): `+(e&&e.message||e))});return}if(self.postMessage({type:`ready`}),n.cmd!==`run`)return;let r;try{let e=t.globals.get(`fc_run`);try{r=JSON.parse(e(n.code,n.pre,n.tests,`Solution`))}finally{e.destroy()}}catch(e){r=a(String(e&&e.message||e))}self.postMessage({type:`done`,id:n.id,result:r})}})();