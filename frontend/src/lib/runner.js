const BOOT_MS = 120000;
const RUN_MS = 15000;

let worker = null;
let booted = false;
let cur = null;
let seq = 0;

const fail = message => ({ status: "error", message, count: 0, stdout: "" });

function finish(result) {
  if (!cur) return;
  clearTimeout(cur.timer);
  const c = cur;
  cur = null;
  c.resolve(result);
}

function kill() {
  if (worker) worker.terminate();
  worker = null;
  booted = false;
}

function arm(ms) {
  if (!cur) return;
  clearTimeout(cur.timer);
  const wasBooted = booted;
  cur.timer = setTimeout(() => {
    kill();
    finish(fail(wasBooted
      ? "Время вышло (15 с). Похоже на бесконечный цикл или слишком медленное решение."
      : "Python не загрузился за 2 минуты. Проверь интернет и попробуй ещё раз."));
  }, ms);
}

function spawn() {
  worker = new Worker(new URL("./pyWorker.js", import.meta.url));
  booted = false;
  worker.onmessage = e => {
    const m = e.data;
    if (m.type === "loading") {
      if (cur) cur.onStatus("loading");
    } else if (m.type === "ready") {
      booted = true;
      if (cur) { cur.onStatus("running"); arm(RUN_MS); }
    } else if (m.type === "done" && cur && m.id === cur.id) {
      finish(m.result);
    }
  };
  worker.onerror = () => {
    kill();
    finish(fail("Python-воркер упал. Попробуй ещё раз."));
  };
}

export function warmup() {
  if (worker) return;
  spawn();
  worker.postMessage({ cmd: "warm" });
}

export function runTests(p, onStatus) {
  if (cur) return Promise.resolve(fail("Предыдущий запуск ещё идёт."));
  if (!worker) spawn();
  return new Promise(resolve => {
    cur = { id: ++seq, resolve, onStatus: onStatus || (() => {}), timer: null };
    cur.onStatus(booted ? "running" : "loading");
    arm(booted ? RUN_MS : BOOT_MS);
    worker.postMessage({ cmd: "run", id: cur.id, code: p.code, pre: p.pre, tests: p.tests });
  });
}
