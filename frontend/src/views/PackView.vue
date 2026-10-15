<script setup>
import { onMounted, ref } from "vue";
import { useRoute } from "vue-router";
import { api } from "../api";

const route = useRoute();
const pack = ref(null);
const error = ref("");

onMounted(async () => {
  try {
    pack.value = await api.get("/packs/" + encodeURIComponent(route.params.pid));
  } catch (e) {
    error.value = e.message;
  }
});
</script>

<template>
  <div>
    <div class="eyebrow"><RouterLink class="crumb" :to="{ name: 'home' }">← Пакеты</RouterLink></div>
    <div v-if="error" class="flash bad" role="alert">{{ error }}</div>
    <p v-else-if="!pack" class="muted">Загружаю…</p>
    <template v-else>
      <h1>{{ pack.title }}</h1>
      <p class="muted">{{ pack.desc }} Готово уроков: {{ pack.ready }} из {{ pack.items.length }}.</p>
      <div class="grid">
        <template v-for="it in pack.items" :key="it.n">
          <RouterLink v-if="it.lesson" class="card" :to="{ name: 'lesson', params: { lid: it.lesson } }">
            <span class="tag">{{ it.n }} · {{ it.category }}</span><h3>{{ it.name }}</h3><p>{{ it.desc }}</p>
            <div class="meta"><span>{{ it.lines }} строк</span><span :class="{ ok: it.finished }">{{ it.finished ? "пройден" : "новый" }}</span></div>
          </RouterLink>
          <div v-else class="card soon">
            <span class="tag">{{ it.n }} · {{ it.category }}</span><h3>{{ it.name }}</h3><p>{{ it.desc }}</p>
            <div class="meta"><span>урок готовится</span><span></span></div>
          </div>
        </template>
      </div>
    </template>
  </div>
</template>
