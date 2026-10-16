<script setup>
import { onMounted, ref } from "vue";
import { api } from "../api";
import { useAuth } from "../stores/auth";

const auth = useAuth();
const packs = ref(null);
const error = ref("");

onMounted(async () => {
  try {
    const r = await api.get("/packs");
    packs.value = r.packs;
    auth.due = r.due;
  } catch (e) {
    error.value = e.message;
  }
});
</script>

<template>
  <div>
    <div class="eyebrow">Уроки</div>
    <h1>Выбери пак</h1>
    <p class="muted">Каждый урок: копирование поверх призрака, потом методы пропадают, и ты вспоминаешь их по памяти.</p>
    <div v-if="error" class="flash bad" role="alert">{{ error }}</div>
    <p v-else-if="!packs" class="muted" style="margin-top:28px">Загружаю…</p>
    <div v-else class="grid">
      <RouterLink v-for="p in packs" :key="p.id" class="card" :to="{ name: 'pack', params: { pid: p.id } }">
        <span class="tag">{{ p.total }} тем</span>
        <h3>{{ p.title }}</h3>
        <p>{{ p.desc }}</p>
        <span v-if="p.author" class="by">Автор: {{ p.author }}</span>
        <span class="meta">
          <span>готово к изучению: {{ p.ready }}</span>
          <span :class="{ ok: p.finished }">пройдено: {{ p.finished }}/{{ p.total }}</span>
        </span>
      </RouterLink>
    </div>
  </div>
</template>
