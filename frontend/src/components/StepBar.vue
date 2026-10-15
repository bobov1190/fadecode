<script setup>
defineProps({ cur: { type: String, required: true } });
const labels = [["read", "1 Разбор"], ["copy", "2 Копирование"], ["recall", "3 Вспоминание"]];
const keys = labels.map(l => l[0]);
</script>

<template>
  <div class="steps">
    <span v-for="([k, label], i) in labels" :key="k" class="st"
          :class="{ on: i === keys.indexOf(cur), done: i < keys.indexOf(cur) }">{{ label }}</span>
  </div>
</template>
