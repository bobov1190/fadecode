<script setup>
import AiPanel from "./components/AiPanel.vue";
import AppHeader from "./components/AppHeader.vue";
</script>

<template>
  <AppHeader />
  <main id="app">
    <RouterView v-slot="{ Component, route }">
      <component :is="Component" :key="route.fullPath" />
    </RouterView>
  </main>
  <AiPanel />
</template>
