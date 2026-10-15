<script setup>
import { computed, onMounted, reactive, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { api } from "../api";
import LessonListing from "../components/LessonListing.vue";
import StepBar from "../components/StepBar.vue";
import { play } from "../lib/sfx";
import { useLesson } from "../stores/lesson";

const route = useRoute();
const router = useRouter();
const lesson = useLesson();
const error = ref("");
const ready = ref(false);
const busy = ref(false);
const resolved = reactive({});

const L = computed(() => lesson.L);
const N = computed(() => L.value.blocks.length);
const r = computed(() => Math.max(1, Math.min(parseInt(route.query.round, 10) || 1, N.value + 1)));
const whole = computed(() => r.value > N.value);
const one = computed(() => lesson.settings.rounds === "one");
const missing = computed(() => (whole.value ? [] : one.value ? [lesson.order[r.value - 1]] : lesson.order.slice(0, r.value)));
const names = computed(() => Object.fromEntries(L.value.blocks.map(b => [b.id, b.name])));
const allDone = computed(() => {
  const ids = whole.value ? ["whole"] : missing.value;
  return ids.length > 0 && ids.every(id => resolved[id]);
});
const nextLabel = computed(() => (whole.value ? "Завершить урок" : r.value === N.value ? "Дальше: весь класс →" : "Дальше: пропадёт ещё метод →"));

function onResolved(e) {
  resolved[e.id] = true;
  if (e.id !== "whole") lesson.grade(e.id, e.grade);
}

async function next() {
  if (!allDone.value || busy.value) return;
  busy.value = true;
  play("next");
  if (whole.value) {
    try { await api.post("/lesson_done", { lesson: L.value.id }); } catch (e) { /* дойдём до итогов в любом случае */ }
    router.push({ name: "lesson-done", params: { lid: L.value.id } });
  } else {
    router.push({ name: "lesson-recall", params: { lid: L.value.id }, query: { round: r.value + 1 } });
  }
}

onMounted(async () => {
  try {
    await lesson.ensure(route.params.lid);
    ready.value = true;
  } catch (e) {
    error.value = e.message;
  }
});
</script>

<template>
  <div>
    <div v-if="error" class="flash bad" role="alert">{{ error }}</div>
    <p v-else-if="!ready" class="muted">Загружаю…</p>
    <template v-else>
      <StepBar cur="recall" />
      <div class="roundhead">
        <div>
          <div class="eyebrow">Раунд {{ r }} из {{ N + 1 }}</div>
          <h2>{{ whole ? "Весь класс по памяти" : one ? "Пропал метод: " + names[missing[0]] : "Пропало методов: " + r }}</h2>
          <p class="muted">{{ whole ? "Напиши класс целиком, начиная со строки class." : "Впиши пропавшие методы. Ctrl+Enter проверяет." }}</p>
        </div>
        <div class="dots"><i v-for="i in N + 1" :key="i" :class="{ on: i < r, cur: i === r }"></i></div>
      </div>
      <div class="task"><div class="eyebrow">Задача</div><p>{{ L.task }}</p></div>
      <div class="codebox">
        <LessonListing :L="L" :missing="missing" :whole="whole" mode="recall" @resolved="onResolved" />
      </div>
      <div class="actions">
        <button class="btn p" type="button" :disabled="!allDone || busy" @click="next">{{ nextLabel }}</button>
      </div>
    </template>
  </div>
</template>
