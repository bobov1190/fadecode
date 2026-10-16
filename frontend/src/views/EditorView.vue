<script setup>
/* Редактор: паки по порядку и все карточки. Отсюда идут формы пака и карточки. */
import { onMounted, ref } from "vue";
import { api } from "../api";
import { play } from "../lib/sfx";

const data = ref(null);
const error = ref("");
const note = ref("");

async function load() {
  try {
    data.value = await api.get("/admin/content");
  } catch (e) {
    error.value = e.message;
  }
}

async function move(i, d) {
  const ids = data.value.packs.map(p => p.id);
  const j = i + d;
  if (j < 0 || j >= ids.length) return;
  [ids[i], ids[j]] = [ids[j], ids[i]];
  try {
    await api.put("/admin/pack-order", { ids });
    play("ok");
    await load();
  } catch (e) {
    error.value = e.message;
    play("err");
  }
}

async function removePack(p) {
  if (!confirm("Удалить пак «" + p.title + "»? Сами карточки останутся.")) return;
  error.value = "";
  try {
    await api.del("/admin/packs/" + p.id);
    note.value = "Пак удалён.";
    await load();
  } catch (e) {
    error.value = e.message;
    play("err");
  }
}

async function removeLesson(l) {
  if (!confirm("Удалить карточку «" + l.title + "»? Прогресс учеников по ней тоже пропадёт.")) return;
  error.value = "";
  try {
    await api.del("/admin/lessons/" + l.id);
    note.value = "Карточка удалена.";
    await load();
  } catch (e) {
    error.value = e.message;
    play("err");
  }
}

onMounted(load);
</script>

<template>
  <div>
    <div class="eyebrow">Админка</div>
    <h1>Редактор</h1>
    <p class="muted">Паки и карточки, которые видят ученики в «Уроках». Правки видны сразу. У каждого пака и карточки есть автор.</p>
    <div v-if="error" class="flash bad" role="alert">{{ error }}</div>
    <div v-if="note" class="flash ok">{{ note }}</div>

    <div class="actions">
      <RouterLink class="btn p" :to="{ name: 'editor-pack', params: { pid: 'new' } }">+ Новый пак</RouterLink>
      <RouterLink class="btn" :to="{ name: 'editor-lesson', params: { lid: 'new' } }">+ Новая карточка</RouterLink>
    </div>

    <p v-if="!data && !error" class="muted">Загружаю…</p>
    <template v-else-if="data">
      <div class="sec">Паки · порядок как у учеников</div>
      <div class="erows">
        <div v-for="(p, i) in data.packs" :key="p.id" class="erow">
          <span class="n">{{ i + 1 }}</span>
          <div>
            <b>{{ p.title }}</b>
            <span class="sub">{{ p.algos ? p.algos + " алгоритмов" : p.items.filter(x => x.lesson).length + " карточек" }} · автор: {{ p.author }}</span>
          </div>
          <div class="tools">
            <button class="btn s g ib" type="button" :disabled="i === 0" aria-label="Выше" @click="move(i, -1)">↑</button>
            <button class="btn s g ib" type="button" :disabled="i === data.packs.length - 1" aria-label="Ниже" @click="move(i, 1)">↓</button>
            <RouterLink class="btn s p" :to="{ name: 'editor-pack', params: { pid: p.id } }">Править</RouterLink>
            <button class="btn s g" type="button" @click="removePack(p)">Удалить</button>
          </div>
        </div>
      </div>

      <div class="sec">Все карточки · {{ data.lessons.length }}</div>
      <div class="erows">
        <div v-for="(l, i) in data.lessons" :key="l.id" class="erow">
          <span class="n">{{ i + 1 }}</span>
          <div>
            <b>{{ l.title }}</b>
            <span class="sub">{{ l.methods }} методов · {{ l.tag || "без тега" }} · автор: {{ l.author }}{{ l.packs.length ? " · в паке: " + l.packs.join(", ") : " · ни в одном паке" }}</span>
          </div>
          <div class="tools">
            <RouterLink class="btn s p" :to="{ name: 'editor-lesson', params: { lid: l.id } }">Править</RouterLink>
            <button class="btn s g" type="button" @click="removeLesson(l)">Удалить</button>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>
