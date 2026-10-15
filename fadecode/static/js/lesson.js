/* Этапы урока: копирование поверх призрака, вспоминание и повторение. Проверку делает сервер. */
(() => {
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const { api, Editor } = window;

  // ---------- копирование ----------
  const copyRoot = $("#copy-root");
  if (copyRoot) {
    const lesson = copyRoot.dataset.lesson, next = copyRoot.dataset.next;
    const target = JSON.parse($("#copy-target").textContent);
    let bad = 0;
    const show = v => {
      const pct = Math.round((v.length / target.length) * 100);
      $("#pbar").style.width = pct + "%";
      $("#pinfo").textContent = pct + "% · ошибок: " + bad;
    };
    const ed = Editor.mount($("#edc"), {
      mode: "ghost", target, rows: target.split("\n").length,
      onError: n => { bad = n; show(ed.get()); },
      onChange: v => {
        show(v);
        $("#copy-next").disabled = v.replace(/\s+$/, "") !== target;
      },
    });
    ed.focus();
    $("#copy-next").addEventListener("click", async () => {
      try { await api("/api/copy_done", { lesson, errors: bad }); } catch (e) { /* журнал не критичен */ }
      location.href = next;
    });
  }

  // ---------- вспоминание и повторение ----------
  const listing = $("#listing");
  if (!listing) return;
  const lesson = listing.dataset.lesson, mode = listing.dataset.mode;
  const slots = {};
  let focusBlock = null;

  $$(".slot", listing).forEach((el, i) => {
    const id = el.dataset.block;
    const ed = Editor.mount($(".ed", el), { mode: "free", rows: +el.dataset.rows, onSubmit: () => check(id) });
    slots[id] = { el, ed, attempts: 0, hints: 0, resolved: false, busy: false, t0: Date.now() };
    el.addEventListener("focusin", () => { focusBlock = id; });
    if (i === 0) { ed.focus(); focusBlock = id; }
  });

  if (window.FadeAI) {
    window.FadeAI.getContext = () => {
      const s = focusBlock && slots[focusBlock];
      return {
        block: focusBlock || "",
        attempt: s ? s.ed.get() : "",
        missing: Object.keys(slots).filter(k => k !== "whole"),
      };
    };
  }

  const errHtml = e => '<div class="res bad">' + String(e.message).replace(/</g, "&lt;") + "</div>";
  const payload = (id, extra) => {
    const s = slots[id];
    return Object.assign({ lesson, block: id, mode, value: s.ed.get(), attempts: s.attempts, hints: s.hints, ms: Date.now() - s.t0 }, extra || {});
  };

  function updateNext() {
    const all = Object.values(slots).every(s => s.resolved);
    const btn = $("#next-round") || $("#review-next");
    if (btn) btn.disabled = !all;
  }

  function finish(id, r) {
    const s = slots[id];
    s.resolved = true;
    s.el.classList.add(r.failed ? "fail" : "good");
    s.ed.lock();
    $$(".slot-actions button", s.el).forEach(b => { b.disabled = true; });
    $(".out", s.el).innerHTML = r.html + (r.why_html || "");
    updateNext();
  }

  async function check(id) {
    const s = slots[id];
    if (!s || s.resolved || s.busy) return;
    const out = $(".out", s.el);
    if (!s.ed.get().trim()) {
      out.innerHTML = '<div class="res mid">Поле пустое: напиши хоть что-то или возьми подсказку.</div>';
      return;
    }
    s.attempts++;
    s.busy = true;
    try {
      const r = await api("/api/check", payload(id));
      if (r.resolved) finish(id, r); else out.innerHTML = r.html;
    } catch (e) {
      s.attempts--;
      out.innerHTML = errHtml(e);
    } finally {
      s.busy = false;
    }
  }

  async function hint(id) {
    const s = slots[id];
    if (!s || s.resolved || s.busy) return;
    s.busy = true;
    try {
      const r = await api("/api/hint", { lesson, block: id, n: s.hints + 1 });
      s.hints = r.n;
      $(".hint", s.el).innerHTML = r.html;
      $(".hc", s.el).textContent = "подсказок: " + r.n;
    } catch (e) {
      $(".out", s.el).innerHTML = errHtml(e);
    } finally {
      s.busy = false;
    }
  }

  async function resolveVia(id, path) {
    const s = slots[id];
    if (!s || s.resolved || s.busy) return;
    s.busy = true;
    try {
      finish(id, await api(path, payload(id)));
    } catch (e) {
      $(".out", s.el).innerHTML = errHtml(e);
    } finally {
      s.busy = false;
    }
  }

  document.addEventListener("click", async e => {
    const opt = e.target.closest(".opt");
    if (opt) {
      const why = opt.closest(".why");
      $$(".opt", why).forEach(o => { o.disabled = true; });
      try {
        const r = await api("/api/why", { lesson, block: why.dataset.block, i: +opt.dataset.i });
        $$(".opt", why).forEach(o => { if (+o.dataset.i === r.ok) o.classList.add("right"); });
        if (!r.right) opt.classList.add("wrong");
        $(".expl", why).textContent = r.exp;
      } catch (err) {
        $(".expl", why).textContent = err.message;
      }
      return;
    }
    const next = e.target.closest("#next-round");
    if (next && !next.disabled) {
      if (next.dataset.finish) {
        next.disabled = true;
        try { await api("/api/lesson_done", { lesson }); } catch (err) { /* дойдём до итогов в любом случае */ }
      }
      location.href = next.dataset.next;
      return;
    }
    const btn = e.target.closest("[data-act]");
    const slot = btn && btn.closest(".slot");
    if (!btn || !slot || btn.disabled) return;
    const id = slot.dataset.block, act = btn.dataset.act;
    if (act === "check") check(id);
    else if (act === "hint") hint(id);
    else if (act === "reveal") resolveVia(id, "/api/reveal");
    else if (act === "accept") resolveVia(id, "/api/accept");
    else if (act === "ai-explain" && window.FadeAI) {
      window.FadeAI.ask("Что не так в моей попытке для этого метода? Готовое решение не показывай.", { block: id, attempt: slots[id].ed.get() });
    }
  });
})();
