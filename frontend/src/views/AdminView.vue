<script setup>
import { computed, onMounted, reactive, ref } from "vue";
import { api } from "../api";
import { play } from "../lib/sfx";

const items = ref(null);
const catalog = ref([]);
const error = ref("");
const note = ref("");
const editing = ref(null); // id или "new"
const form = reactive({ title: "", note: "", minutes: 40, max_score: 100, lessons: [] });
const busy = ref(false);

const byId = computed(() => Object.fromEntries(catalog.value.map(c => [c.id, c])));

async function load() {
  try {
    const r = await api.get("/admin/assign");
    items.value = r.items;
    catalog.value = r.catalog;
  } catch (e) {
    error.value = e.message;
  }
}

function openNew() {
  Object.assign(form, { title: "", note: "", minutes: 40, max_score: 100, lessons: [] });
  editing.value = "new";
  error.value = "";
}

function openEdit(it) {
  Object.assign(form, { title: it.title, note: it.note, minutes: it.minutes, max_score: it.max_score, lessons: [...it.lessons] });
  editing.value = it.id;
  error.value = "";
}

function toggle(id) {
  const i = form.lessons.indexOf(id);
  if (i >= 0) form.lessons.splice(i, 1); else form.lessons.push(id);
}

async function save() {
  if (busy.value) return;
  busy.value = true;
  error.value = "";
  const body = { title: form.title, note: form.note, minutes: form.minutes, max_score: form.max_score, lessons: form.lessons };
  try {
    if (editing.value === "new") await api.post("/admin/assign", body);
    else await api.put("/admin/assign/" + editing.value, body);
    editing.value = null;
    play("win");
    await load();
  } catch (e) {
    error.value = e.message;
    play("err");
  } finally {
    busy.value = false;
  }
}

async function remove(it) {
  if (!confirm("Удалить задание «" + it.title + "» вместе со всеми результатами?")) return;
  try {
    await api.del("/admin/assign/" + it.id);
    await load();
  } catch (e) {
    error.value = e.message;
  }
}

async function copyLink(it) {
  const url = location.origin + "/a/" + it.id;
  try { await navigator.clipboard.writeText(url); note.value = "Ссылка скопирована: " + url; play("ok"); }
  catch (e) { note.value = url; }
}

onMounted(load);
</script>

<template>
  <div>
    <div class="eyebrow">Админка</div>
    <h1>Задания</h1>
    <p class="muted">Собери задание из карточек-уроков, поставь время и максимум баллов. Ученики заходят по ссылке, балл считается сам.</p>
    <div v-if="error" class="flash bad" role="alert">{{ error }}</div>
    <div v-if="note" class="flash ok">{{ note }}</div>

    <form v-if="editing" class="aform" @submit.prevent="save">
      <h2>{{ editing === "new" ? "Новое задание" : "Правка задания" }}</h2>
      <label>Название<input v-model="form.title" required maxlength="120" placeholder="Например, Logistic regression и Softmax"></label>
      <label>Описание для учеников (необязательно)<textarea v-model="form.note" rows="3" maxlength="2000"></textarea></label>
      <div class="two">
        <label>Время, минут<input v-model.number="form.minutes" type="number" min="1" max="600" required></label>
        <label>Максимум баллов<input v-model.number="form.max_score" type="number" min="1" max="1000" required></label>
      </div>
      <div>
        <div class="eyebrow">Карточки (порядок выбора = порядок в задании)</div>
        <div class="picks">
          <button v-for="c in catalog" :key="c.id" type="button" class="opt pick" :class="{ right: form.lessons.includes(c.id) }" @click="toggle(c.id)">
            <b v-if="form.lessons.includes(c.id)">{{ form.lessons.indexOf(c.id) + 1 }}</b>{{ c.title }}
          </button>
        </div>
      </div>
      <div class="actions">
        <button class="btn p" type="submit" :disabled="busy || !form.lessons.length">Сохранить</button>
        <button class="btn g" type="button" @click="editing = null">Отмена</button>
      </div>
    </form>

    <div v-else class="actions"><button class="btn p" type="button" @click="openNew">+ Новое задание</button></div>

    <p v-if="!items && !error" class="muted">Загружаю…</p>
    <p v-else-if="items && !items.length && !editing" class="empty">Заданий пока нет.</p>
    <div class="grid">
      <div v-for="it in items" :key="it.id" class="card">
        <span class="tag">{{ it.minutes }} мин · {{ it.max_score }} баллов</span>
        <h3>{{ it.title }}</h3>
        <p>{{ it.lessons.map(l => (byId[l] || {}).title || l).join(" · ") }}</p>
        <div class="meta"><span>начали: {{ it.started }}</span><span>завершили: {{ it.finished }}</span></div>
        <div class="row" style="margin-top:12px">
          <RouterLink class="btn p s" :to="{ name: 'admin-results', params: { aid: it.id } }">Результаты</RouterLink>
          <button class="btn s" type="button" @click="copyLink(it)">Ссылка</button>
          <button class="btn s g" type="button" @click="openEdit(it)">Изменить</button>
          <button class="btn s g" type="button" @click="remove(it)">Удалить</button>
        </div>
      </div>
    </div>
  </div>
</template>
