/* Звуки интерфейса: синтез через Web Audio, файлов нет. Порт fadecode/static/js/sfx.js в ES-модуль. */
const store = {
  get(k, d) { try { const v = localStorage.getItem(k); return v === null ? d : v; } catch (e) { return d; } },
  set(k, v) { try { localStorage.setItem(k, v); } catch (e) { /* приватный режим */ } },
};

let on = store.get("fc_sound", "1") !== "0";
let vol = parseFloat(store.get("fc_vol", "0.6"));
if (!(vol >= 0 && vol <= 1)) vol = 0.6;

let ctx = null, master = null;
function ac() {
  if (!ctx) {
    const A = window.AudioContext || window.webkitAudioContext;
    if (!A) return null;
    ctx = new A();
    master = ctx.createGain();
    master.gain.value = vol;
    master.connect(ctx.destination);
  }
  if (ctx.state === "suspended") ctx.resume().catch(() => {});
  return ctx;
}

function tone(o) {
  const c = ac();
  if (!c) return;
  const { f = 440, to = null, t = 0, d = 0.1, type = "sine", g = 0.2, a = 0.005 } = o;
  const t0 = c.currentTime + t;
  const osc = c.createOscillator(), env = c.createGain();
  osc.type = type;
  osc.frequency.setValueAtTime(f, t0);
  if (to) osc.frequency.exponentialRampToValueAtTime(to, t0 + d);
  env.gain.setValueAtTime(0.0001, t0);
  env.gain.exponentialRampToValueAtTime(g, t0 + a);
  env.gain.exponentialRampToValueAtTime(0.0001, t0 + d);
  osc.connect(env);
  env.connect(master);
  osc.start(t0);
  osc.stop(t0 + d + 0.03);
}

function noise(o) {
  const c = ac();
  if (!c) return;
  const { t = 0, d = 0.1, g = 0.15, f = 1500, q = 1 } = o;
  const t0 = c.currentTime + t;
  const n = Math.max(1, Math.floor(c.sampleRate * d));
  const buf = c.createBuffer(1, n, c.sampleRate);
  const data = buf.getChannelData(0);
  for (let i = 0; i < n; i++) data[i] = Math.random() * 2 - 1;
  const src = c.createBufferSource();
  src.buffer = buf;
  const flt = c.createBiquadFilter();
  flt.type = "bandpass";
  flt.frequency.value = f;
  flt.Q.value = q;
  const env = c.createGain();
  env.gain.setValueAtTime(g, t0);
  env.gain.exponentialRampToValueAtTime(0.0001, t0 + d);
  src.connect(flt);
  flt.connect(env);
  env.connect(master);
  src.start(t0);
}

const C5 = 523.25, E5 = 659.25, G5 = 783.99, C6 = 1046.5, E6 = 1318.5;
const SOUNDS = {
  click() { tone({ f: 520, to: 340, d: 0.06, type: "square", g: 0.06 }); },
  press() { tone({ f: 440, to: 880, d: 0.09, type: "square", g: 0.07 }); tone({ f: 880, t: 0.07, d: 0.08, type: "square", g: 0.05 }); },
  tab() { tone({ f: 700, to: 920, d: 0.06, type: "triangle", g: 0.09 }); },
  key() { tone({ f: 900 + Math.random() * 250, d: 0.03, type: "triangle", g: 0.05 }); },
  miss() { tone({ f: 160, to: 80, d: 0.14, type: "sawtooth", g: 0.11 }); noise({ d: 0.08, g: 0.07, f: 400 }); },
  err() { tone({ f: 220, to: 110, d: 0.18, type: "sawtooth", g: 0.12 }); tone({ f: 165, to: 82, t: 0.12, d: 0.22, type: "sawtooth", g: 0.12 }); },
  warn() { tone({ f: 440, d: 0.1, type: "square", g: 0.07 }); tone({ f: 370, t: 0.11, d: 0.14, type: "square", g: 0.07 }); },
  ok() { [C5, E5, G5].forEach((f, i) => tone({ f, t: i * 0.07, d: 0.14, type: "square", g: 0.07 })); },
  win() {
    [C5, E5, G5, C6].forEach((f, i) => tone({ f, t: i * 0.1, d: 0.16, type: "square", g: 0.08 }));
    tone({ f: C6, t: 0.4, d: 0.5, type: "triangle", g: 0.12 });
    tone({ f: E6, t: 0.4, d: 0.5, type: "sine", g: 0.08 });
  },
  lose() { [392, 330, 262].forEach((f, i) => tone({ f, t: i * 0.12, d: 0.2, type: "triangle", g: 0.12 })); },
  hint() { tone({ f: 880, d: 0.1, type: "sine", g: 0.12 }); tone({ f: E6, t: 0.09, d: 0.18, type: "sine", g: 0.1 }); },
  next() { tone({ f: 400, to: 900, d: 0.14, type: "square", g: 0.06 }); },
  open() { tone({ f: 350, to: 700, d: 0.12, type: "triangle", g: 0.1 }); },
  close() { tone({ f: 700, to: 350, d: 0.12, type: "triangle", g: 0.1 }); },
  send() { tone({ f: 500, to: 900, d: 0.09, type: "sine", g: 0.1 }); },
  recv() { tone({ f: 700, d: 0.07, type: "sine", g: 0.1 }); tone({ f: 940, t: 0.07, d: 0.1, type: "sine", g: 0.1 }); },
  on() { tone({ f: 600, d: 0.08, type: "square", g: 0.07 }); tone({ f: 900, t: 0.08, d: 0.12, type: "square", g: 0.07 }); },
  off() { tone({ f: 700, to: 300, d: 0.15, type: "square", g: 0.07 }); },
};

let lastKey = 0;
export function play(name, force) {
  if (!on && !force) return;
  if (name === "key") {
    const now = performance.now();
    if (now - lastKey < 30) return;
    lastKey = now;
  }
  try { if (SOUNDS[name]) SOUNDS[name](); } catch (e) { /* звук не критичен */ }
}

export const Sfx = {
  play,
  enabled: () => on,
  setEnabled(v) { on = !!v; store.set("fc_sound", on ? "1" : "0"); },
  volume: () => vol,
  setVolume(v) {
    vol = Math.min(1, Math.max(0, +v || 0));
    store.set("fc_vol", String(vol));
    if (master) master.gain.value = vol;
  },
};


// Первое касание страницы будит AudioContext (браузеры не дают играть звук без жеста).
if (typeof window !== "undefined") {
  ["pointerdown", "keydown"].forEach(ev => addEventListener(ev, () => { ac(); }, { once: true, capture: true }));
}

// Звук при клике по кнопкам, вкладкам и карточкам (один глобальный слушатель).
const CLICKABLE = "button, a.btn, a.tab, a.card, .opt, .crumb, .back, .logo, .linkbtn";
const OWN_SOUND = "#sfx-wrap, #ai-fab, #ai-close, #ai-send";
export function installClickSounds() {
  document.addEventListener("click", e => {
    const t = e.target.closest(CLICKABLE);
    if (!t || t.disabled || t.getAttribute("aria-disabled") === "true" || t.closest(OWN_SOUND)) return;
    play(t.matches("a.tab") ? "tab" : t.matches(".btn.p, .p") ? "press" : "click");
  }, true);
}

