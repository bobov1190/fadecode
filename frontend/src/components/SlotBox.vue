<script setup>
/* Одно поле «вспомни метод»: проверка, подсказки, ответ, вопрос «зачем так». Разметку рисует Vue, проверяет сервер. */
import { computed, onMounted, reactive, ref } from "vue";
import { api } from "../api";
import CodeEditor from "./CodeEditor.vue";
import { highlight } from "../lib/core";
import { play } from "../lib/sfx";

const props = defineProps({
  lesson: { type: String, required: true },
  bid: { type: String, required: true },
  rows: { type: Number, default: 3 },
  label: { type: String, default: "ПРОПАЛ МЕТОД" },
  whole: Boolean,
  mode: { type: String, default: "recall" },
  why: { type: Object, default: null },
  autofocus: Boolean,
});
const emit = defineEmits(["resolved"]);

const ed = ref(null);
const st = reactive({ attempts: 0, hints: 0, resolved: false, failed: false, busy: false, t0: Date.now() });
const hintLines = ref([]);
const res = ref(null); // { kind: "good"|"mid"|"bad", ... }
const opts = ref([]); // варианты «зачем так» с исходными индексами
const pick = reactive({ done: false, chosen: -1, ok: -1, right: false, exp: "" });

const cls = computed(() => ({ whole: props.whole, good: st.resolved && !st.failed, fail: st.resolved && st.failed }));

function payload(extra) {
  return Object.assign({ lesson: props.lesson, block: props.bid, mode: props.mode, value: ed.value.get(),
    attempts: st.attempts, hints: st.hints, ms: Date.now() - st.t0 }, extra || {});
}

function summary(r) {
  const bits = [];
  if (r.extra.length) bits.push("красным отмечено лишнее (" + r.extra.length + ")");
  if (r.missed_count) {
    bits.push(r.status === "close"
      ? "оранжевым вставлено то, чего не хватает (токенов: " + r.missed_count + ")"
      : "оранжевое «…» показывает, где что-то пропущено (токенов: " + r.missed_count + ")");
  }
  if (!bits.length) return "";
  const t = bits.join("; ");
  return t[0].toUpperCase() + t.slice(1) + ".";
}

function shuffleOpts() {
  if (props.whole || !props.why) return;
  const a = props.why.opts.map((text, i) => ({ i, text }));
  for (let k = a.length - 1; k > 0; k--) {
    const j = Math.floor(Math.random() * (k + 1));
    [a[k], a[j]] = [a[j], a[k]];
  }
  opts.value = a;
}

function finish(r, extra) {
  st.resolved = true;
  st.failed = !!r.failed;
  ed.value.lock();
  if (r.how === "ok") {
    const msg = r.status === "renamed" ? "Верно: названия переменных другие, но логика та же."
      : st.hints || st.attempts > 1 ? "Верно (с подсказкой или не с первой попытки)." : "Точно, с первого раза.";
    res.value = { kind: "good", msg };
  } else if (r.how === "accepted") {
    res.value = { kind: "good", msg: "Засчитано как «с трудом»: метод вернётся в повторение раньше." };
  } else {
    res.value = Object.assign({ kind: "bad", reveal: true }, extra);
  }
  play(r.failed ? "lose" : r.grade === "good" ? "win" : "ok");
  shuffleOpts();
  emit("resolved", { id: props.bid, grade: r.grade });
}

function fail(e) {
  res.value = { kind: "bad", msg: e.message };
  play("err");
}

async function check() {
  if (st.resolved || st.busy) return;
  if (!ed.value.get().trim()) {
    res.value = { kind: "mid", msg: "Поле пустое: напиши хоть что-то или возьми подсказку." };
    play("warn");
    return;
  }
  st.attempts++;
  st.busy = true;
  try {
    const value = ed.value.get();
    const r = await api.post("/check", payload());
    if (r.resolved) { finish(r); return; }
    const close = r.status === "close";
    res.value = { kind: close ? "mid" : "bad", close, pct: r.score, summary: summary(r),
      hl: highlight(value, new Set(r.extra), new Map(r.ins)) };
    play(close ? "warn" : "err");
  } catch (e) {
    st.attempts--;
    fail(e);
  } finally {
    st.busy = false;
  }
}

