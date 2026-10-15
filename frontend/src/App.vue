<script setup>
import AppHeader from "./components/AppHeader.vue";
</script>

<template>
  <AppHeader />
  <main id="app">
    <RouterView v-slot="{ Component, route }">
      <component :is="Component" :key="route.name === 'pack' || route.name === 'lesson' ? route.fullPath : route.name" />
    </RouterView>
  </main>
</template>
