<script setup>
/* Прогресс: цифры, коробки SRS, ИИ-разбор, настройки, экспорт и сброс. */
import { onMounted, reactive, ref } from "vue";
import { api } from "../api";
import { play } from "../lib/sfx";
import { useAuth } from "../stores/auth";

const auth = useAuth();
const error = ref("");
const loading = ref(true);
const data = ref(null);
const set = reactive({ order: "small", rounds: "all", research: true });
const saved = ref("");
const advice = reactive({ show: false, text: "", err: false, busy: false });

async function load() {
  loading.value = true;
  error.value = "";
  try {
    data.value = await api.get("/stats");
    Object.assign(set, data.value.settings);
    auth.due = data.value.cards.due;
  } catch (e) {
    error.value = e.message;
  } finally {
    loading.value = false;
  }
}

async function saveSettings() {
  try {
    const r = await api.put("/settings", { order: set.order, rounds: set.rounds, research: set.research });
    Object.assign(set, r.settings);
    saved.value = "Сохранено";
    play("ok");
    setTimeout(() => { saved.value = ""; }, 2000);
  } catch (e) {
    saved.value = e.message;
    play("err");
  }
}

async function getAdvice() {
  advice.show = true;
  advice.err = false;
  advice.busy = true;
  advice.text = "Думаю…";
  try {
    advice.text = (await api.post("/ai/advice")).text;
  } catch (e) {
    advice.err = true;
    advice.text = e.message;
  } finally {
    advice.busy = false;
  }
}

async function exportLog() {
  try {
    const r = await api.get("/export");
    const url = URL.createObjectURL(new Blob([JSON.stringify(r, null, 2)], { type: "application/json" }));
    const a = document.createElement("a");
    a.href = url;
    a.download = "fadecode-export.json";
    a.click();
    URL.revokeObjectURL(url);
  } catch (e) {
    error.value = e.message;
  }
}

async function reset() {
  if (!confirm("Стереть весь прогресс и журнал?")) return;
  try {
    await api.post("/reset");
    advice.show = false;
    await auth.refreshDue();
    await load();
  } catch (e) {
    error.value = e.message;
  }
}

onMounted(load);
</script>

<template>
  <div>
    <div class="eyebrow">прогресс</div>
    <h1>Как идёт память</h1>
    <div v-if="error" class="flash bad" role="alert">{{ error }}</div>
    <p v-if="loading" class="muted">Загружаю…</p>

    <template v-else-if="data">
      <div class="stats">
        <div class="stat"><b>{{ data.cards.done }}</b><span>уроков пройдено</span></div>
        <div class="stat"><b>{{ data.cards.fixed }}</b><span>методов закреплено</span></div>
        <div class="stat"><b>{{ data.cards.accuracy === null ? "—" : data.cards.accuracy + "%" }}</b><span>вспомнено с первого раза</span></div>
        <div class="stat"><b>{{ data.cards.due }}</b><span>карточек к повторению</span></div>
      </div>

      <table>
        <thead><tr><th>Урок</th><th>Методов изучено</th><th>Коробки (светлее значит надёжнее)</th><th></th></tr></thead>
        <tbody>
          <tr v-for="r in data.rows" :key="r.id">
            <td>{{ r.title }}</td>
            <td>{{ r.learned }} / {{ r.total }}</td>
            <td>
              <div class="boxes">
                <template v-for="(n, i) in r.boxes" :key="i">
                  <i v-if="n" :style="{ width: n * 16 + 'px', opacity: 0.3 + i * 0.175 }"></i>
                </template>
              </div>
            </td>
            <td><span v-if="r.finished" class="g-good">пройден</span><span v-else class="muted">—</span></td>
          </tr>
        </tbody>
      </table>

      <div class="sec">ИИ-разбор</div>
      <p class="muted" style="margin-top:8px">ИИ посмотрит, какие методы запомнены хуже всего, и посоветует, что повторить первым.</p>
      <div class="actions" style="margin-top:12px">
        <button class="btn" type="button" :disabled="!data.has_progress || advice.busy" @click="getAdvice">Разобрать мой прогресс</button>
      </div>
      <div v-if="advice.show" class="advice" :class="{ err: advice.err, muted: advice.busy }">{{ advice.text }}</div>

      <div class="sec">Настройки</div>
      <div class="set">
        <label>Порядок исчезновения
          <select v-model="set.order">
            <option value="small">от маленького к большому</option>
            <option value="random">случайный</option>
          </select>
        </label>
        <label>Раунды
          <select v-model="set.rounds">
            <option value="all">накопительные: старые пропажи остаются</option>
            <option value="one">по одному полю за раунд</option>
          </select>
        </label>
        <label><input v-model="set.research" type="checkbox"> писать журнал попыток</label>
        <button class="btn s" type="button" @click="saveSettings">Сохранить</button>
        <span v-if="saved" class="muted">{{ saved }}</span>
      </div>

      <div class="actions">
        <button class="btn" type="button" @click="exportLog">Скачать журнал (JSON)</button>
        <button class="btn g" type="button" @click="reset">Стереть прогресс</button>
      </div>
    </template>
  </div>
</template>
