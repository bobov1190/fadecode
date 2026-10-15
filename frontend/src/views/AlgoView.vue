<script setup>
import { computed, onMounted, ref } from "vue";
import { useRoute } from "vue-router";
import { api } from "../api";

const route = useRoute();
const A = ref(null);
const error = ref("");

const levels = { easy: "лёгкая", medium: "средняя", hard: "сложная" };
const stNames = { new: "новая", open: "начата", solved: "решена", given_up: "подсмотрена" };
const stageNames = { "lesson-read": "разбор", "lesson-copy": "копирование", "lesson-recall": "вспоминание" };
const lessonRoute = { "lesson-read": "lesson", "lesson-copy": "lesson-copy", "lesson-recall": "lesson-recall" };

const solved = computed(() => (A.value ? A.value.problems.filter(p => p.status === "solved").length : 0));
const pct = computed(() => (A.value && A.value.problems.length ? Math.round((solved.value / A.value.problems.length) * 100) : 0));

const resume = computed(() => {
  const r = A.value && A.value.resume;
  if (!r) return null;
  if (r.stage === "problem") {
    const p = A.value.problems.find(x => x.id === r.ref);
    return p ? { to: { name: "problem", params: { pid: p.id } }, label: "задача «" + p.title + "»" } : null;
  }
  const L = [A.value.template, ...A.value.variations].find(x => x.id === r.ref);
  const name = lessonRoute[r.stage];
  return L && name ? { to: { name, params: { lid: L.id } }, label: stageNames[r.stage] + ": " + L.title } : null;
});

onMounted(async () => {
  try {
    A.value = await api.get("/algos/" + encodeURIComponent(route.params.aid));
  } catch (e) {
    error.value = e.message;
  }
});
</script>

<template>
  <div>
    <div v-if="error" class="flash bad" role="alert">{{ error }}</div>
    <p v-else-if="!A" class="muted">Загружаю…</p>
    <template v-else>
      <div class="eyebrow"><RouterLink class="crumb" :to="{ name: 'pack', params: { pid: A.pack } }">← Алгоритмы</RouterLink></div>
      <h1>{{ A.title }}</h1>
      <p class="muted">{{ A.desc }}</p>
      <div class="progress"><div class="bar"><i :style="{ width: pct + '%' }"></i></div><span>решено {{ solved }} из {{ A.problems.length }}</span></div>

      <div v-if="resume" class="task resume">
        <div class="eyebrow">Ты остановился здесь</div>
        <p>{{ resume.label }}</p>
        <div class="actions"><RouterLink class="btn p" :to="resume.to">Продолжить →</RouterLink></div>
      </div>

      <div class="sec">Шаг 1 · Шаблон</div>
      <div class="card tpl">
        <span class="tag">{{ A.template.methods }} методов</span>
        <h3>{{ A.template.title }}</h3>
        <p>{{ A.template.desc }}</p>
        <div class="actions">
          <RouterLink class="btn s" :class="{ p: !A.template.done }" :to="{ name: 'lesson', params: { lid: A.template.id } }">1 Разбор</RouterLink>
          <RouterLink class="btn s" :to="{ name: 'lesson-copy', params: { lid: A.template.id } }">2 Копирование</RouterLink>
          <RouterLink class="btn s" :to="{ name: 'lesson-recall', params: { lid: A.template.id } }">3 Вспоминание</RouterLink>
        </div>
        <div class="meta"><span>{{ A.template.done ? "шаблон выучен" : "сначала выучи шаблон, потом задачи" }}</span><span :class="{ ok: A.template.done }">{{ A.template.done ? "пройден" : "новый" }}</span></div>
      </div>

      <div class="sec">Шаг 2 · Задачи</div>
      <p v-if="!A.template.done" class="muted hintline">Задачи открыты, но проще, когда шаблон уже в голове.</p>
      <div class="plist">
        <RouterLink v-for="(p, i) in A.problems" :key="p.id" class="prow" :to="{ name: 'problem', params: { pid: p.id } }">
          <span class="t"><span class="num">{{ i + 1 }}{{ p.num ? " · LC " + p.num : "" }}</span><b>{{ p.title }}</b></span>
          <span class="t"><span class="lvl" :class="p.level">{{ levels[p.level] }}</span><span :class="'st-' + p.status">{{ stNames[p.status] }}</span></span>
        </RouterLink>
      </div>

      <template v-if="A.variations.length">
        <div class="sec">Дополнительно · вариации шаблона</div>
        <p class="muted hintline">Тот же приём в новых классах. Копирование и вспоминание, как в основном шаблоне.</p>
        <div class="grid">
          <RouterLink v-for="v in A.variations" :key="v.id" class="card" :to="{ name: 'lesson', params: { lid: v.id } }">
            <span class="tag">{{ v.methods }} методов</span><h3>{{ v.title }}</h3><p>{{ v.desc }}</p>
            <div class="meta"><span></span><span :class="{ ok: v.done }">{{ v.done ? "пройден" : "новый" }}</span></div>
          </RouterLink>
        </div>
      </template>
    </template>
  </div>
</template>
