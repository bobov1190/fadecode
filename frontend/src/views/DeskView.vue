<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref } from "vue";
import { api } from "../api";
import { play } from "../lib/sfx";

const tasks = ref([]);
const error = ref("");
const loaded = ref(false);
const busy = ref(false);
const now = ref(Date.now());
let skew = 0;
let tickId = null;

const presets = [15, 30, 45, 60, 90, 120, 180, 240];
const form = reactive({ title: "", est: 30, note: "" });
const editing = ref(null);
const draft = reactive({ title: "", note: "", est: 30 });
const goal = ref(readGoal());

const columns = [
  { key: "idea", name: "Идея" },
  { key: "doing", name: "В работе" },
  { key: "done", name: "Готово" },
];

function readGoal() {
  try { return Math.max(15, parseInt(localStorage.getItem("fc_goal"), 10) || 240); } catch (e) { return 240; }
}
function saveGoal() {
  goal.value = Math.max(15, Math.min(1440, parseInt(goal.value, 10) || 240));
  try { localStorage.setItem("fc_goal", String(goal.value)); } catch (e) { /* приватный режим */ }
}

function apply(r) {
  tasks.value = r.tasks;
  skew = r.now - Date.now();
  now.value = Date.now() + skew;
}

function spent(t) {
  return t.spent_sec + (t.timer_at ? Math.max(0, Math.floor((now.value - t.timer_at) / 1000)) : 0);
}

function human(sec) {
  const m = Math.round(Math.abs(sec) / 60);
  if (m < 60) return m + " мин";
  const h = Math.floor(m / 60);
  return h + " ч" + (m % 60 ? " " + (m % 60) + " мин" : "");
}

function clock(sec) {
  const p = n => String(n).padStart(2, "0");
  return p(Math.floor(sec / 3600)) + ":" + p(Math.floor((sec % 3600) / 60)) + ":" + p(sec % 60);
}

const byCol = key => {
  const list = tasks.value.filter(t => t.status === key);
  return key === "done" ? list.sort((a, b) => b.done_at - a.done_at) : list;
};

const dayStart = computed(() => { const d = new Date(now.value); d.setHours(0, 0, 0, 0); return d.getTime(); });
const done = computed(() => tasks.value.filter(t => t.status === "done"));
const todayMin = computed(() => done.value.filter(t => t.done_at >= dayStart.value).reduce((s, t) => s + t.est_min, 0));
const earnedMin = computed(() => done.value.reduce((s, t) => s + t.est_min, 0));
const bankSec = computed(() => done.value.filter(t => t.spent_sec > 0).reduce((s, t) => s + t.est_min * 60 - t.spent_sec, 0));
const queueMin = computed(() => tasks.value.filter(t => t.status !== "done").reduce((s, t) => s + t.est_min, 0));
const pct = computed(() => Math.min(100, Math.round((todayMin.value / goal.value) * 100)));
const running = computed(() => tasks.value.find(t => t.timer_at));

async function call(fn, sound) {
  if (busy.value) return;
  busy.value = true;
  error.value = "";
  try {
    apply(await fn());
    if (sound) play(sound);
  } catch (e) {
    error.value = e.message;
    play("err");
  } finally {
    busy.value = false;
  }
}

function add() {
  const title = form.title.trim();
  if (!title) { play("warn"); return; }
  call(() => api.post("/desk", { title, est_min: form.est, note: form.note.trim() }), "ok").then(() => {
    if (!error.value) { form.title = ""; form.note = ""; }
  });
}

const move = (t, status) => call(() => api.put("/desk/" + t.id, { status }), status === "done" ? "win" : "next");
const start = t => call(() => api.post("/desk/" + t.id + "/start"), "on");
const stop = t => call(() => api.post("/desk/" + t.id + "/stop"), "off");

function remove(t) {
  if (confirm("Удалить задание «" + t.title + "»?")) call(() => api.del("/desk/" + t.id), "close");
}

function edit(t) {
  editing.value = t.id;
  draft.title = t.title;
  draft.note = t.note;
  draft.est = t.est_min;
}

function saveEdit(t) {
  call(() => api.put("/desk/" + t.id, { title: draft.title, note: draft.note, est_min: draft.est }), "ok").then(() => {
    if (!error.value) editing.value = null;
  });
}

onMounted(async () => {
  try {
    apply(await api.get("/desk"));
  } catch (e) {
    error.value = e.message;
  }
  loaded.value = true;
  tickId = setInterval(() => { now.value = Date.now() + skew; }, 1000);
});
onBeforeUnmount(() => clearInterval(tickId));
</script>

