<script setup>
/* Редактор алгоритма: шаблон-карточка, вариации и задачи. Эталон каждой задачи гоняется на её тестах прямо в браузере (Pyodide). */
import { computed, nextTick, onMounted, reactive, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { api } from "../api";
import { runTests } from "../lib/runner";
import { play } from "../lib/sfx";

const route = useRoute();
const router = useRouter();
const isNew = computed(() => route.params.aid === "new");
const error = ref("");
const ready = ref(false);
const busy = ref(false);
const packs = ref([]);
const lessons = ref([]);
const form = reactive({ title: "", tag: "алгоритм", desc: "", pack: "", template: "", variations: [], problems: [] });
// AiMaker для задач: ИИ собирает черновик, браузер проверяет его в Python (эталон должен пройти, заготовка pass должна упасть)
const pm = reactive({ open: true, idea: "", level: "medium", fn: "", num: "", notes: "", busy: false, stage: "", info: "", error: "" });

let seq = 0;
const SKELETON = {
  starter: "class Solution:\n    def solve(self, nums):\n        pass",
  reference: "class Solution:\n    def solve(self, nums):\n        return sum(nums)",
  tests: "def gen(r):\n    return ([r.randint(-9, 9) for _ in range(r.randint(0, 8))],)\n\ndef brute(nums):\n    return sum(nums)\n\ncheck(S, \"solve\", gen, brute)",
};

function blank() {
  return { key: ++seq, id: "", num: "", title: "", level: "easy", fn: "solve", statement: "", examples: "", hints: "",
    starter: SKELETON.starter, reference: SKELETON.reference, insight: "", pre: "", tests: SKELETON.tests, open: true, check: null };
}

function fromServer(p) {
  return { key: ++seq, id: p.id, num: p.num == null ? "" : p.num, title: p.title, level: p.level, fn: p.fn,
    statement: p.statement, examples: p.examples.join("\n"), hints: p.hints.join("\n"), starter: p.starter,
    reference: p.reference, insight: p.insight, pre: p.pre, tests: p.tests, open: false, check: null };
}

const lines = s => String(s || "").split("\n").map(x => x.trim()).filter(Boolean);

onMounted(async () => {
  try {
    const c = await api.get("/admin/content");
    packs.value = c.packs;
    lessons.value = c.lessons;
    if (isNew.value) {
      form.pack = c.packs.length ? c.packs[0].id : "";
      form.template = c.lessons.length ? c.lessons[0].id : "";
      form.problems.push(blank());
    } else {
      const { algo: A } = await api.get("/admin/algos/" + encodeURIComponent(route.params.aid));
      Object.assign(form, { title: A.title, tag: A.tag, desc: A.desc, pack: A.pack, template: A.template, variations: [...A.variations] });
      form.problems = A.problems.map(fromServer);
    }
    ready.value = true;
  } catch (e) {
    error.value = e.message;
  }
});

const rowsOf = s => Math.max(3, Math.min(30, String(s || "").split("\n").length + 1));
const others = computed(() => lessons.value.filter(l => l.id !== form.template));

function onTab(e) {
  const t = e.target;
  t.setRangeText("    ", t.selectionStart, t.selectionEnd, "end");
  t.dispatchEvent(new Event("input"));
}

function toggleVar(id) {
  const i = form.variations.indexOf(id);
  if (i >= 0) form.variations.splice(i, 1);
  else form.variations.push(id);
}

function addProblem() {
  form.problems.push(blank());
  play("ok");
}
function moveProblem(i, d) {
  const j = i + d;
  if (j < 0 || j >= form.problems.length) return;
  [form.problems[i], form.problems[j]] = [form.problems[j], form.problems[i]];
}
function removeProblem(i) {
  const p = form.problems[i];
  if (!confirm("Убрать задачу «" + (p.title || "без названия") + "»? Прогресс учеников по ней пропадёт после сохранения.")) return;
  form.problems.splice(i, 1);
}

async function run(p) {
  p.check = { state: "run", msg: "Запускаю…" };
  const r = await runTests({ code: p.reference, pre: p.pre, tests: p.tests }, s => {
    if (p.check && p.check.state === "run") p.check.msg = s === "loading" ? "Загружаю Python (первый раз около 10 МБ)…" : "Гоняю тесты…";
  });
  p.check = { state: r.status, msg: r.status === "ok" ? "Эталон прошёл все тесты (" + r.count + " проверок)." : r.message };
  play(r.status === "ok" ? "win" : "err");
}

function problemBody(p) {
  return {
    id: p.id, num: p.num === "" ? null : p.num, title: p.title, level: p.level, fn: p.fn, statement: p.statement,
    examples: lines(p.examples), hints: lines(p.hints), starter: p.starter, reference: p.reference,
    insight: p.insight, pre: p.pre, tests: p.tests,
  };
}

// Эталон должен пройти тесты, а пустая заготовка (pass) должна на них упасть: иначе тесты ничего не проверяют.
async function verify(p) {
  pm.stage = "Проверяю эталон в Python…";
  await run(p);
  if (p.check.state !== "ok") return;
  pm.stage = "Проверяю, что заготовка падает…";
  const s = await runTests({ code: p.starter, pre: p.pre, tests: p.tests }, () => {});
  if (s.status === "ok") p.check = { state: "fail", msg: "Заготовка (pass) проходит тесты: они ничего не проверяют. Нажми «Починить через ИИ» или усиль тесты." };
}

async function generateProblem() {
  if (pm.busy || !pm.idea.trim()) return;
  pm.busy = true;
  pm.stage = "Генерирую, это до минуты…";
  pm.info = "";
  pm.error = "";
  try {
    const r = await api.post("/admin/aimaker/problem", {
      idea: pm.idea, level: pm.level, fn: pm.fn, num: pm.num === "" ? null : pm.num, notes: pm.notes,
      template: form.template, topic: form.title, titles: form.problems.map(p => p.title).filter(Boolean),
    });
    const p = Object.assign(fromServer(r.draft), { open: true, warns: r.problems });
    form.problems.push(p);
    pm.idea = "";
    pm.info = "Модель: " + r.model + ". Осталось генераций задач сегодня: " + r.left + ". Новая задача добавлена в конец списка, черновик не сохранён.";
    play(r.problems.length ? "warn" : "ok");
    await nextTick();
    const el = document.getElementById("prob-" + p.key);
    if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });
    await verify(p);
  } catch (e) {
    pm.error = e.message; // ошибку показываем под кнопкой, а не наверху страницы, где её не видно
    play("err");
  } finally {
    pm.busy = false;
  }
}

