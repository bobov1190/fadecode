<script setup>
import { onMounted, ref } from "vue";
import { api } from "../api";
import { useAuth } from "../stores/auth";

const auth = useAuth();
const packs = ref(null);

// Почему это работает: короткие мысли из когнитивной психологии. Показывается одна, кнопка листает дальше.
const THOUGHTS = [
  { t: "Кривая забывания круто падает в первые часы и дни: без возвращения к материалу след памяти истончается быстрее, чем кажется. Повторение работает не как перечитывание, а как реставрация, и каждое возвращение делает след прочнее.", src: "Г. Эббингауз, «О памяти», 1885" },
  { t: "Вспоминать труднее, чем перечитывать, и именно поэтому запоминается лучше: само извлечение из памяти укрепляет след. Потому здесь методы исчезают, а не подсвечиваются.", src: "Х. Роедигер, Дж. Карпике, 2006" },
  { t: "Усилие, которое кажется помехой, на деле работает как механизм. Призрачный текст держит руку, пустое поле отнимает опору, и мы убираем её по одному методу за раунд.", src: "Р. Бьорк, «желательные трудности», 1994" },
  { t: "Рабочая память вмещает порядка семи единиц, но единицей может быть всё осмысленное. Выучи шаблон бинарного поиска, и left <= right перестанет быть тремя символами и станет одной мыслью.", src: "Дж. Миллер, 1956" },
  { t: "Сделанное самим запоминается прочнее прочитанного. Поэтому решение не показывается, пока ты сам о нём не попросишь.", src: "Н. Сламецка, П. Граф, 1978" },
];
const thought = ref(Math.floor(Math.random() * THOUGHTS.length));
const nextThought = () => { thought.value = (thought.value + 1) % THOUGHTS.length; };
const error = ref("");

onMounted(async () => {
  try {
    const r = await api.get("/packs");
    packs.value = r.packs;
    auth.due = r.due;
  } catch (e) {
    error.value = e.message;
  }
});
</script>

<template>
  <div>
    <div class="eyebrow">Уроки</div>
    <h1>Выбери пак</h1>
    <p class="muted">Каждый урок: копирование поверх призрака, потом методы пропадают, и ты вспоминаешь их по памяти.</p>
    <div v-if="error" class="flash bad" role="alert">{{ error }}</div>
    <p v-else-if="!packs" class="muted" style="margin-top:28px">Загружаю…</p>
    <div v-else class="grid">
      <RouterLink v-for="p in packs" :key="p.id" class="card" :to="{ name: 'pack', params: { pid: p.id } }">
        <span class="tag">{{ p.total }} тем</span>
        <h3>{{ p.title }}</h3>
        <p>{{ p.desc }}</p>
        <span v-if="p.author" class="by">Автор: {{ p.author }}</span>
        <span class="meta">
          <span>готово к изучению: {{ p.ready }}</span>
          <span :class="{ ok: p.finished }">пройдено: {{ p.finished }}/{{ p.total }}</span>
        </span>
      </RouterLink>
    </div>
    <aside class="epi">
      <div class="eyebrow">Почему это работает</div>
      <blockquote>{{ THOUGHTS[thought].t }}</blockquote>
      <cite>{{ THOUGHTS[thought].src }}</cite>
      <button class="linkbtn" type="button" @click="nextThought">Другая мысль →</button>
    </aside>
  </div>
</template>
