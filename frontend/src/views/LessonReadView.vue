<script setup>
import { computed, onMounted, ref } from "vue";
import { useRoute } from "vue-router";
import StepBar from "../components/StepBar.vue";
import { highlight } from "../lib/core";
import { useLesson } from "../stores/lesson";

const route = useRoute();
const lesson = useLesson();
const error = ref("");
const L = computed(() => (lesson.id === route.params.lid ? lesson.L : null));
const code = computed(() => (L.value ? highlight(L.value.code) : ""));

onMounted(async () => {
  try {
    await lesson.begin(route.params.lid);
    lesson.track("lesson-read");
  } catch (e) {
    error.value = e.message;
  }
});
</script>

<template>
  <div>
    <div v-if="error" class="flash bad" role="alert">{{ error }}</div>
    <p v-else-if="!L" class="muted">Загружаю…</p>
    <template v-else>
      <div v-if="L.algo" class="eyebrow"><RouterLink class="crumb" :to="{ name: 'algo', params: { aid: L.algo.id } }">← {{ L.algo.title }}</RouterLink></div>
      <StepBar cur="read" />
      <div class="eyebrow">{{ L.tag }}</div><h1>{{ L.title }}</h1>
      <div v-if="L.algo" class="task change"><p><b>{{ L.algo.role === "template" ? "Это шаблон, а не задача." : "Это вариация шаблона." }}</b> {{ L.algo.role === "template" ? "Сначала выучи его: разбор, копирование поверх призрака, вспоминание. Задачи на этот шаблон ждут на странице алгоритма." : "Тот же приём в другом виде. Выучи так же: разбор, копирование, вспоминание." }}</p></div>
      <div class="task"><div class="eyebrow">{{ L.algo ? "Что выучим" : "Задача" }}</div><p>{{ L.task }}</p></div>
      <div v-if="L.change" class="task change"><div class="eyebrow" style="color:var(--warn)">Что изменилось</div><p>{{ L.change }}</p></div>
      <div class="codebox"><pre class="code" v-html="code"></pre></div>
      <div class="notes">
        <div v-for="b in L.blocks" :key="b.id" class="note"><code>{{ b.name }}</code><span>{{ b.note }}</span></div>
      </div>
      <div class="actions">
        <RouterLink class="btn p" :to="{ name: 'lesson-copy', params: { lid: L.id } }">Копировать код →</RouterLink>
        <RouterLink class="btn" :to="{ name: 'lesson-recall', params: { lid: L.id } }">Сразу вспоминать</RouterLink>
      </div>
    </template>
  </div>
</template>
