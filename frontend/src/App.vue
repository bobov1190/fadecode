<script setup>
import { watch } from "vue";
import AiPanel from "./components/AiPanel.vue";
import AppHeader from "./components/AppHeader.vue";
import AssignBar from "./components/AssignBar.vue";
import { useAssign } from "./stores/assign";
import { useAuth } from "./stores/auth";

const auth = useAuth();
const assign = useAssign();
watch(() => auth.user && auth.user.id, id => { if (id) assign.load(); else assign.clear(); }, { immediate: true });
</script>

<template>
  <AppHeader />
  <AssignBar />
  <main id="app">
    <RouterView v-slot="{ Component, route }">
      <component :is="Component" :key="route.fullPath" />
    </RouterView>
  </main>
  <AiPanel />
</template>
