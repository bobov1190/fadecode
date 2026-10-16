<script setup>
/* Форма карточки: поля урока, методы по порядку, вопрос «зачем так» у каждого метода, живой предпросмотр кода. */
import { computed, onMounted, reactive, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { api } from "../api";
import { highlight, indent } from "../lib/core";
import { play } from "../lib/sfx";

const route = useRoute();
const router = useRouter();
const isNew = computed(() => route.params.lid === "new");
const packId = computed(() => (typeof route.query.pack === "string" ? route.query.pack : ""));
const error = ref("");
const ready = ref(false);
const busy = ref(false);
const form = reactive({ title: "", tag: "", desc: "", task: "", change: "", imports: "import numpy as np", cls: "class MyModel:", author: "", blocks: [] });

let seq = 0;
const blank = () => ({ key: ++seq, id: "", name: "", note: "", code: "", q: "", opts: ["", ""], ok: 0, exp: "", open: false });

function fromServer(b) {
  const w = b.why || {};
  const opts = w.opts && w.opts.length ? [...w.opts] : ["", ""];
  return { key: ++seq, id: b.id, name: b.name, note: b.note, code: b.code, q: w.q || "", opts, ok: w.ok || 0, exp: w.exp || "", open: !!w.q };
}

onMounted(async () => {
  try {
    if (isNew.value) {
      form.blocks.push(blank());
    } else {
      const { lesson: L } = await api.get("/admin/lessons/" + encodeURIComponent(route.params.lid));
      Object.assign(form, { title: L.title, tag: L.tag, desc: L.desc, task: L.task, change: L.change, imports: L.imports, cls: L.cls, author: L.author });
      form.blocks = L.blocks.map(fromServer);
    }
    ready.value = true;
  } catch (e) {
    error.value = e.message;
  }
});

// ---------- AiMaker: ИИ собирает черновик, ничего не сохраняет ----------
const maker = reactive({ open: isNew.value, topic: "", goal: "", stack: "Python", level: "medium", n_methods: 3, notes: "", busy: false, problems: [], info: "" });

async function generate() {
  if (maker.busy) return;
  const hasWork = form.title || form.blocks.some(b => b.name || b.code);
  if (hasWork && !confirm("Форма уже заполнена. Заменить её черновиком от ИИ?")) return;
  maker.busy = true;
  maker.problems = [];
  maker.info = "";
  error.value = "";
  try {
    const r = await api.post("/admin/aimaker/lesson", {
      topic: maker.topic, goal: maker.goal, stack: maker.stack, level: maker.level, n_methods: maker.n_methods, notes: maker.notes,
    });
    const D = r.draft;
    Object.assign(form, { title: D.title, tag: D.tag, desc: D.desc, task: D.task, imports: D.imports, cls: D.cls || form.cls });
    form.blocks = D.blocks.length ? D.blocks.map(fromServer) : [blank()];
    maker.problems = r.problems;
    maker.info = "Модель: " + r.model + ". Осталось генераций сегодня: " + r.left + ". Проверь черновик и нажми «Сохранить».";
    play(r.problems.length ? "warn" : "win");
  } catch (e) {
    error.value = e.message;
    play("err");
  } finally {
    maker.busy = false;
  }
}

const rowsOf = s => Math.max(3, String(s || "").split("\n").length + 1);
const preview = computed(() => {
  const body = form.cls + "\n" + form.blocks.map(b => indent(b.code || "")).join("\n\n");
  return highlight(form.imports + "\n\n\n" + body);
});

function onTab(e) {
  const t = e.target;
  t.setRangeText("    ", t.selectionStart, t.selectionEnd, "end");
  t.dispatchEvent(new Event("input"));
}

function addBlock() {
  const b = blank();
  b.open = false;
  form.blocks.push(b);
  play("ok");
}
function moveBlock(i, d) {
  const j = i + d;
  if (j < 0 || j >= form.blocks.length) return;
  [form.blocks[i], form.blocks[j]] = [form.blocks[j], form.blocks[i]];
}
function removeBlock(i) {
  if (form.blocks.length === 1) return;
  const b = form.blocks[i];
  if ((b.name || b.code) && !confirm("Убрать метод «" + (b.name || "без имени") + "»?")) return;
  form.blocks.splice(i, 1);
}
function addOpt(b) {
  if (b.opts.length < 6) b.opts.push("");
}
function removeOpt(b, oi) {
  if (b.opts.length <= 2) return;
  b.opts.splice(oi, 1);
  if (b.ok === oi) b.ok = 0;
  else if (b.ok > oi) b.ok--;
}

function whyOf(b) {
  const opts = b.opts.map(o => o.trim());
  if (!b.q.trim() && opts.every(o => !o)) return { q: "", opts: [], ok: 0, exp: "" };
  return { q: b.q, opts, ok: b.ok, exp: b.exp };
}

async function save() {
  if (busy.value) return;
  busy.value = true;
  error.value = "";
  const body = {
    title: form.title, tag: form.tag, desc: form.desc, task: form.task, change: form.change,
    imports: form.imports, cls: form.cls, author: form.author,
    blocks: form.blocks.map(b => ({ id: b.id, name: b.name, note: b.note, code: b.code, why: whyOf(b) })),
  };
  try {
    if (isNew.value) await api.post("/admin/lessons", Object.assign(body, packId.value ? { pack: packId.value } : {}));
    else await api.put("/admin/lessons/" + encodeURIComponent(route.params.lid), body);
    play("win");
    router.push(packId.value ? { name: "editor-pack", params: { pid: packId.value } } : { name: "editor" });
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
    <h1>{{ isNew ? "Новая карточка" : "Правка карточки" }}</h1>
    <p v-if="!isNew && ready" class="by"><RouterLink class="crumb" :to="{ name: 'lesson', params: { lid: route.params.lid } }">открыть как ученик</RouterLink></p>
    <div v-if="error" class="flash bad" role="alert">{{ error }}</div>
    <p v-if="!ready && !error" class="muted">Загружаю…</p>

    <form v-if="ready" class="aform eform" @submit.prevent="save">
      <div class="eblock">
        <div class="ehead">
          <span class="num">AI</span>
          <strong class="grow">AiMaker: ИИ соберёт черновик карточки</strong>
          <button class="btn s g" type="button" @click="maker.open = !maker.open">{{ maker.open ? "Свернуть" : "Развернуть" }}</button>
        </div>
        <template v-if="maker.open">
          <label>Тема или алгоритм<input v-model="maker.topic" maxlength="200" placeholder="Например, Стек: монотонный стек"></label>
          <label>Что должен уметь написать ученик<input v-model="maker.goal" maxlength="400" placeholder="Например, находить следующий больший элемент за O(n)"></label>
          <div class="two">
            <label>Язык и библиотеки<input v-model="maker.stack" maxlength="120"></label>
            <label>Сложность
              <select v-model="maker.level"><option value="easy">easy</option><option value="medium">medium</option><option value="hard">hard</option></select>
            </label>
          </div>
          <div class="two">
            <label>Сколько методов (1-6)<input v-model.number="maker.n_methods" type="number" min="1" max="6"></label>
            <label>Пожелания (необязательно)<input v-model="maker.notes" maxlength="600" placeholder="Например, упор на крайние случаи"></label>
          </div>
          <div>
            <button class="btn p" type="button" :disabled="maker.busy || !maker.topic.trim() || !maker.goal.trim()" @click="generate">
              {{ maker.busy ? "Генерирую, это до минуты…" : "Сгенерировать" }}
            </button>
          </div>
          <p v-if="maker.info" class="muted">{{ maker.info }}</p>
          <div v-for="(p, i) in maker.problems" :key="i" class="flash bad" role="alert">{{ p }}</div>
        </template>
      </div>

      <label>Название<input v-model="form.title" required maxlength="120" placeholder="Например, Бинарный поиск: границы"></label>
      <div class="two">
        <label>Тег<input v-model="form.tag" maxlength="80" placeholder="основы, графы…"></label>
        <label>Автор<input v-model="form.author" maxlength="60" :placeholder="isNew ? 'Если пусто, подставится твоё имя' : ''"></label>
      </div>
      <label>Короткое описание<input v-model="form.desc" maxlength="600"></label>
      <label>Задача (что нужно реализовать)<textarea v-model="form.task" rows="3" maxlength="3000"></textarea></label>
      <label>«Что изменилось» (необязательно, для вариаций)<textarea v-model="form.change" rows="2" maxlength="3000"></textarea></label>
      <label>Импорты<textarea v-model="form.imports" class="mono" :rows="rowsOf(form.imports)" spellcheck="false" @keydown.tab.prevent="onTab"></textarea></label>
      <label>Строка класса<input v-model="form.cls" class="mono" required maxlength="160" spellcheck="false" placeholder="class Solution:"></label>

      <div class="eyebrow">Методы по порядку ({{ form.blocks.length }}). Именно они будут пропадать при вспоминании.</div>

      <div v-for="(b, i) in form.blocks" :key="b.key" class="eblock">
        <div class="ehead">
          <span class="num">{{ i + 1 }}</span>
          <input v-model="b.name" class="grow" required maxlength="60" placeholder="Имя метода, например fit">
          <button class="btn s g ib" type="button" :disabled="i === 0" aria-label="Выше" @click="moveBlock(i, -1)">↑</button>
          <button class="btn s g ib" type="button" :disabled="i === form.blocks.length - 1" aria-label="Ниже" @click="moveBlock(i, 1)">↓</button>
          <button class="btn s g ib" type="button" :disabled="form.blocks.length === 1" aria-label="Убрать метод" @click="removeBlock(i)">✕</button>
        </div>
        <label>Что делает (пояснение в разборе)<input v-model="b.note" maxlength="600"></label>
        <label>Код метода (с def, без отступа слева)
          <textarea v-model="b.code" class="mono" required :rows="rowsOf(b.code)" spellcheck="false" maxlength="8000"
                    placeholder="def fit(self, X, y):&#10;    ..." @keydown.tab.prevent="onTab"></textarea>
        </label>

        <button class="btn s g" type="button" style="justify-self:start" @click="b.open = !b.open">
          {{ b.open ? "Скрыть вопрос «Зачем так?»" : "Вопрос «Зачем так?»" + (b.q ? " ✓" : " (необязательно)") }}
        </button>
        <template v-if="b.open">
          <label>Вопрос<input v-model="b.q" maxlength="400"></label>
          <div>
            <div class="eyebrow">Варианты ответа: отметь верный</div>
            <div v-for="(o, oi) in b.opts" :key="oi" class="eopt" style="margin-top:8px">
              <input v-model.number="b.ok" type="radio" :name="'ok' + b.key" :value="oi" :aria-label="'Верный вариант ' + (oi + 1)">
              <input v-model="b.opts[oi]" type="text" maxlength="400" :placeholder="'Вариант ' + (oi + 1)">
              <button class="btn s g ib" type="button" :disabled="b.opts.length <= 2" aria-label="Убрать вариант" @click="removeOpt(b, oi)">✕</button>
            </div>
            <button class="btn s g" type="button" style="margin-top:8px" :disabled="b.opts.length >= 6" @click="addOpt(b)">+ Вариант</button>
          </div>
          <label>Пояснение после ответа<textarea v-model="b.exp" rows="2" maxlength="1200"></textarea></label>
        </template>
      </div>

      <div><button class="btn" type="button" @click="addBlock">+ Метод</button></div>

      <div>
        <div class="eyebrow">Так увидят код ученики</div>
        <div class="codebox preview"><pre class="code" v-html="preview"></pre></div>
      </div>

      <div class="actions" style="margin-top:0">
        <button class="btn p" type="submit" :disabled="busy">Сохранить</button>
        <RouterLink class="btn g" :to="packId ? { name: 'editor-pack', params: { pid: packId } } : { name: 'editor' }">Отмена</RouterLink>
      </div>
    </form>
  </div>
</template>
