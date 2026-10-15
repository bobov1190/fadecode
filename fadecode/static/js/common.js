/* Общее: запросы к API с CSRF, подтверждение форм, разбор прогресса ИИ. */
(() => {
  const csrf = () => document.querySelector('meta[name="csrf-token"]').content;

  window.api = async function (path, body) {
    let res;
    try {
      res = await fetch(path, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-CSRF-Token": csrf() },
        body: JSON.stringify(body || {}),
      });
    } catch (e) {
      if (window.Sfx) window.Sfx.play("err");
      throw new Error("Нет связи с сервером.");
    }
    if (res.status === 401) { location.href = "/login"; throw new Error("Нужно войти."); }
    let data = null;
    try { data = await res.json(); } catch (e) { /* пустой ответ */ }
    if (!res.ok) {
      const err = new Error((data && data.error) || "Ошибка сервера (" + res.status + ").");
      err.status = res.status;
      if (window.Sfx) window.Sfx.play("err");
      throw err;
    }
    return data;
  };

  document.addEventListener("submit", e => {
    const msg = e.target.dataset && e.target.dataset.confirm;
    if (msg && !confirm(msg)) e.preventDefault();
  });

  const advBtn = document.getElementById("advice-btn");
  if (advBtn) {
    const out = document.getElementById("advice-out");
    advBtn.addEventListener("click", async () => {
      advBtn.disabled = true;
      out.hidden = false;
      out.className = "advice muted";
      out.textContent = "Думаю…";
      try {
        const r = await window.api("/api/ai/advice", {});
        out.className = "advice";
        out.textContent = r.text;
      } catch (e) {
        out.className = "advice err";
        out.textContent = e.message;
      } finally {
        advBtn.disabled = false;
      }
    });
  }
})();
