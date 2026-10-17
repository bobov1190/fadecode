<script setup>
/* Крупные «пухлые» иконки нижнего меню в духе Duolingo, но в одной палитре проекта:
   основная форма красится currentColor, вторая часть полупрозрачна (двухтоновость без радуги). */
defineProps({ name: { type: String, required: true } });
</script>

<template>
  <svg class="nav-ico" viewBox="0 0 32 32" aria-hidden="true" focusable="false">
    <!-- Уроки: раскрытая книга -->
    <template v-if="name === 'lessons'">
      <path d="M3 8.2c0-1.1.9-1.9 2-1.7 3.7.5 7.1 1.8 9.4 4v14.7c-2.5-1.9-5.7-3-9.2-3.3-1.2-.1-2.2-1-2.2-2.2V8.2Z" fill="currentColor" />
      <path d="M29 8.2c0-1.1-.9-1.9-2-1.7-3.7.5-7.1 1.8-9.4 4v14.7c2.5-1.9 5.7-3 9.2-3.3 1.2-.1 2.2-1 2.2-2.2V8.2Z" fill="currentColor" opacity=".55" />
      <rect x="14.4" y="10.4" width="3.2" height="15.4" rx="1.6" fill="currentColor" />
    </template>
    <!-- Повторение: две карточки -->
    <template v-else-if="name === 'review'">
      <rect x="7.5" y="3.5" width="19" height="20" rx="5" transform="rotate(8 17 13.5)" fill="currentColor" opacity=".5" />
      <rect x="4.5" y="7.5" width="19" height="21" rx="5" transform="rotate(-6 14 18)" fill="currentColor" />
      <path d="M10 18.2l3 3 6-6.4" fill="none" stroke="#0d100e" stroke-width="2.8" stroke-linecap="round" stroke-linejoin="round" transform="rotate(-6 14 18)" />
    </template>
    <!-- Прогресс: столбики -->
    <template v-else-if="name === 'stats'">
      <rect x="4" y="16" width="6.4" height="12" rx="3.2" fill="currentColor" opacity=".55" />
      <rect x="12.8" y="4" width="6.4" height="24" rx="3.2" fill="currentColor" />
      <rect x="21.6" y="11" width="6.4" height="17" rx="3.2" fill="currentColor" opacity=".8" />
    </template>
    <!-- Задания: планшет с галочкой -->
    <template v-else-if="name === 'tasks'">
      <rect x="5.5" y="5" width="21" height="24" rx="5" fill="currentColor" />
      <rect x="11" y="2.5" width="10" height="6.5" rx="3" fill="currentColor" opacity=".55" />
      <path d="M11 18.2l3.6 3.6 6.6-7.2" fill="none" stroke="#0d100e" stroke-width="2.9" stroke-linecap="round" stroke-linejoin="round" />
    </template>
    <!-- Редактор: карандаш -->
    <template v-else-if="name === 'editor'">
      <path d="M21.6 4.4a3.4 3.4 0 0 1 4.8 0l1.2 1.2a3.4 3.4 0 0 1 0 4.8L11.8 26.2 4 28l1.8-7.8L21.6 4.4Z" fill="currentColor" />
      <path d="M19 7l6 6" stroke="#0d100e" stroke-width="2.6" stroke-linecap="round" opacity=".55" />
    </template>
  </svg>
</template>

<style scoped>
.nav-ico { width: 28px; height: 28px; display: block; }
</style>
