/* Подсветка Python и сравнение кода. Порт fadecode/static/js/core.js в ES-модуль. */
const KW = new Set(["False", "None", "True", "and", "as", "assert", "break", "class", "continue", "def", "del", "elif", "else", "except", "finally", "for", "from", "global", "if", "import", "in", "is", "lambda", "nonlocal", "not", "or", "pass", "raise", "return", "try", "while", "with", "yield"]);
const PROTECTED = new Set([...KW, "self", "np", "range", "len", "print", "sum", "min", "max", "abs", "float", "int", "list", "zip", "enumerate", "sorted", "super", "isinstance",
  "axis", "keepdims", "replace", "shape", "T", "exp", "log", "sqrt", "mean", "argmax", "argmin", "argsort", "bincount", "eye", "maximum", "minimum", "zeros", "ones",
  "allclose", "copy", "astype", "array", "random", "default_rng", "choice", "normal", "where", "clip", "reshape"]);

const RE = /(#[^\n]*)|("""[\s\S]*?"""|'''[\s\S]*?'''|"(?:\\.|[^"\\\n])*"|'(?:\\.|[^'\\\n])*')|(\d+(?:\.\d*)?(?:[eE][+-]?\d+)?)|([A-Za-z_]\w*)|(\n)|([ \t\r]+)|(\*\*=?|\/\/=?|[-+*\/%@<>=!]=|->|[\s\S])/y;

function esc(s) {
  return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

function tokenize(src) {
  const out = [];
  let line = 0;
  RE.lastIndex = 0;
  while (RE.lastIndex < src.length) {
    const m = RE.exec(src);
    if (!m) break;
    const v = m[0];
    let t;
    if (m[1]) t = "comment";
    else if (m[2]) t = "str";
    else if (m[3]) t = "num";
    else if (m[4]) t = KW.has(v) ? "kw" : "id";
    else if (m[5]) t = "nl";
    else if (m[6]) t = "ws";
    else t = "op";
    out.push({ t, v, s: m.index, e: m.index + v.length, line });
    if (t === "nl") line++;
  }
  return out;
}

const isSig = t => t.t !== "ws" && t.t !== "nl" && t.t !== "comment";
const sig = toks => toks.filter(isSig);

function tokClass(t, prev, src) {
  if (t.t === "kw") return "k";
  if (t.t === "str") return "s";
  if (t.t === "num") return "n";
  if (t.t === "comment") return "c";
  if (t.t === "op") return "o";
  if (t.t === "id") {
    if (prev && prev.v === "def") return "f";
    if (prev && prev.v === "class") return "cl";
    if (t.v === "self") return "sf";
    if (src[t.e] === "(") return "f";
    if (t.v === "np") return "np";
  }
  return "";
}

function highlight(src, flagged, ins) {
  const toks = tokenize(src);
  let h = "", si = 0, prev = null;
  const gapAt = k => (ins && ins.has(k) ? `<ins class="miss">${esc(ins.get(k))}</ins>` : "");
  for (const t of toks) {
    const cls = tokClass(t, prev, src);
    let inner = esc(t.v);
    if (cls) inner = `<span class="${cls}">${inner}</span>`;
    if (isSig(t)) {
      if (flagged && flagged.has(si)) inner = `<mark>${inner}</mark>`;
      inner = gapAt(si) + inner;
      si++;
      prev = t;
    }
    h += inner;
  }
  return h + gapAt(si);
}

function charClasses(src) {
  const arr = new Array(src.length).fill("");
  let prev = null;
  for (const t of tokenize(src)) {
    const c = tokClass(t, prev, src);
    if (c) for (let i = t.s; i < t.e; i++) arr[i] = c;
    if (isSig(t)) prev = t;
  }
  return arr;
}

function runs(items) {
  let h = "", i = 0;
  while (i < items.length) {
    let j = i;
    while (j < items.length && items[j].c === items[i].c) j++;
    let text = "";
    for (let k = i; k < j; k++) text += items[k].ch;
    h += `<span class="${items[i].c}">${esc(text)}</span>`;
    i = j;
  }
  return h;
}

function ghostHTML(target, typed) {
  const cls = charClasses(target);
  const items = [];
  for (let i = 0; i < typed.length; i++) {
    const ch = typed[i];
    if (i < target.length && ch === target[i]) items.push({ ch, c: "ok " + (cls[i] || "") });
    else items.push({ ch: ch === "\n" ? "↵\n" : ch === " " ? "·" : ch, c: "bad" });
  }
  for (let i = typed.length; i < target.length; i++) {
    const nx = i === typed.length;
    items.push({ ch: nx && target[i] === "\n" ? "↵\n" : target[i], c: (nx ? "gh nx " : "gh ") + (cls[i] || "") });
  }
  return runs(items);
}

function lcsDiff(a, b) {
  const n = a.length, m = b.length, w = m + 1;
  const dp = new Uint16Array((n + 1) * w);
  for (let i = n - 1; i >= 0; i--) {
    for (let j = m - 1; j >= 0; j--) {
      dp[i * w + j] = a[i] === b[j] ? dp[(i + 1) * w + j + 1] + 1 : Math.max(dp[(i + 1) * w + j], dp[i * w + j + 1]);
    }
  }
  const missed = new Set(), extra = new Set(), gaps = new Map();
  const gap = (j, i) => { if (!gaps.has(j)) gaps.set(j, []); gaps.get(j).push(i); };
  let i = 0, j = 0;
  while (i < n && j < m) {
    if (a[i] === b[j]) { i++; j++; }
    else if (dp[(i + 1) * w + j] >= dp[i * w + j + 1]) { missed.add(i); gap(j, i); i++; }
    else extra.add(j++);
  }
  while (i < n) { missed.add(i); gap(m, i); i++; }
  while (j < m) extra.add(j++);
  return { lcs: dp[0], missed, extra, gaps };
}

function renamedOk(T, A) {
  const defLines = new Set();
  T.forEach(t => { if (t.v === "def" || t.v === "class") defLines.add(t.line); });
  const f = new Map(), b = new Map();
  for (let i = 0; i < T.length; i++) {
    const x = T[i], y = A[i];
    if (x.t === "id" && y.t === "id") {
      const prot = PROTECTED.has(x.v) || defLines.has(x.line) || (i > 1 && T[i - 1].v === "." && T[i - 2].v !== "self");
      if (prot) {
        if (x.v !== y.v) return false;
      } else {
        if (PROTECTED.has(y.v)) return false;
        if (f.has(x.v) && f.get(x.v) !== y.v) return false;
        if (b.has(y.v) && b.get(y.v) !== x.v) return false;
      }
      f.set(x.v, y.v);
      b.set(y.v, x.v);
    } else if (x.v !== y.v) return false;
  }
  return true;
}

function compareCode(target, answer) {
  const T = sig(tokenize(target)), A = sig(tokenize(answer));
  if (!A.length) return { status: "empty", score: 0, missed: new Set(T.map((_, i) => i)), extra: new Set() };
  if (T.length === A.length && T.every((x, i) => x.v === A[i].v)) return { status: "perfect", score: 1, missed: new Set(), extra: new Set() };
  if (T.length === A.length && renamedOk(T, A)) return { status: "renamed", score: 1, missed: new Set(), extra: new Set() };
  const d = lcsDiff(T.map(x => x.v), A.map(x => x.v));
  const score = (2 * d.lcs) / (T.length + A.length);
  const status = score >= 0.85 ? "close" : "wrong";
  const ins = new Map();
  d.gaps.forEach((idx, j) => {
    if (status === "close") ins.set(j, target.slice(T[idx[0]].s, T[idx[idx.length - 1]].e).replace(/\s*\n\s*/g, " ↵ "));
    else ins.set(j, "…");
  });
  return { status, score, missed: d.missed, extra: d.extra, ins };
}

const indent = (code, n = 4) => code.split("\n").map(l => (l ? " ".repeat(n) + l : l)).join("\n");

export { esc, tokenize, highlight, charClasses, ghostHTML, compareCode, indent };
