/* Плавающая панель ИИ-наставника. Контекст (урок, метод, попытка) подмешивается автоматически. */
(() => {
  const root = document.getElementById("ai-root");
  if (!root) return;
  const fab = document.getElementById("ai-fab");
  const panel = document.getElementById("ai-panel");
  const msgs = document.getElementById("ai-msgs");
  const input = document.getElementById("ai-input");
  const send = document.getElementById("ai-send");
  const quota = document.getElementById("ai-quota");
  const history = [];
  const sfx = n => { if (window.Sfx) window.Sfx.play(n); };
  let busy = false;

  const FadeAI = (window.FadeAI = { getContext: null, open, ask });

  function context() {
    return Object.assign({ lesson: root.dataset.lesson }, FadeAI.getContext ? FadeAI.getContext() : {});
  }

  function open(silent) {
    const was = panel.hidden;
    panel.hidden = false;
    fab.hidden = true;
    input.focus();
    if (was && silent !== true) sfx("open");
  }

  function close() {
    if (!panel.hidden) sfx("close");
    panel.hidden = true;
    fab.hidden = false;
  }

  function add(role, text, cls) {
    const el = document.createElement("div");
    el.className = "ai-msg " + role + (cls ? " " + cls : "");
    el.textContent = text;
    msgs.appendChild(el);
    msgs.scrollTop = msgs.scrollHeight;
    return el;
  }

  async function ask(text, extra) {
    text = (text || "").trim();
    if (!text || busy) return;
    open(true);
    busy = true;
    sfx("send");
    send.disabled = true;
    add("user", text);
    const wait = add("bot", "Думаю…", "typing");
    try {
      const body = Object.assign({}, context(), extra || {}, { message: text, history: history.slice(-6) });
      const r = await window.api("/api/ai/chat", body);
      wait.remove();
      add("bot", r.text);
      sfx("recv");
      history.push({ role: "user", content: text }, { role: "assistant", content: r.text });
      if (typeof r.left === "number") quota.textContent = "Осталось запросов сегодня: " + r.left;
    } catch (e) {
      wait.textContent = e.message;
      wait.classList.remove("typing");
      wait.classList.add("err");
      sfx("err");
    } finally {
      busy = false;
      send.disabled = false;
    }
  }

  fab.addEventListener("click", () => open());
  document.getElementById("ai-close").addEventListener("click", close);
  send.addEventListener("click", () => { const t = input.value; input.value = ""; ask(t); });
  input.addEventListener("keydown", e => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send.click(); }
  });
})();
