<script setup>
/* Плашка с таймером задания на всех экранах и блокирующее окно, когда время вышло. */
import { onBeforeUnmount, onMounted, watch } from "vue";
import { useRouter } from "vue-router";
import { clock } from "../lib/fmt";
import { play } from "../lib/sfx";
import { useAssign } from "../stores/assign";

const assign = useAssign();
const router = useRouter();
let iv = null;
let warned = false;

function tick() {
  const was = assign.over;
  assign.tick();
  if (assign.active && assign.left <= 300 && assign.left > 0 && !warned) { warned = true; play("warn"); }
  if (!was && assign.over) play("lose");
}

function results() {
  const id = assign.active && assign.active.id;
  assign.clear();
  if (id) router.push({ name: "assign", params: { aid: id } });
}

watch(() => assign.active && assign.active.id, () => { warned = false; });
onMounted(() => { iv = setInterval(tick, 1000); });
onBeforeUnmount(() => clearInterval(iv));
</script>

<template>
  <template v-if="assign.active">
    <RouterLink class="abar" :class="{ low: assign.left <= 300 }" :to="{ name: 'assign', params: { aid: assign.active.id } }">
      <span class="abar-t">{{ assign.active.title }}</span>
      <b class="abar-c">{{ clock(assign.left) }}</b>
    </RouterLink>
    <div v-if="assign.over" class="modal" role="alertdialog" aria-modal="true">
      <div class="modal-box">
        <div class="eyebrow" style="color:var(--bad)">Время вышло</div>
        <h2>{{ assign.active.title }}</h2>
        <p class="muted">Всё, что ты успел до дедлайна, засчитано. Дальше работа по этому заданию не учитывается.</p>
        <div class="actions"><button class="btn p" type="button" @click="results">Посмотреть результат</button></div>
      </div>
    </div>
  </template>
</template>
