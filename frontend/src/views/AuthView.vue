<script setup>
import { computed, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useAuth } from "../stores/auth";
import { play } from "../lib/sfx";

const auth = useAuth();
const route = useRoute();
const router = useRouter();
const isReg = computed(() => route.name === "register");
const username = ref("");
const password = ref("");
const fullName = ref("");
const error = ref("");
const busy = ref(false);
const form = ref(null);

async function submit() {
  if (busy.value) return;
  error.value = "";
  busy.value = true;
  try {
    await (isReg.value ? auth.register(username.value.trim(), password.value, fullName.value.trim()) : auth.login(username.value.trim(), password.value));
    play("win");
    const next = String(route.query.next || "");
    router.push(next.startsWith("/") && !next.startsWith("//") ? next : { name: auth.user && auth.user.is_admin ? "admin" : "home" });
  } catch (e) {
    error.value = e.message;
    play("err");
    const el = form.value;
    if (el) { el.classList.remove("shake"); void el.offsetWidth; el.classList.add("shake"); }
  } finally {
    busy.value = false;
  }
}
</script>

<template>
  <div class="auth">
    <div class="eyebrow">{{ isReg ? "Регистрация" : "Вход" }}</div>
    <h1>{{ isReg ? "Создай аккаунт" : "С возвращением" }}</h1>
    <div v-if="error" class="flash bad" role="alert">{{ error }}</div>
    <form ref="form" @submit.prevent="submit">
      <label>Логин
        <input v-model="username" autocomplete="username" required minlength="3" maxlength="32" autofocus>
      </label>
      <label v-if="isReg">Имя и фамилия (по ним учитель найдёт твой балл)
        <input v-model="fullName" autocomplete="name" maxlength="80" placeholder="Иван Петров">
      </label>
      <label>Пароль
        <input v-model="password" type="password" :autocomplete="isReg ? 'new-password' : 'current-password'" required minlength="6">
      </label>
      <button class="btn p" type="submit" :disabled="busy">{{ busy ? "Секунду…" : isReg ? "Зарегистрироваться" : "Войти" }}</button>
    </form>
    <p class="alt">
      <template v-if="isReg">Уже есть аккаунт? <RouterLink :to="{ name: 'login', query: route.query }">Войти</RouterLink></template>
      <template v-else>Нет аккаунта? <RouterLink :to="{ name: 'register', query: route.query }">Зарегистрироваться</RouterLink></template>
    </p>
  </div>
</template>
