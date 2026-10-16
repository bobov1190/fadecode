<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { useRoute } from "vue-router";
import { api } from "../api";
import { clock, dur, num } from "../lib/fmt";
import { play } from "../lib/sfx";
import { useAssign } from "../stores/assign";

const route = useRoute();
const assign = useAssign();
const data = ref(null);
const error = ref("");
const name = ref("");
const busy = ref(false);
const now = ref(Date.now());
let offset = 0;
let iv = null;
let reloading = false;

const A = computed(() => data.value && data.value.assignment);
const T = computed(() => data.value && data.value.attempt);
const left = computed(() => (T.value && T.value.status === "running" ? Math.max(0, Math.ceil((T.value.deadline - (now.value + offset)) / 1000)) : 0));

function apply(r) {
  data.value = r;
  offset = r.now - Date.now();
  if (!name.value) name.value = r.name || "";
}

async function load() {
  try {
    apply(await api.get("/assign/" + encodeURIComponent(route.params.aid)));
  } catch (e) {
    error.value = e.message;
  }
}

async function act(path, body) {
  if (busy.value) return;
  busy.value = true;
  error.value = "";
  try {
    apply(await api.post("/assign/" + encodeURIComponent(route.params.aid) + path, body));
    await assign.load();
  } catch (e) {
    error.value = e.message;
    play("err");
  } finally {
    busy.value = false;
  }
}

function start() { play("next"); return act("/start", { name: name.value }); }
function finish() {
  if (!confirm("Завершить задание? Изменить результат потом будет нельзя.")) return;
  return act("/finish");
}

function tick() {
  now.value = Date.now();
  if (T.value && T.value.status === "running" && left.value === 0 && !reloading) {
    reloading = true;
    load().then(() => assign.load()).finally(() => { reloading = false; });
  }
}

onMounted(() => { load(); iv = setInterval(tick, 1000); });
onBeforeUnmount(() => clearInterval(iv));
</script>

<template>
  <div>
    <div v-if="error" class="flash bad" role="alert">{{ error }}</div>
    <p v-if="!data && !error" class="muted">Загружаю…</p>
    <template v-if="data">
      <div class="eyebrow">Задание</div>
      <h1>{{ A.title }}</h1>
      <p v-if="A.note" class="muted" style="white-space:pre-wrap">{{ A.note }}</p>
      <div class="chips">
        <span class="chip">Время: {{ A.minutes }} мин</span>
        <span class="chip">Максимум: {{ A.max_score }} баллов</span>
        <span class="chip">Карточек: {{ A.cards.length }}</span>
      </div>

      <div class="task">
        <div class="eyebrow">Правила</div>
        <p>Таймер идёт с нажатия «Начать» и не останавливается, даже если закрыть страницу. Балл считается сам: он снижается за ошибки при копировании, неверные проверки и подсказки. «Показать ответ» даёт 0 за метод. Попытка одна, так что работай аккуратно.</p>
      </div>

      <template v-if="T.status === 'new'">
        <form class="start" @submit.prevent="start">
          <label>Имя и фамилия (по ним учитель найдёт твой балл)
            <input v-model="name" required maxlength="80" autocomplete="name" placeholder="Например, Иван Петров">
          </label>
          <button class="btn p" type="submit" :disabled="busy || !name.trim()">Начать: {{ A.minutes }} мин</button>
        </form>
      </template>

      <template v-else-if="T.status === 'running'">
        <div class="bigtimer" :class="{ low: left <= 300 }"><span>Осталось</span><b>{{ clock(left) }}</b></div>
        <div class="grid">
          <RouterLink v-for="(c, i) in A.cards" :key="c.id" class="card" :to="{ name: 'lesson', params: { lid: c.id } }">
            <span class="tag">{{ i + 1 }} · {{ c.tag }}</span><h3>{{ c.title }}</h3>
            <div class="meta"><span>{{ c.methods }} методов</span><span>открыть →</span></div>
          </RouterLink>
        </div>
        <div class="actions"><button class="btn" type="button" :disabled="busy" @click="finish">Завершить задание</button></div>
      </template>

      <template v-else>
        <div class="bigscore">
          <span>Твой результат</span>
          <b>{{ num(T.score) }}<small> из {{ A.max_score }}</small></b>
          <em>Потрачено: {{ dur(T.spent_sec) }}</em>
        </div>
        <div v-for="b in T.breakdown" :key="b.id" class="bd">
          <div class="bd-h"><h3>{{ b.title }}</h3><b>{{ num(b.score) }} / {{ num(b.max) }}</b></div>
          <div class="bd-r"><span>Копирование</span>
            <span>{{ b.copy_errors === null ? "пропущено, 0" : "ошибок: " + b.copy_errors }}</span></div>
          <div v-for="s in b.slots" :key="s.id" class="bd-r">
            <span>{{ s.name }}</span>
            <span>{{ s.revealed ? "показал ответ, 0" : !s.solved ? "не решено, 0"
              : (s.wrong ? "неверных проверок: " + s.wrong + " " : "") + (s.hints ? "подсказок: " + s.hints + " " : "") + (s.accepted ? "«почти» " : "")
              + (!s.wrong && !s.hints && !s.accepted ? "чисто" : "") }}</span>
          </div>
        </div>
      </template>
    </template>
  </div>
</template>
