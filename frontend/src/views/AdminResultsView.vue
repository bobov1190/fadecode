<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { useRoute } from "vue-router";
import { api } from "../api";
import { dur, num } from "../lib/fmt";

const route = useRoute();
const data = ref(null);
const error = ref("");
const open = ref(null);
let iv = null;

const A = computed(() => data.value && data.value.assignment);
const rows = computed(() => (data.value ? data.value.results : []));
const label = { running: "идёт", finished: "завершил" };

async function load() {
  try {
    data.value = await api.get("/admin/assign/" + encodeURIComponent(route.params.aid));
  } catch (e) {
    error.value = e.message;
  }
}

async function reset(r) {
  if (!confirm("Сбросить попытку: " + (r.name || r.username) + "? Человек сможет пройти задание заново.")) return;
  try {
    await api.del("/admin/assign/" + encodeURIComponent(route.params.aid) + "/attempt/" + r.user_id);
    await load();
  } catch (e) {
    error.value = e.message;
  }
}

function csv() {
  const q = v => '"' + String(v).replace(/"/g, '""') + '"';
  const head = ["Имя", "Логин", "Статус", "Минут", "Балл", "Максимум"];
  const lines = [head.map(q).join(";")];
  for (const r of rows.value) {
    lines.push([r.name, r.username, label[r.status] || r.status, (r.spent_sec / 60).toFixed(1),
      r.status === "finished" ? String(r.score).replace(".", ",") : "", A.value.max_score].map(q).join(";"));
  }
  const blob = new Blob(["\ufeff" + lines.join("\r\n")], { type: "text/csv;charset=utf-8" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "results-" + A.value.id + ".csv";
  a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 1000);
}

onMounted(() => { load(); iv = setInterval(load, 15000); });
onBeforeUnmount(() => clearInterval(iv));
</script>

<template>
  <div>
    <div class="eyebrow"><RouterLink class="crumb" :to="{ name: 'admin' }">← Задания</RouterLink></div>
    <div v-if="error" class="flash bad" role="alert">{{ error }}</div>
    <p v-if="!data && !error" class="muted">Загружаю…</p>
    <template v-if="data">
      <h1>{{ A.title }}</h1>
      <p class="muted">{{ A.minutes }} мин · максимум {{ A.max_score }} · карточек: {{ A.cards.length }}. Список обновляется сам.</p>
      <div class="actions"><button class="btn p" type="button" :disabled="!rows.length" @click="csv">Скачать CSV для LMS</button></div>
      <p v-if="!rows.length" class="empty">Пока никто не начинал.</p>
      <table v-else>
        <thead><tr><th>Имя</th><th>Логин</th><th>Статус</th><th>Время</th><th>Балл</th><th></th></tr></thead>
        <tbody>
          <template v-for="r in rows" :key="r.user_id">
            <tr>
              <td>{{ r.name || "без имени" }}</td>
              <td class="mono">{{ r.username }}</td>
              <td>{{ label[r.status] }}</td>
              <td>{{ dur(r.spent_sec) }}</td>
              <td><b v-if="r.status === 'finished'">{{ num(r.score) }}</b><span v-else class="muted">…</span> <span class="muted">/ {{ A.max_score }}</span></td>
              <td class="rowbtns">
                <button v-if="r.breakdown" class="btn s g" type="button" @click="open = open === r.user_id ? null : r.user_id">Разбор</button>
                <button class="btn s g" type="button" @click="reset(r)">Сбросить</button>
              </td>
            </tr>
            <tr v-if="open === r.user_id && r.breakdown" class="detail"><td colspan="6">
              <div v-for="b in r.breakdown" :key="b.id" class="bd">
                <div class="bd-h"><h3>{{ b.title }}</h3><b>{{ num(b.score) }} / {{ num(b.max) }}</b></div>
                <div class="bd-r"><span>Копирование</span><span>{{ b.copy_errors === null ? "пропущено" : "ошибок: " + b.copy_errors }}</span></div>
                <div v-for="s in b.slots" :key="s.id" class="bd-r">
                  <span>{{ s.name }}</span>
                  <span>{{ s.revealed ? "показал ответ" : !s.solved ? "не решено" : "неверных: " + s.wrong + ", подсказок: " + s.hints + (s.accepted ? ", «почти»" : "") }}</span>
                </div>
              </div>
            </td></tr>
          </template>
        </tbody>
      </table>
    </template>
  </div>
</template>
