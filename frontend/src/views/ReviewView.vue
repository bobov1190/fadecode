<script setup>
/* Повторение: очередь карточек из /review, по одному методу. Оценки пишет сервер (SRS). */
import { computed, onMounted, ref } from "vue";
import { api } from "../api";
import LessonListing from "../components/LessonListing.vue";
import { play } from "../lib/sfx";
import { useAuth } from "../stores/auth";

const auth = useAuth();
const error = ref("");
const loading = ref(true);
const info = ref(null); // ответ /review
const queue = ref([]);
const idx = ref(0);
const finished = ref(0);
const L = ref(null);
const resolved = ref(false);
const busy = ref(false);

const cur = computed(() => queue.value[idx.value] || null);
const inSession = computed(() => queue.value.length > 0 && idx.value < queue.value.length);
const doneAll = computed(() => queue.value.length > 0 && idx.value >= queue.value.length);

function ruDate(iso) {
  const d = new Date(iso);
  if (isNaN(d)) return iso;
  return d.toLocaleString("ru-RU", { day: "numeric", month: "long", hour: "2-digit", minute: "2-digit" });
}

async function openCard() {
  L.value = null;
  resolved.value = false;
  if (!cur.value) return;
  try {
    L.value = await api.get("/lessons/" + encodeURIComponent(cur.value.lesson));
  } catch (e) {
    error.value = e.message;
  }
}

async function load(all) {
  loading.value = true;
  error.value = "";
  try {
    const r = await api.get("/review" + (all ? "?all=1" : ""));
    info.value = r;
    queue.value = r.items;
    idx.value = 0;
    finished.value = 0;
    auth.due = r.due;
    await openCard();
  } catch (e) {
    error.value = e.message;
  } finally {
    loading.value = false;
  }
}

async function next() {
  if (!resolved.value || busy.value) return;
  busy.value = true;
  play("next");
  finished.value++;
  idx.value++;
  await auth.refreshDue();
  await openCard();
  busy.value = false;
}

onMounted(() => load(false));
</script>

<template>
  <div>
    <div v-if="error" class="flash bad" role="alert">{{ error }}</div>
    <p v-else-if="loading" class="muted">Загружаю…</p>

    <template v-else-if="inSession">
      <div class="eyebrow">Повторение · {{ idx + 1 }} из {{ queue.length }}</div>
      <p v-if="!L" class="muted">Загружаю карточку…</p>
      <template v-else>
        <h2>{{ L.title }}</h2>
        <div class="task"><div class="eyebrow">Задача</div><p>{{ L.task }}</p></div>
        <div class="codebox">
          <LessonListing :key="idx" :L="L" :missing="[cur.block]" mode="review" @resolved="resolved = true" />
        </div>
        <div class="actions">
          <button class="btn p" type="button" :disabled="!resolved || busy" @click="next">Дальше →</button>
        </div>
      </template>
    </template>

    <div v-else class="empty">
      <template v-if="doneAll">
        <h2>Готово</h2>
        <p>Повторено карточек: {{ finished }}.</p>
        <div class="actions" style="justify-content:center">
          <RouterLink class="btn p" :to="{ name: 'home' }">К урокам</RouterLink>
        </div>
      </template>
      <template v-else>
        <h2>Пока нечего повторять</h2>
        <p v-if="info.next_due">Ближайшая карточка будет готова {{ ruDate(info.next_due) }}.</p>
        <p v-else>Пройди хотя бы один урок, и методы появятся здесь.</p>
        <div class="actions" style="justify-content:center">
          <button v-if="info.has_cards" class="btn" type="button" @click="load(true)">Повторить всё изученное сейчас</button>
          <RouterLink v-else class="btn p" :to="{ name: 'home' }">К урокам</RouterLink>
        </div>
      </template>
    </div>
  </div>
</template>
