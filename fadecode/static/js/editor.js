/* Редактор кода: призрачный режим (копирование) и свободный режим (вспоминание). */
(() => {
  const C = window.Core;

  function mount(el, o) {
    const pre = document.createElement("pre");
    pre.className = "ed-pre";
    pre.setAttribute("aria-hidden", "true");
    const ta = document.createElement("textarea");
    ta.spellcheck = false;
    ta.setAttribute("autocomplete", "off");
    ta.setAttribute("autocapitalize", "off");
    ta.setAttribute("aria-label", "Редактор кода");
    el.append(pre, ta);
    el.style.setProperty("--rows", o.rows || 3);

    const draw = () => {
      pre.innerHTML = (o.mode === "ghost" ? C.ghostHTML(o.target, ta.value) : C.highlight(ta.value)) + "\n ";
      if (o.onChange) o.onChange(ta.value);
    };

    if (o.mode === "ghost") {
      const T = o.target;
      let errs = 0;
      let last = "";
      const pin = () => { const n = ta.value.length; ta.setSelectionRange(n, n); };
      const set = v => { ta.value = v; last = v; pin(); draw(); };
      const miss = () => {
        errs++;
        el.classList.remove("shake");
        void el.offsetWidth;
        el.classList.add("shake");
        if (o.onError) o.onError(errs);
      };
      const run = (v, ch) => { let n = v.length; while (T[n] === ch) n++; return n; };
      const putChar = ch => {
        const v = ta.value;
        if (v.length < T.length && T[v.length] === ch) set(v + ch); else miss();
      };
      const putEnter = () => {
        const v = ta.value;
        if (T[v.length] === "\n") { let n = v.length + 1; while (T[n] === " ") n++; set(T.slice(0, n)); } else miss();
      };
      const putTab = () => {
        const v = ta.value;
        if (T[v.length] === " ") set(T.slice(0, run(v, " "))); else miss();
      };
      ta.addEventListener("beforeinput", e => {
        e.preventDefault();
        const t = e.inputType;
        if (t === "insertText" && e.data) { for (const ch of e.data) putChar(ch); }
        else if (t === "insertLineBreak" || t === "insertParagraph") putEnter();
        else if (t === "deleteContentBackward") set(ta.value.slice(0, -1));
        else if (t === "deleteWordBackward") set(ta.value.replace(/\s*\S*$/, ""));
      });
      ta.addEventListener("input", () => {
        const v = ta.value;
        if (T.startsWith(v)) { last = v; draw(); }
        else { ta.value = last; pin(); miss(); draw(); }
      });
      ta.addEventListener("keydown", e => { if (e.key === "Tab") { e.preventDefault(); putTab(); } });
      ["click", "focus", "keyup", "select"].forEach(ev => ta.addEventListener(ev, pin));
      draw();
      return { get: () => ta.value, focus: () => ta.focus(), lock: () => { ta.disabled = true; }, errors: () => errs };
    }

    const ins = t => { ta.setRangeText(t, ta.selectionStart, ta.selectionEnd, "end"); draw(); };
    ta.addEventListener("input", draw);
    ta.addEventListener("keydown", e => {
      if (e.key === "Tab") { e.preventDefault(); ins("    "); }
      else if (e.key === "Enter") {
        e.preventDefault();
        if (e.ctrlKey || e.metaKey) { if (o.onSubmit) o.onSubmit(); return; }
        const cur = ta.value.slice(0, ta.selectionStart).split("\n").pop();
        let ind = cur.match(/^ */)[0];
        if (/:\s*$/.test(cur)) ind += "    ";
        ins("\n" + ind);
      }
    });
    draw();
    return { get: () => ta.value, focus: () => ta.focus(), lock: () => { ta.disabled = true; } };
  }

  window.Editor = { mount };
})();
