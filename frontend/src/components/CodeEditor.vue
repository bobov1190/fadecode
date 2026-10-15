<script setup>
/* Редактор кода: призрачный режим (копирование) и свободный режим (вспоминание). Порт static/js/editor.js. */
import { onMounted, ref } from "vue";
import { ghostHTML, highlight } from "../lib/core";
import { play } from "../lib/sfx";

const props = defineProps({
  mode: { type: String, default: "free" },
  target: { type: String, default: "" },
  rows: { type: Number, default: 3 },
  initial: { type: String, default: "" },
});
const emit = defineEmits(["change", "error", "submit"]);

const el = ref(null);
const ta = ref(null);
const html = ref("");
const locked = ref(false);
let errs = 0;
let last = "";

const ghost = props.mode === "ghost";
const T = props.target;

function draw() {
  html.value = (ghost ? ghostHTML(T, ta.value.value) : highlight(ta.value.value)) + "\n ";
  emit("change", ta.value.value);
}

// ---------- призрак ----------
const pin = () => { if (ghost) { const n = ta.value.value.length; ta.value.setSelectionRange(n, n); } };
function set(v) { ta.value.value = v; last = v; pin(); draw(); }
function miss() {
  errs++;
  play("miss");
  const e = el.value;
  e.classList.remove("shake");
  void e.offsetWidth;
  e.classList.add("shake");
  emit("error", errs);
}
const run = (v, ch) => { let n = v.length; while (T[n] === ch) n++; return n; };
function putChar(ch) {
  const v = ta.value.value;
  if (v.length < T.length && T[v.length] === ch) { set(v + ch); play("key"); } else miss();
}
function putEnter() {
  const v = ta.value.value;
  if (T[v.length] === "\n") { let n = v.length + 1; while (T[n] === " ") n++; set(T.slice(0, n)); play("key"); } else miss();
}
function putTab() {
  const v = ta.value.value;
  if (T[v.length] === " ") { set(T.slice(0, run(v, " "))); play("key"); } else miss();
}

function onBeforeInput(e) {
  if (!ghost) return;
  e.preventDefault();
  const t = e.inputType;
  if (t === "insertText" && e.data) { for (const ch of e.data) putChar(ch); }
  else if (t === "insertLineBreak" || t === "insertParagraph") putEnter();
  else if (t === "deleteContentBackward") set(ta.value.value.slice(0, -1));
  else if (t === "deleteWordBackward") set(ta.value.value.replace(/\s*\S*$/, ""));
}

function onInput() {
  if (!ghost) { draw(); return; }
  const v = ta.value.value;
  if (T.startsWith(v)) { last = v; draw(); }
  else { ta.value.value = last; pin(); miss(); draw(); }
}

// ---------- свободный режим ----------
function ins(t) {
  const x = ta.value;
  x.setRangeText(t, x.selectionStart, x.selectionEnd, "end");
  draw();
}

function onKeydown(e) {
  if (ghost) {
    if (e.key === "Tab") { e.preventDefault(); putTab(); }
    return;
  }
  if (e.key === "Tab") { e.preventDefault(); ins("    "); }
  else if (e.key === "Enter") {
    e.preventDefault();
    if (e.ctrlKey || e.metaKey) { emit("submit"); return; }
    const x = ta.value;
    const cur = x.value.slice(0, x.selectionStart).split("\n").pop();
    let ind = cur.match(/^ */)[0];
    if (/:\s*$/.test(cur)) ind += "    ";
    ins("\n" + ind);
  }
}

onMounted(() => {
  if (props.initial) ta.value.value = props.initial;
  draw();
});

defineExpose({
  get: () => ta.value.value,
  focus: () => ta.value.focus(),
  lock: () => { locked.value = true; },
  set: v => { ta.value.value = v; draw(); },
  errors: () => errs,
});
</script>

<template>
  <div ref="el" class="ed" :style="{ '--rows': rows }">
    <pre class="ed-pre" aria-hidden="true" v-html="html"></pre>
    <textarea ref="ta" spellcheck="false" autocomplete="off" autocapitalize="off" aria-label="Редактор кода"
              :disabled="locked"
              @beforeinput="onBeforeInput" @input="onInput" @keydown="onKeydown"
              @click="pin" @focus="pin" @keyup="pin" @select="pin"></textarea>
  </div>
</template>