async function hint() {
  if (st.resolved || st.busy) return;
  st.busy = true;
  try {
    const r = await api.post("/hint", { lesson: props.lesson, block: props.bid, n: st.hints + 1 });
    st.hints = r.n;
    hintLines.value = r.lines;
    play("hint");
  } catch (e) {
    fail(e);
  } finally {
    st.busy = false;
  }
}

async function resolveVia(path) {
  if (st.resolved || st.busy) return;
  st.busy = true;
  try {
    const r = await api.post(path, payload());
    finish(r, r.target !== undefined ? { hl: highlight(r.target, new Set(r.missed)) } : null);
  } catch (e) {
    fail(e);
  } finally {
    st.busy = false;
  }
}

async function choose(o) {
  if (pick.done) return;
  pick.done = true;
  pick.chosen = o.i;
  try {
    const r = await api.post("/why", { lesson: props.lesson, block: props.bid, i: o.i });
    pick.ok = r.ok;
    pick.right = r.right;
    pick.exp = r.exp;
    play(r.right ? "ok" : "err");
  } catch (e) {
    pick.exp = e.message;
  }
}

onMounted(() => { if (props.autofocus) ed.value.focus(); });
defineExpose({ focus: () => ed.value.focus(), value: () => ed.value.get() });
</script>

<template>
  <div class="slot" :class="cls">
    <div class="slot-head"><span>{{ whole ? "ВЕСЬ КЛАСС ПО ПАМЯТИ" : label }}</span><span>{{ st.hints ? "подсказок: " + st.hints : "" }}</span></div>
    <CodeEditor ref="ed" mode="free" :rows="rows" @submit="check" />
    <div class="hint"><div v-for="(l, i) in hintLines" :key="i">{{ l }}</div></div>
    <div class="slot-actions">
      <button class="btn p s" type="button" :disabled="st.resolved" @click="check">Проверить<kbd>Ctrl+Enter</kbd></button>
      <button class="btn s" type="button" :disabled="st.resolved" @click="hint">Подсказка</button>
      <button class="btn s g" type="button" :disabled="st.resolved" @click="resolveVia('/reveal')">Показать ответ</button>
    </div>
    <div class="out">
      <div v-if="res" class="res" :class="res.kind">
        <template v-if="res.reveal"><b>Эталон.</b> Оранжевым отмечено, чего не хватило.<pre class="ref" v-html="res.hl"></pre></template>
        <template v-else-if="res.kind === 'good'">✓ {{ res.msg }}</template>
        <template v-else-if="res.msg">{{ res.msg }}</template>
        <template v-else>
          <b>{{ res.close ? "Почти" : "Не совпало" }}</b> · сходство {{ res.pct }}%. {{ res.summary }}
          <pre v-html="res.hl"></pre>
          <div v-if="res.close" class="row">
            <button class="btn s" type="button" @click="resolveVia('/accept')">Мой вариант верный, засчитать</button>
          </div>
        </template>
      </div>
      <div v-if="st.resolved && opts.length" class="why">
        <div class="eyebrow">Зачем так?</div><p>{{ why.q }}</p>
        <div class="opts">
          <button v-for="o in opts" :key="o.i" class="opt" type="button" :disabled="pick.done"
                  :class="{ right: pick.done && o.i === pick.ok, wrong: pick.done && pick.ok >= 0 && !pick.right && o.i === pick.chosen }"
                  @click="choose(o)">{{ o.text }}</button>
        </div>
        <div class="expl">{{ pick.exp }}</div>
      </div>
    </div>
  </div>
</template>
