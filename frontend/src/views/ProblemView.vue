<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { api } from "../api";
import CodeEditor from "../components/CodeEditor.vue";
import { highlight } from "../lib/core";
import { runTests, warmup } from "../lib/runner";
import { play } from "../lib/sfx";
import { useAi } from "../stores/ai";

const route = useRoute();
const router = useRouter();
const ai = useAi();

const P = ref(null);
const error = ref("");
const ed = ref(null);
const phase = ref("idle");
const res = ref(null);
const sol = ref(null);
const hints = ref([]);
const attempts = ref(0);
const status = ref("new");
const initial = ref("");
const rows = ref(12);
let lastError = "";
let lastSaved = "";
let timer = null;

const levels = { easy: "лёгкая", medium: "средняя", hard: "сложная" };
const solved = computed(() => status.value === "solved");
const busy = computed(() => phase.value !== "idle");
const canHint = computed(() => P.value && hints.value.length < P.value.hints_total);

async function save(v) {
  lastSaved = v;
  try { await api.put("/problems/" + P.value.id + "/draft", { code: v }); } catch (e) { /* черновик не критичен */ }
}

function onChange(v) {
  clearTimeout(timer);
  if (v !== lastSaved) timer = setTimeout(() => save(v), 900);
}

async function showSolution() {
  try {
    const r = await api.post("/problems/" + P.value.id + "/solution");
    sol.value = r;
    status.value = r.status;
  } catch (e) {
    res.value = { status: "error", message: e.message, count: 0, stdout: "" };
  }
}

async function run() {
  if (busy.value || !ed.value) return;
  const code = ed.value.get();
  if (!code.trim()) {
    res.value = { status: "empty" };
    play("warn");
    return;
  }
  res.value = null;
  phase.value = "loading";
  const r = await runTests({ code, pre: P.value.pre, tests: P.value.tests }, s => { phase.value = s; });
  phase.value = "idle";
  lastError = r.status === "ok" ? "" : r.message;
  try {
    const srv = await api.post("/problems/" + P.value.id + "/result", { status: r.status });
    attempts.value = srv.attempts;
    if (srv.solved) status.value = "solved";
  } catch (e) {
    attempts.value += 1;
  }
  res.value = r;
  if (r.status === "ok") {
    play("win");
    await showSolution();
  } else {
    play(r.status === "fail" ? "err" : "warn");
  }
}

async function hint() {
  if (!canHint.value) return;
  try {
    const r = await api.post("/problems/" + P.value.id + "/hint", { n: hints.value.length + 1 });
    hints.value = r.hints;
    play("hint");
  } catch (e) {
    res.value = { status: "error", message: e.message, count: 0, stdout: "" };
  }
}

async function reveal() {
  if (!solved.value && !confirm("Показать решение? Задача пометится как подсмотренная и вернётся к тебе позже.")) return;
  await showSolution();
}

function reset() {
  if (confirm("Вернуть заготовку? Твой код пропадёт.")) ed.value.set(P.value.starter);
}

function askAi() {
  ai.ask("Где у меня ошибка? Готовое решение не показывай.", {});
}

function go(id) {
  play("next");
  router.push({ name: "problem", params: { pid: id } });
}

onMounted(async () => {
  try {
    const p = await api.get("/problems/" + encodeURIComponent(route.params.pid));
    P.value = p;
    hints.value = p.hints;
    attempts.value = p.attempts;
    status.value = p.status;
    initial.value = p.draft || p.starter;
    lastSaved = initial.value;
    rows.value = Math.max(10, initial.value.split("\n").length + 2);
    ai.setProblem(p.id, () => (ed.value ? ed.value.get() : ""), () => lastError);
    warmup();
    api.put("/algos/" + p.algo.id + "/state", { stage: "problem", ref: p.id }).catch(() => {});
    if (p.status === "solved") await showSolution();
  } catch (e) {
    error.value = e.message;
  }
});

onBeforeUnmount(() => {
  clearTimeout(timer);
  if (P.value && ed.value && ed.value.get() !== lastSaved) save(ed.value.get());
  ai.clearProblem();
});
</script>