async function fixProblem(p) {
  if (pm.busy || !p.check || (p.check.state !== "fail" && p.check.state !== "error")) return;
  pm.busy = true;
  pm.stage = "ИИ чинит задачу, это до минуты…";
  pm.error = "";
  try {
    const r = await api.post("/admin/aimaker/problem", {
      fix: { draft: problemBody(p), error: p.check.msg }, idea: p.title, level: p.level, fn: p.fn,
      template: form.template, topic: form.title,
    });
    const n = fromServer(r.draft);
    Object.assign(p, { title: n.title, fn: n.fn, statement: n.statement, examples: n.examples, hints: n.hints,
      starter: n.starter, reference: n.reference, insight: n.insight, pre: n.pre, tests: n.tests, warns: r.problems, check: null });
    pm.info = "Исправлено моделью " + r.model + ". Осталось генераций задач сегодня: " + r.left + ".";
    await verify(p);
  } catch (e) {
    p.warns = [e.message];
    play("err");
  } finally {
    pm.busy = false;
  }
}

function bodyOf() {
  return {
    title: form.title, tag: form.tag, desc: form.desc, pack: form.pack, template: form.template, variations: form.variations,
    problems: form.problems.map(problemBody),
  };
}

async function save() {
  if (busy.value) return;
  const unchecked = form.problems.filter(p => !p.check || p.check.state !== "ok");
  if (unchecked.length && !confirm("Эталон не прогнан или не прошёл у задач: " + unchecked.map(p => "«" + (p.title || "без названия") + "»").join(", ") + ". Сохранить всё равно?")) return;
  busy.value = true;
  error.value = "";
  try {
    if (isNew.value) await api.post("/admin/algos", bodyOf());
    else await api.put("/admin/algos/" + encodeURIComponent(route.params.aid), bodyOf());
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
    <h1>{{ isNew ? "Новый алгоритм" : "Правка алгоритма" }}</h1>
    <p class="muted">Алгоритм = шаблон (карточка, которую учат наизусть) плюс задачи на него. Тесты исполняются в браузере: сначала «Прогнать эталон», потом сохраняй.</p>
    <div v-if="error" class="flash bad" role="alert">{{ error }}</div>
    <p v-if="!ready && !error" class="muted">Загружаю…</p>

    <form v-if="ready" class="aform eform" @submit.prevent="save">
      <label>Название<input v-model="form.title" required maxlength="120" placeholder="Например, Скользящее окно"></label>
      <div class="two">
        <label>Тег<input v-model="form.tag" maxlength="80"></label>
        <label>Пак
          <select v-model="form.pack"><option v-for="p in packs" :key="p.id" :value="p.id">{{ p.title }}</option></select>
        </label>
      </div>
      <label>Короткое описание<input v-model="form.desc" maxlength="600"></label>
      <label>Шаблон (карточка, которую ученик учит перед задачами)
        <select v-model="form.template"><option v-for="l in lessons" :key="l.id" :value="l.id">{{ l.title }}</option></select>
      </label>
      <div>
        <div class="eyebrow">Вариации шаблона (необязательно)</div>
        <label v-for="l in others" :key="l.id" style="display:flex;gap:8px;align-items:center;margin-top:6px">
          <input type="checkbox" :checked="form.variations.includes(l.id)" @change="toggleVar(l.id)"> {{ l.title }}
        </label>
      </div>

      <div class="eyebrow">Задачи ({{ form.problems.length }})</div>

      <div v-for="(p, i) in form.problems" :id="'prob-' + p.key" :key="p.key" class="eblock">
        <div class="ehead">
          <span class="num">{{ i + 1 }}</span>
          <input v-model="p.title" class="grow" required maxlength="120" placeholder="Название задачи">
          <span v-if="p.check" :class="p.check.state === 'ok' ? 'g-good' : p.check.state === 'run' ? 'muted' : 'g-again'">{{ p.check.state === "ok" ? "✓" : p.check.state === "run" ? "…" : "✕" }}</span>
          <button class="btn s g" type="button" @click="p.open = !p.open">{{ p.open ? "Свернуть" : "Открыть" }}</button>
          <button class="btn s g ib" type="button" :disabled="i === 0" aria-label="Выше" @click="moveProblem(i, -1)">↑</button>
          <button class="btn s g ib" type="button" :disabled="i === form.problems.length - 1" aria-label="Ниже" @click="moveProblem(i, 1)">↓</button>
          <button class="btn s g ib" type="button" aria-label="Убрать задачу" @click="removeProblem(i)">✕</button>
        </div>
        <template v-if="p.open">
          <div v-for="(w, wi) in (p.warns || [])" :key="wi" class="flash bad" role="alert">{{ w }}</div>
          <div class="two">
            <label>Сложность
              <select v-model="p.level"><option value="easy">easy</option><option value="medium">medium</option><option value="hard">hard</option></select>
            </label>
            <label>Номер (LeetCode, необязательно)<input v-model="p.num" type="number" min="0"></label>
          </div>
          <label>Метод решения (fn)<input v-model="p.fn" class="mono" maxlength="40" spellcheck="false" @input="p.check = null"></label>
          <label>Условие<textarea v-model="p.statement" rows="4" maxlength="4000"></textarea></label>
          <label>Примеры (по одному на строку)<textarea v-model="p.examples" rows="3" spellcheck="false"></textarea></label>
          <label>Подсказки (по одной на строку, до 5)<textarea v-model="p.hints" rows="3"></textarea></label>
          <label>Заготовка для ученика (class Solution с методом fn)
            <textarea v-model="p.starter" class="mono" :rows="rowsOf(p.starter)" spellcheck="false" @keydown.tab.prevent="onTab"></textarea>
          </label>
          <label>Эталонное решение
            <textarea v-model="p.reference" class="mono" :rows="rowsOf(p.reference)" spellcheck="false" @input="p.check = null" @keydown.tab.prevent="onTab"></textarea>
          </label>
          <label>Тесты (используют gen, brute, check; см. существующие задачи)
            <textarea v-model="p.tests" class="mono" :rows="rowsOf(p.tests)" spellcheck="false" @input="p.check = null" @keydown.tab.prevent="onTab"></textarea>
          </label>
          <label>Код перед тестами (pre, необязательно: например ListNode)
            <textarea v-model="p.pre" class="mono" :rows="rowsOf(p.pre)" spellcheck="false" @input="p.check = null" @keydown.tab.prevent="onTab"></textarea>
          </label>
          <label>Разбор «в чём идея» (показывается после решения)<textarea v-model="p.insight" rows="3" maxlength="2000"></textarea></label>
          <div class="row">
            <button class="btn s" type="button" :disabled="p.check && p.check.state === 'run'" @click="run(p)">Прогнать эталон</button>
            <button v-if="p.check && (p.check.state === 'fail' || p.check.state === 'error')" class="btn s" type="button" :disabled="pm.busy" @click="fixProblem(p)">Починить через ИИ</button>
            <span v-if="p.check" :class="p.check.state === 'ok' ? 'g-good' : 'g-again'" style="white-space:pre-wrap">{{ p.check.msg }}</span>
          </div>
        </template>
      </div>

      <div class="eblock">
        <div class="ehead">
          <span class="num">AI</span>
          <strong class="grow">AiMaker: ИИ соберёт задачу на этот шаблон</strong>
          <button class="btn s g" type="button" @click="pm.open = !pm.open">{{ pm.open ? "Свернуть" : "Развернуть" }}</button>
        </div>
        <template v-if="pm.open">
          <p class="muted" style="margin:0">ИИ напишет условие, эталон, заготовку, подсказки и тесты. Потом браузер сам проверит: эталон должен пройти тесты, а заготовка с pass должна упасть. Если что-то не так, появится кнопка «Починить через ИИ».</p>
          <label>Идея задачи<input v-model="pm.idea" maxlength="600" placeholder="Например, LeetCode 121: лучшее время для покупки акций"></label>
          <div class="two">
            <label>Сложность
              <select v-model="pm.level"><option value="easy">easy</option><option value="medium">medium</option><option value="hard">hard</option></select>
            </label>
            <label>Метод (fn, необязательно)<input v-model="pm.fn" class="mono" maxlength="40" spellcheck="false" placeholder="maxProfit"></label>
          </div>
          <div class="two">
            <label>Номер LeetCode (необязательно)<input v-model="pm.num" type="number" min="0"></label>
            <label>Пожелания (необязательно)<input v-model="pm.notes" maxlength="600" placeholder="Например, упор на крайние случаи"></label>
          </div>
          <div>
            <button class="btn p" type="button" :disabled="pm.busy || !pm.idea.trim()" @click="generateProblem">
              {{ pm.busy ? pm.stage : "Сгенерировать задачу" }}
            </button>
          </div>
          <div v-if="pm.error" class="flash bad" role="alert" style="margin:0">{{ pm.error }}</div>
          <p v-if="pm.info" class="muted" style="margin:0">{{ pm.info }}</p>
        </template>
      </div>

      <div><button class="btn" type="button" @click="addProblem">+ Задача</button></div>

      <div class="actions" style="margin-top:0">
        <button class="btn p" type="submit" :disabled="busy">Сохранить</button>
        <RouterLink class="btn g" :to="{ name: 'editor' }">Отмена</RouterLink>
      </div>
    </form>
  </div>
</template>