<template>
  <div>
    <div class="eyebrow">Доска</div>
    <h1>Мои задания</h1>
    <p class="muted">Время здесь валюта. У задания есть цена в минутах, таймер считает, сколько ты реально потратил, а разница копится в банке времени.</p>

    <div v-if="error" class="flash bad" role="alert">{{ error }}</div>

    <div class="stats">
      <div class="stat"><b>{{ human(todayMin * 60) }}</b><span>заработано сегодня</span></div>
      <div class="stat"><b :class="bankSec >= 0 ? 'g-good' : 'g-again'">{{ bankSec >= 0 ? "+" : "−" }}{{ human(bankSec) }}</b><span>банк времени</span></div>
      <div class="stat"><b>{{ human(earnedMin * 60) }}</b><span>заработано всего</span></div>
      <div class="stat"><b>{{ human(queueMin * 60) }}</b><span>в очереди</span></div>
    </div>

    <div class="scalebox">
      <div class="scalehead">
        <span>Цель на день</span>
        <label class="goal"><input v-model.number="goal" class="fld sm" type="number" min="15" max="1440" step="15" @change="saveGoal"> мин</label>
      </div>
      <div class="scale" role="progressbar" :aria-valuenow="pct" aria-valuemin="0" aria-valuemax="100"><i :style="{ width: pct + '%' }"></i></div>
      <div class="scalefoot"><span>{{ human(todayMin * 60) }} из {{ human(goal * 60) }}</span><span>{{ pct }}%</span></div>
    </div>

    <div v-if="running" class="runbar">
      <span class="dot"></span>
      <b>{{ running.title }}</b>
      <span class="mono">{{ clock(spent(running)) }}</span>
      <span class="muted">из {{ human(running.est_min * 60) }}</span>
      <button class="btn s" type="button" :disabled="busy" @click="stop(running)">Стоп</button>
    </div>

    <form class="deskform" @submit.prevent="add">
      <input v-model="form.title" class="fld" maxlength="120" placeholder="Новое задание…" aria-label="Название">
      <select v-model.number="form.est" class="fld" aria-label="Цена в минутах">
        <option v-for="m in presets" :key="m" :value="m">{{ human(m * 60) }}</option>
      </select>
      <button class="btn p" type="submit" :disabled="busy">Добавить</button>
      <input v-model="form.note" class="fld wide" maxlength="2000" placeholder="Заметка (необязательно)" aria-label="Заметка">
    </form>

    <p v-if="!loaded" class="muted">Загружаю…</p>
    <div v-else class="deskgrid">
      <section v-for="c in columns" :key="c.key" class="dcol">
        <h3><span>{{ c.name }}</span><span>{{ byCol(c.key).length }}</span></h3>
        <p v-if="!byCol(c.key).length" class="muted dempty">Пока пусто</p>
        <article v-for="t in byCol(c.key)" :key="t.id" class="dcard" :class="{ run: t.timer_at }">
          <template v-if="editing === t.id">
            <input v-model="draft.title" class="fld" maxlength="120" aria-label="Название">
            <input v-model="draft.note" class="fld" maxlength="2000" placeholder="Заметка" aria-label="Заметка">
            <select v-model.number="draft.est" class="fld" aria-label="Цена в минутах">
              <option v-for="m in presets" :key="m" :value="m">{{ human(m * 60) }}</option>
              <option v-if="!presets.includes(draft.est)" :value="draft.est">{{ human(draft.est * 60) }}</option>
            </select>
            <div class="dact">
              <button class="btn s p" type="button" :disabled="busy" @click="saveEdit(t)">Сохранить</button>
              <button class="btn s g" type="button" @click="editing = null">Отмена</button>
            </div>
          </template>
          <template v-else>
            <div class="dhead">
              <b>{{ t.title }}</b>
              <span class="dtools">
                <button class="ibtn" type="button" title="Изменить" aria-label="Изменить" @click="edit(t)">✎</button>
                <button class="ibtn" type="button" title="Удалить" aria-label="Удалить" :disabled="busy" @click="remove(t)">✕</button>
              </span>
            </div>
            <p v-if="t.note" class="dnote">{{ t.note }}</p>
            <div class="dmeta">
              <span>цена {{ human(t.est_min * 60) }}</span>
              <span v-if="spent(t)" :class="{ over: t.status !== 'done' && spent(t) > t.est_min * 60 }">
                {{ t.timer_at ? clock(spent(t)) : "потрачено " + human(spent(t)) }}
              </span>
              <span v-if="t.status === 'done' && t.spent_sec" :class="t.est_min * 60 - t.spent_sec >= 0 ? 'g-good' : 'g-again'">
                {{ t.est_min * 60 - t.spent_sec >= 0 ? "+" : "−" }}{{ human(t.est_min * 60 - t.spent_sec) }}
              </span>
              <span v-else-if="t.status === 'done'">без таймера</span>
            </div>
            <div class="dact">
              <template v-if="t.status !== 'done'">
                <button v-if="t.timer_at" class="btn s" type="button" :disabled="busy" @click="stop(t)">Пауза</button>
                <button v-else class="btn s p" type="button" :disabled="busy" @click="start(t)">Старт</button>
              </template>
              <button v-if="t.status === 'idea'" class="btn s" type="button" :disabled="busy" @click="move(t, 'doing')">В работу →</button>
              <template v-if="t.status === 'doing'">
                <button class="btn s" type="button" :disabled="busy" @click="move(t, 'done')">Готово ✓</button>
                <button class="btn s g" type="button" :disabled="busy" @click="move(t, 'idea')">← Идея</button>
              </template>
              <button v-if="t.status === 'done'" class="btn s g" type="button" :disabled="busy" @click="move(t, 'doing')">← Вернуть</button>
            </div>
          </template>
        </article>
      </section>
    </div>
  </div>
</template>
