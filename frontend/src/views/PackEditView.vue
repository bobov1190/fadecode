<script setup>
/* Форма пака: название, описание и пункты по порядку (карточка из списка или «урок готовится»). */
import { computed, onMounted, reactive, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { api } from "../api";
import { play } from "../lib/sfx";

const route = useRoute();
const router = useRouter();
const isNew = computed(() => route.params.pid === "new");
const form = reactive({ title: "", desc: "", author: "", items: [] });
const lessons = ref([]);
const algos = ref(0);
const error = ref("");
const ready = ref(false);
const busy = ref(false);
const pick = ref("");

const byId = computed(() => Object.fromEntries(lessons.value.map(l => [l.id, l])));
const free = computed(() => lessons.value.filter(l => !form.items.some(it => it.lesson === l.id)));
const optionsFor = it => lessons.value.filter(l => l.id === it.lesson || !form.items.some(x => x.lesson === l.id));

onMounted(async () => {
  try {
    const r = await api.get("/admin/content");
    lessons.value = r.lessons;
    if (!isNew.value) {
      const p = r.packs.find(x => x.id === route.params.pid);
      if (!p) throw new Error("Пак не найден.");
      Object.assign(form, { title: p.title, desc: p.desc, author: p.author, items: p.items.map(it => ({ ...it })) });
      algos.value = p.algos;
    }
    ready.value = true;
  } catch (e) {
    error.value = e.message;
  }
});

function addLesson() {
  const l = byId.value[pick.value];
  if (!l) return;
  form.items.push({ name: l.title, category: l.tag, desc: l.desc, lesson: l.id });
  pick.value = "";
  play("ok");
}
function addSoon() {
  form.items.push({ name: "", category: "", desc: "", lesson: null });
}
function move(i, d) {
  const j = i + d;
  if (j < 0 || j >= form.items.length) return;
  [form.items[i], form.items[j]] = [form.items[j], form.items[i]];
}
function remove(i) {
  form.items.splice(i, 1);
}

async function save() {
  if (busy.value) return;
  busy.value = true;
  error.value = "";
  const body = {
    title: form.title, desc: form.desc, author: form.author,
    items: form.items.map(it => ({ name: it.name, category: it.category, desc: it.desc, lesson: it.lesson || null })),
  };
  try {
    if (isNew.value) await api.post("/admin/packs", body);
    else await api.put("/admin/packs/" + route.params.pid, body);
    play("win");
    router.push({ name: "editor" });
  } catch (e) {
    error.value = e.message;
    play("err");
    window.scrollTo({ top: 0, behavior: "smooth" });
  } finally {
    busy.value = false;
  }
}
</script>

<template>
  <div>
    <div class="eyebrow"><RouterLink class="crumb" :to="{ name: 'editor' }">← Редактор</RouterLink></div>
    <h1>{{ isNew ? "Новый пак" : "Правка пака" }}</h1>
    <div v-if="error" class="flash bad" role="alert">{{ error }}</div>
    <p v-if="!ready && !error" class="muted">Загружаю…</p>

    <form v-if="ready" class="aform eform" @submit.prevent="save">
      <label>Название<input v-model="form.title" required maxlength="80" placeholder="Например, Алгоритмы на графах"></label>
      <label>Описание<textarea v-model="form.desc" rows="2" maxlength="600"></textarea></label>
      <label>Автор<input v-model="form.author" maxlength="60" :placeholder="isNew ? 'Если пусто, подставится твоё имя' : ''"></label>

      <div v-if="algos" class="task change"><p>В этом паке {{ algos }} алгоритмов с задачами. Их состав пока правится только через JSON, а здесь можно поменять название, описание и автора.</p></div>

      <div>
        <div class="eyebrow">Пункты по порядку ({{ form.items.length }})</div>
        <p v-if="!form.items.length" class="muted">Пока пусто. Добавь карточку из списка ниже.</p>
      </div>

      <div v-for="(it, i) in form.items" :key="i" class="eitem">
        <label class="wide">Название в паке<input v-model="it.name" maxlength="120" placeholder="Как увидят ученики"></label>
        <label>Категория<input v-model="it.category" maxlength="80"></label>
        <label>Карточка
          <select v-model="it.lesson">
            <option :value="null">урок готовится</option>
            <option v-for="l in optionsFor(it)" :key="l.id" :value="l.id">{{ l.title }}</option>
          </select>
        </label>
        <label class="wide">Описание<input v-model="it.desc" maxlength="600"></label>
        <div class="row wide">
          <button class="btn s g ib" type="button" :disabled="i === 0" aria-label="Выше" @click="move(i, -1)">↑</button>
          <button class="btn s g ib" type="button" :disabled="i === form.items.length - 1" aria-label="Ниже" @click="move(i, 1)">↓</button>
          <RouterLink v-if="it.lesson" class="btn s" :to="{ name: 'editor-lesson', params: { lid: it.lesson } }">Править карточку</RouterLink>
          <button class="btn s g" type="button" @click="remove(i)">Убрать из пака</button>
        </div>
      </div>

      <div class="addrow">
        <select v-model="pick" aria-label="Добавить карточку">
          <option value="">Добавить существующую карточку…</option>
          <option v-for="l in free" :key="l.id" :value="l.id">{{ l.title }}</option>
        </select>
        <button class="btn s" type="button" :disabled="!pick" @click="addLesson">Добавить</button>
        <button class="btn s g" type="button" @click="addSoon">+ «Урок готовится»</button>
        <RouterLink v-if="!isNew" class="btn s g" :to="{ name: 'editor-lesson', params: { lid: 'new' }, query: { pack: route.params.pid } }">+ Новая карточка</RouterLink>
      </div>
      <p v-if="isNew" class="muted">Чтобы создавать новые карточки прямо в паке, сначала сохрани его.</p>

      <div class="actions">
        <button class="btn p" type="submit" :disabled="busy">Сохранить</button>
        <RouterLink class="btn g" :to="{ name: 'editor' }">Отмена</RouterLink>
      </div>
    </form>
  </div>
</template>
