<script setup>
defineProps({ title: { type: String, default: "Скоро" } });
</script>

<template>
  <div class="empty">
    <h2>{{ title }}</h2>
    <p>Этот экран ещё переезжает на Vue.</p>
    <div class="actions" style="justify-content:center">
      <RouterLink class="btn" :to="{ name: 'home' }">К урокам</RouterLink>
    </div>
  </div>
</template>
