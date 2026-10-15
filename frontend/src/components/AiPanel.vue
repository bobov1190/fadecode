<script setup>
/* Плавающая панель ИИ-наставника. Видна на экранах урока и повторения. Контекст берётся из стора ai. */
import { computed, nextTick, ref, watch } from "vue";
import { useRoute } from "vue-router";
import { useAi } from "../stores/ai";
import { useAuth } from "../stores/auth";

const route = useRoute();
const auth = useAuth();
const ai = useAi();
const input = ref("");
const inputEl = ref(null);
const msgsEl = ref(null);

// на повторении адрес без id урока, там урок отдаёт открытый листинг; пустой экран без карточки панель не показывает
const lessonId = computed(() => route.params.lid || ai.lesson);
const visible = computed(() => !!auth.user && !!route.meta.ai && !!lessonId.value);

function scroll() {
  nextTick(() => { if (msgsEl.value) msgsEl.value.scrollTop = msgsEl.value.scrollHeight; });
}

function open() {
  ai.open = true;
  nextTick(() => inputEl.value && inputEl.value.focus());
}

function send() {
  const t = input.value;
  input.value = "";
  ai.ask(t, { lesson: lessonId.value });
}

function onKey(e) {
  if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); }
}

watch(() => ai.msgs.length, scroll);
watch(() => ai.open, v => { if (v) scroll(); });
watch(lessonId, id => { if (id) ai.resetFor(id); }, { immediate: true });
</script>

<template>
  <div v-if="visible" id="ai-root">
    <button v-show="!ai.open" class="ai-fab" type="button" @click="open">ИИ-наставник</button>
    <section v-show="ai.open" class="ai-panel" aria-label="ИИ-наставник">
      <div class="ai-head"><span>ИИ-наставник</span><button type="button" aria-label="Закрыть" @click="ai.open = false">×</button></div>
      <div ref="msgsEl" class="ai-msgs">
        <div v-if="!ai.msgs.length" class="ai-hello">Спроси, как подступиться к методу. Готовый код я не дам, но наведу на мысль и покажу, где в твоей попытке расхождение.</div>
        <div v-for="(m, i) in ai.msgs" :key="i" class="ai-msg" :class="[m.role, m.cls]">{{ m.text }}</div>
      </div>
      <div class="ai-foot">
        <div class="ai-row">
          <textarea ref="inputEl" v-model="input" placeholder="Твой вопрос…" maxlength="600" @keydown="onKey"></textarea>
          <button class="btn p s" type="button" :disabled="ai.busy" @click="send">→</button>
        </div>
        <div class="ai-quota">{{ ai.left === null ? "" : "Осталось запросов сегодня: " + ai.left }}</div>
      </div>
    </section>
  </div>
</template>
