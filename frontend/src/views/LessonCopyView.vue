<script setup>
import { computed, nextTick, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { api } from "../api";
import CodeEditor from "../components/CodeEditor.vue";
import StepBar from "../components/StepBar.vue";
import { play } from "../lib/sfx";
import { useLesson } from "../stores/lesson";

const route = useRoute();
const router = useRouter();
const lesson = useLesson();
const error = ref("");
const ready = ref(false);
const editor = ref(null);
const typed = ref("");
const bad = ref(0);
let finished = false;

const L = computed(() => lesson.L);
const target = computed(() => (L.value ? L.value.code : ""));
const pct = computed(() => (target.value ? Math.round((typed.value.length / target.value.length) * 100) : 0));
const complete = computed(() => ready.value && typed.value.replace(/\s+$/, "") === target.value);

function onChange(v) {
  typed.value = v;
  if (!finished && v.replace(/\s+$/, "") === target.value) { finished = true; play("ok"); }
}

async function next() {
  try { await api.post("/copy_done", { lesson: L.value.id, errors: bad.value }); } catch (e) { /* журнал не критичен */ }
  play("next");
  router.push({ name: "lesson-recall", params: { lid: L.value.id } });
}

onMounted(async () => {
  try {
    await lesson.ensure(route.params.lid);
    ready.value = true;
    await nextTick();
    editor.value && editor.value.focus();
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
      <StepBar cur="copy" />
      <div class="eyebrow">Копирование</div><h2>Печатай поверх призрака</h2>
      <p class="muted">Верные символы загораются, ошибки краснеют. Enter сам ставит отступ.</p>
      <div class="codebox">
        <CodeEditor ref="editor" mode="ghost" :target="target" :rows="target.split('\n').length"
                    @change="onChange" @error="n => (bad = n)" />
      </div>
      <div class="progress"><div class="bar"><i :style="{ width: pct + '%' }"></i></div><span>{{ pct }}% · ошибок: {{ bad }}</span></div>
      <div class="actions">
        <button class="btn p" type="button" :disabled="!complete" @click="next">Дальше: пропадёт метод →</button>
        <RouterLink class="btn g" :to="{ name: 'lesson-recall', params: { lid: L.id } }">Пропустить</RouterLink>
      </div>
    </template>
  </div>
</template>
