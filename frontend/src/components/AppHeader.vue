<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import MascotCat from "./MascotCat.vue";
import NavIcon from "./NavIcon.vue";
import { useAi } from "../stores/ai";
import { useAuth } from "../stores/auth";
import { Sfx, play } from "../lib/sfx";

const auth = useAuth();
const ai = useAi();
const route = useRoute();
const router = useRouter();

const open = ref(false);
const wrap = ref(null);
const btn = ref(null);
const on = ref(Sfx.enabled());
const vol = ref(Math.round(Sfx.volume() * 100));
const tab = computed(() => route.meta.tab || "");
// чат наставника на телефоне живёт в нижнем меню; условие видимости то же, что у AiPanel
const chatVisible = computed(() => !!auth.user && !!route.meta.ai && !!(route.params.lid || ai.lesson || ai.problem));
const initial = computed(() => (auth.user ? auth.user.username.slice(0, 1).toUpperCase() : ""));

function toggleChat() {
  ai.open = !ai.open;
  play(ai.open ? "open" : "close");
}
function toggle() {
  open.value = !open.value;
  play(open.value ? "open" : "close");
}
function onDoc(e) {
  if (open.value && wrap.value && !wrap.value.contains(e.target)) open.value = false;
}
function onKey(e) {
  if (e.key === "Escape" && open.value) { open.value = false; btn.value && btn.value.focus(); }
}
function setOn() {
  Sfx.setEnabled(on.value);
  play(on.value ? "on" : "off", true);
}
function setVol() { Sfx.setVolume(vol.value / 100); }
function logout() {
  open.value = false;
  auth.drop();
  router.push({ name: "login" });
}

onMounted(() => { document.addEventListener("click", onDoc); document.addEventListener("keydown", onKey); });
onBeforeUnmount(() => { document.removeEventListener("click", onDoc); document.removeEventListener("keydown", onKey); });
</script>

<template>
  <header class="top">
    <div class="in">
      <RouterLink class="logo" :to="{ name: auth.user && auth.user.is_admin ? 'admin' : 'home' }" aria-label="Fadecode">
        <img class="lg-full" src="/logo-dark.svg" alt="Fadecode">
        <img class="lg-mark" src="/mark.svg" alt="">
      </RouterLink>

      <nav v-if="auth.user" class="tabs" aria-label="Разделы">
        <RouterLink v-if="auth.user.is_admin" class="tab" :class="{ on: tab === 'admin' }" :to="{ name: 'admin' }">
          <NavIcon name="tasks" /><span class="lbl">Задания</span>
        </RouterLink>
        <RouterLink v-if="auth.user.is_admin" class="tab" :class="{ on: tab === 'editor' }" :to="{ name: 'editor' }">
          <NavIcon name="editor" /><span class="lbl">Редактор</span>
        </RouterLink>
        <RouterLink class="tab" :class="{ on: tab === 'home' }" :to="{ name: 'home' }">
          <NavIcon name="lessons" /><span class="lbl">Уроки</span>
        </RouterLink>
        <RouterLink class="tab" :class="{ on: tab === 'review' }" :to="{ name: 'review' }">
          <NavIcon name="review" /><span class="lbl">Повторение</span><span v-if="auth.due" class="badge">{{ auth.due }}</span>
        </RouterLink>
        <RouterLink class="tab" :class="{ on: tab === 'stats' }" :to="{ name: 'stats' }">
          <NavIcon name="stats" /><span class="lbl">Прогресс</span>
        </RouterLink>
        <button v-if="chatVisible" class="tab chat-tab" :class="{ on: ai.open }" type="button"
                aria-label="ИИ-наставник" :aria-pressed="ai.open" @click="toggleChat">
          <MascotCat /><span class="lbl">ИИ-наставник</span>
        </button>
      </nav>

      <div id="sfx-wrap" ref="wrap" class="sfx">
        <button ref="btn" class="menubtn" :class="{ 'muted-on': !on }" type="button" aria-label="Меню"
                :aria-expanded="open" aria-controls="sfx-pop" @click="toggle">
          <i v-if="auth.user" class="ava">{{ initial }}</i>
          <svg v-else viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><circle cx="5" cy="12" r="1.8"/><circle cx="12" cy="12" r="1.8"/><circle cx="19" cy="12" r="1.8"/></svg>
        </button>
        <div v-show="open" id="sfx-pop" class="setpop">
          <div v-if="auth.user" class="pop-user"><i class="ava">{{ initial }}</i><span>{{ auth.user.username }}</span></div>
          <label class="swrow"><span>Звуки</span><input v-model="on" type="checkbox" class="sw" @change="setOn"></label>
          <label class="swrow"><span>Громкость</span>
            <input v-model.number="vol" type="range" min="0" max="100" step="5" :disabled="!on" @input="setVol" @change="play('ok')">
          </label>
          <button class="btn s g" type="button" :disabled="!on" @click="play('win')">Проверить звук</button>
          <div class="pop-links">
            <a class="linkbtn" href="/about">О проекте</a>
            <button v-if="auth.user" class="linkbtn" type="button" @click="logout">Выйти</button>
          </div>
        </div>
      </div>
    </div>
  </header>
</template>
