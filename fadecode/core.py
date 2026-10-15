"""Токенизатор Python-кода, подсветка и сравнение ответа с эталоном.

Порт static/js/core.js: на сервере живёт «истина» (проверка), в браузере
остаётся только то, что нужно для набора поверх призрака.
"""
import re
from collections import namedtuple

from markupsafe import Markup, escape

KW = {
    "False", "None", "True", "and", "as", "assert", "break", "class", "continue", "def", "del", "elif",
    "else", "except", "finally", "for", "from", "global", "if", "import", "in", "is", "lambda", "nonlocal",
    "not", "or", "pass", "raise", "return", "try", "while", "with", "yield",
}
PROTECTED = KW | {
    "self", "np", "range", "len", "print", "sum", "min", "max", "abs", "float", "int", "list", "zip",
    "enumerate", "sorted", "super", "isinstance", "axis", "keepdims", "replace", "shape", "T", "exp", "log",
    "sqrt", "mean", "argmax", "argmin", "argsort", "bincount", "eye", "maximum", "minimum", "zeros", "ones",
    "allclose", "copy", "astype", "array", "random", "default_rng", "choice", "normal", "where", "clip",
    "reshape",
}

# группы: 1 комментарий, 2 строка, 3 число, 4 имя, 5 перевод строки, 6 пробелы, 7 оператор/символ
_RE = re.compile(
    r"""(#[^\n]*)"""
    r"""|(\"\"\"[\s\S]*?\"\"\"|'''[\s\S]*?'''|"(?:\\.|[^"\\\n])*"|'(?:\\.|[^'\\\n])*')"""
    r"""|(\d+(?:\.\d*)?(?:[eE][+-]?\d+)?)"""
    r"""|([A-Za-z_]\w*)"""
    r"""|(\n)"""
    r"""|([ \t\r]+)"""
    r"""|(\*\*=?|//=?|[-+*/%@<>=!]=|->|[\s\S])"""
)
_KIND = {1: "comment", 2: "str", 3: "num", 4: "id", 5: "nl", 6: "ws", 7: "op"}

Tok = namedtuple("Tok", "t v s e line")


def tokenize(src):
    out = []
    pos, line, n = 0, 0, len(src)
    while pos < n:
        m = _RE.match(src, pos)
        if not m:
            break
        v = m.group(0)
        t = _KIND[m.lastindex]
        if t == "id" and v in KW:
            t = "kw"
        out.append(Tok(t, v, m.start(), m.end(), line))
        if t == "nl":
            line += 1
        pos = m.end()
    return out


def is_sig(t):
    return t.t not in ("ws", "nl", "comment")


def sig(toks):
    return [t for t in toks if is_sig(t)]


def tok_class(t, prev, src):
    if t.t == "kw":
        return "k"
    if t.t == "str":
        return "s"
    if t.t == "num":
        return "n"
    if t.t == "comment":
        return "c"
    if t.t == "op":
        return "o"
    if t.t == "id":
        if prev is not None and prev.v == "def":
            return "f"
        if prev is not None and prev.v == "class":
            return "cl"
        if t.v == "self":
            return "sf"
        if t.e < len(src) and src[t.e] == "(":
            return "f"
        if t.v == "np":
            return "np"
    return ""


def highlight(src, flagged=None, ins=None):
    """HTML с подсветкой. flagged: индексы значимых токенов в <mark>; ins: {индекс: текст} вставки-«дыры»."""
    src = "" if src is None else str(src)
    h = []
    si = 0
    prev = None

    def gap_at(k):
        if ins and k in ins:
            return '<ins class="miss">%s</ins>' % escape(ins[k])
        return ""

    for t in tokenize(src):
        cls = tok_class(t, prev, src)
        inner = str(escape(t.v))
        if cls:
            inner = '<span class="%s">%s</span>' % (cls, inner)
        if is_sig(t):
            if flagged and si in flagged:
                inner = "<mark>%s</mark>" % inner
            inner = gap_at(si) + inner
            si += 1
            prev = t
        h.append(inner)
    h.append(gap_at(si))
    return Markup("".join(h))


def lcs_diff(a, b):
    n, m = len(a), len(b)
    dp = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n - 1, -1, -1):
        ai, row, nxt = a[i], dp[i], dp[i + 1]
        for j in range(m - 1, -1, -1):
            if ai == b[j]:
                row[j] = nxt[j + 1] + 1
            else:
                row[j] = nxt[j] if nxt[j] >= row[j + 1] else row[j + 1]
    missed, extra, gaps = set(), set(), {}

    def gap(j, i):
        gaps.setdefault(j, []).append(i)

    i = j = 0
    while i < n and j < m:
        if a[i] == b[j]:
            i += 1
            j += 1
        elif dp[i + 1][j] >= dp[i][j + 1]:
            missed.add(i)
            gap(j, i)
            i += 1
        else:
            extra.add(j)
            j += 1
    while i < n:
        missed.add(i)
        gap(m, i)
        i += 1
    while j < m:
        extra.add(j)
        j += 1
    return {"lcs": dp[0][0], "missed": missed, "extra": extra, "gaps": gaps}


def renamed_ok(T, A):
    """Одинаковая структура, но другие имена локальных переменных (последовательно)."""
    def_lines = {t.line for t in T if t.v in ("def", "class")}
    fwd, bwd = {}, {}
    for i, (x, y) in enumerate(zip(T, A)):
        if x.t == "id" and y.t == "id":
            prot = (
                x.v in PROTECTED
                or x.line in def_lines
                or (i > 1 and T[i - 1].v == "." and T[i - 2].v != "self")
            )
            if prot:
                if x.v != y.v:
                    return False
            else:
                if y.v in PROTECTED:
                    return False
                if x.v in fwd and fwd[x.v] != y.v:
                    return False
                if y.v in bwd and bwd[y.v] != x.v:
                    return False
            fwd[x.v] = y.v
            bwd[y.v] = x.v
        elif x.v != y.v:
            return False
    return True


def compare_code(target, answer):
    """status: empty | perfect | renamed | close | wrong."""
    T = sig(tokenize(target))
    A = sig(tokenize(answer))
    if not A:
        return {"status": "empty", "score": 0.0, "missed": set(range(len(T))), "extra": set(), "ins": {}}
    if len(T) == len(A) and all(x.v == y.v for x, y in zip(T, A)):
        return {"status": "perfect", "score": 1.0, "missed": set(), "extra": set(), "ins": {}}
    if len(T) == len(A) and renamed_ok(T, A):
        return {"status": "renamed", "score": 1.0, "missed": set(), "extra": set(), "ins": {}}
    d = lcs_diff([x.v for x in T], [x.v for x in A])
    score = 2 * d["lcs"] / (len(T) + len(A))
    status = "close" if score >= 0.85 else "wrong"
    ins = {}
    for j, idx in d["gaps"].items():
        if status == "close":
            piece = target[T[idx[0]].s:T[idx[-1]].e]
            ins[j] = re.sub(r"\s*\n\s*", " ↵ ", piece)
        else:
            ins[j] = "…"
    return {"status": status, "score": score, "missed": d["missed"], "extra": d["extra"], "ins": ins}