<template>
  <div>
    <div v-if="error" class="flash bad" role="alert">{{ error }}</div>
    <p v-else-if="!P" class="muted">Загружаю…</p>
    <template v-else>
      <div class="eyebrow"><RouterLink class="crumb" :to="{ name: 'algo', params: { aid: P.algo.id } }">← {{ P.algo.title }}</RouterLink></div>
      <div class="roundhead">
        <div>
          <div class="eyebrow">{{ P.num ? "LeetCode " + P.num : "Задача" }}</div>
          <h1>{{ P.title }}</h1>
        </div>
        <span class="lvl" :class="P.level">{{ levels[P.level] }}</span>
      </div>

      <div class="task"><div class="eyebrow">Условие</div><p class="statement">{{ P.statement }}</p></div>
      <div v-if="P.examples.length" class="examples">
        <div class="eyebrow">Примеры</div>
        <pre v-for="(x, i) in P.examples" :key="i" class="exmp">{{ x }}</pre>
      </div>

      <div class="codebox">
        <CodeEditor ref="ed" mode="free" :initial="initial" :rows="rows" @change="onChange" @submit="run" />
      </div>

      <div v-if="hints.length" class="hintlist">
        <div v-for="(h, i) in hints" :key="i"><b>Подсказка {{ i + 1 }}.</b> {{ h }}</div>
      </div>

      <div class="actions tight">
        <button class="btn p" type="button" :disabled="busy" @click="run">Запустить<kbd class="kb">Ctrl+Enter</kbd></button>
        <button class="btn" type="button" :disabled="!canHint" @click="hint">Подсказка {{ hints.length }}/{{ P.hints_total }}</button>
        <button class="btn" type="button" @click="askAi">ИИ: где ошибка?</button>
        <button class="btn g" type="button" :disabled="busy" @click="reveal">Показать решение</button>
        <button class="btn g" type="button" :disabled="busy" @click="reset">Сбросить код</button>
      </div>
      <div class="progress"><span>попыток: {{ attempts }}</span><span v-if="status === 'solved'" class="g-good">решена</span><span v-else-if="status === 'given_up'" class="g-hard">решение подсмотрено</span></div>

      <div class="out">
        <div v-if="busy" class="res mid">{{ phase === "loading" ? "Загружаю Python в браузер. Это один раз, около 10 МБ, потом из кэша…" : "Гоняю тесты…" }}</div>
        <div v-else-if="res && res.status === 'empty'" class="res mid">Редактор пустой: напиши решение или возьми подсказку.</div>
        <div v-else-if="res" class="res" :class="res.status === 'ok' ? 'good' : res.status === 'fail' ? 'bad' : 'mid'">
          <template v-if="res.status === 'ok'">✓ Все {{ res.count }} тестов пройдены.</template>
          <template v-else-if="res.status === 'fail'"><b>Тест не прошёл</b> (успешных до него: {{ res.count }})<pre class="log">{{ res.message }}</pre></template>
          <template v-else><b>Ошибка выполнения</b><pre class="log">{{ res.message }}</pre></template>
          <pre v-if="res.stdout" class="log">{{ res.stdout }}</pre>
        </div>
      </div>

      <div v-if="sol" class="solution">
        <div class="eyebrow">Разбор</div>
        <div class="task change"><p>{{ sol.insight }}</p></div>
        <p class="muted">Эталон. Сравни с шаблоном: что в нём поменялось, это и есть главный навык.</p>
        <div class="codebox"><pre class="code" v-html="highlight(sol.reference)"></pre></div>
      </div>

      <div v-if="solved || sol" class="actions">
        <button v-if="P.next" class="btn p" type="button" @click="go(P.next)">Следующая задача →</button>
        <RouterLink class="btn" :class="{ p: !P.next }" :to="{ name: 'algo', params: { aid: P.algo.id } }">К алгоритму</RouterLink>
      </div>
    </template>
  </div>
</template>
