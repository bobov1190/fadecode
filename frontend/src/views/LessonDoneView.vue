<script setup>
import { computed, onMounted, ref } from "vue";
import { useRoute } from "vue-router";
import { play } from "../lib/sfx";
import { useAuth } from "../stores/auth";
import { useLesson } from "../stores/lesson";

const route = useRoute();
const lesson = useLesson();
const auth = useAuth();
const error = ref("");
const ready = ref(false);
const names = { good: "с первого раза", hard: "с трудом", again: "не вспомнил" };

const L = computed(() => lesson.L);
const rows = computed(() => L.value.blocks.filter(b => b.id in lesson.grades).map(b => [b.name, lesson.grades[b.id]]));

onMounted(async () => {
  try {
    await lesson.load(route.params.lid);
    ready.value = true;
    play("win");
    auth.refreshDue();
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
      <div class="eyebrow">Урок пройден</div><h1>{{ L.title }}</h1>
      <p class="muted">Что не вспомнилось, вернётся в разделе «Повторение» раньше остальных.</p>
      <div class="sum">
        <div v-for="[name, grade] in rows" :key="name"><code>{{ name }}</code><span :class="'g-' + grade">{{ names[grade] }}</span></div>
      </div>
      <div class="actions">
        <RouterLink v-if="L.algo && L.algo.role === 'template'" class="btn p" :to="{ name: 'algo', params: { aid: L.algo.id } }">К задачам →</RouterLink>
        <RouterLink v-else-if="L.algo" class="btn p" :to="{ name: 'algo', params: { aid: L.algo.id } }">К алгоритму →</RouterLink>
        <RouterLink v-if="L.next" class="btn p" :to="{ name: 'lesson', params: { lid: L.next.id } }">Следующий: {{ L.next.title }} →</RouterLink>
        <RouterLink class="btn" :to="{ name: 'lesson', params: { lid: L.id } }">Пройти заново</RouterLink>
        <RouterLink class="btn g" :to="L.pack ? { name: 'pack', params: { pid: L.pack.id } } : { name: 'home' }">К урокам</RouterLink>
      </div>
    </template>
  </div>
</template>
