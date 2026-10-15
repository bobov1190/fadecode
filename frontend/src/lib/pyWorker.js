import prelude from "./prelude.py?raw";

const CDN = "https://cdn.jsdelivr.net/pyodide/v0.26.4/full/";
let py = null;
let booting = null;

async function boot() {
  importScripts(CDN + "pyodide.js");
  py = await self.loadPyodide({ indexURL: CDN });
  py.runPython(prelude);
}

function ensure() {
  if (!booting) booting = boot().catch(e => { booting = null; py = null; throw e; });
  return booting;
}

const bad = message => ({ status: "error", message, count: 0, stdout: "" });

self.onmessage = async e => {
  const m = e.data;
  try {
    if (!py) self.postMessage({ type: "loading" });
    await ensure();
  } catch (err) {
    self.postMessage({ type: "done", id: m.id, result: bad("Не удалось загрузить Python (нужен интернет): " + ((err && err.message) || err)) });
    return;
  }
  self.postMessage({ type: "ready" });
  if (m.cmd !== "run") return;
  let result;
  try {
    const fn = py.globals.get("fc_run");
    try { result = JSON.parse(fn(m.code, m.pre, m.tests, "Solution")); } finally { fn.destroy(); }
  } catch (err) {
    result = bad(String((err && err.message) || err));
  }
  self.postMessage({ type: "done", id: m.id, result });
};
