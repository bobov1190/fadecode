export function clock(sec) {
  sec = Math.max(0, Math.floor(sec));
  const h = Math.floor(sec / 3600), m = Math.floor((sec % 3600) / 60), s = sec % 60;
  const p = n => String(n).padStart(2, "0");
  return (h ? h + ":" + p(m) : String(m)) + ":" + p(s);
}

export function dur(sec) {
  sec = Math.max(0, Math.round(sec));
  const m = Math.floor(sec / 60), s = sec % 60;
  return m + " мин " + String(s).padStart(2, "0") + " с";
}

export function num(n) {
  return Number.isInteger(n) ? String(n) : n.toFixed(1);
}
