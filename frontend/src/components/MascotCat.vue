<script>
// Счётчик для уникальных id градиентов: на странице может быть несколько котов сразу (кнопка и шапка панели).
let counter = 0;
</script>

<script setup>
/* Маскот Fadecode: кот из присланного SVG, перекрашен в палитру проекта (зелёные --g и --g2).
   С alive изредка косится на урок (зрачки вверх-влево) и моргает; интервалы случайные. */
import { onBeforeUnmount, onMounted, ref } from "vue";

const props = defineProps({ shadow: Boolean, alive: Boolean });
const id = "cat" + ++counter;
const looking = ref(false);
const blinking = ref(false);
const timers = new Set();

const rnd = (a, b) => a + Math.random() * (b - a);
function later(fn, ms) {
  const t = setTimeout(() => { timers.delete(t); fn(); }, ms);
  timers.add(t);
}

function glance() {
  if (!document.hidden) {
    looking.value = true;
    later(() => { looking.value = false; }, rnd(1400, 2600));
  }
  later(glance, rnd(9000, 20000));
}

function blink() {
  const once = () => { blinking.value = true; later(() => { blinking.value = false; }, 130); };
  if (!document.hidden) {
    once();
    if (Math.random() < 0.2) later(once, 280); // иногда моргает дважды
  }
  later(blink, rnd(3500, 8000));
}

onMounted(() => {
  if (!props.alive || window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
  later(glance, rnd(3000, 7000));
  later(blink, rnd(2000, 5000));
});
onBeforeUnmount(() => { timers.forEach(clearTimeout); timers.clear(); });
</script>

<template>
  <svg class="cat" :class="{ look: looking, blink: blinking }" viewBox="30 225 622 520" xmlns="http://www.w3.org/2000/svg" aria-hidden="true" focusable="false">
    <defs>
      <linearGradient :id="id + 'h'" x1="0%" y1="0%" x2="0%" y2="100%">
        <stop offset="0%" stop-color="#4c8736" />
        <stop offset="35%" stop-color="#5d9c42" />
        <stop offset="70%" stop-color="#72b254" />
        <stop offset="100%" stop-color="#86c765" />
      </linearGradient>
      <linearGradient :id="id + 'e'" x1="0%" y1="0%" x2="0%" y2="100%">
        <stop offset="0%" stop-color="#cdeeb8" />
        <stop offset="100%" stop-color="#a3d884" />
      </linearGradient>
      <linearGradient :id="id + 'p'" x1="0%" y1="0%" x2="0%" y2="100%">
        <stop offset="0%" stop-color="#14290f" />
        <stop offset="100%" stop-color="#2f5522" />
      </linearGradient>
      <radialGradient :id="id + 's'" cx="50%" cy="50%" r="50%">
        <stop offset="0%" stop-color="rgba(134, 199, 101, 0.20)" />
        <stop offset="60%" stop-color="rgba(134, 199, 101, 0.05)" />
        <stop offset="100%" stop-color="rgba(134, 199, 101, 0)" />
      </radialGradient>
    </defs>

    <ellipse v-if="shadow" cx="341" cy="745" rx="205" ry="24" :fill="'url(#' + id + 's)'" />

    <path d="M 160,255 C 112,275 95,435 95,535 C 95,665 200,732 341,732 C 482,732 587,665 587,535 C 587,435 570,295 522,285 C 475,275 430,368 375,368 C 320,368 210,235 160,255 Z"
          :fill="'url(#' + id + 'h)'" />
    <path d="M 182,300 C 156,332 150,408 188,422 C 218,408 218,348 182,300 Z" :fill="'url(#' + id + 'e)'" />
    <path d="M 520,335 C 540,362 538,428 506,438 C 483,423 488,368 520,335 Z" :fill="'url(#' + id + 'e)'" />

    <g class="eyes">
      <ellipse cx="218" cy="552" rx="85" ry="100" fill="#ffffff" />
      <g class="pupil"><ellipse cx="232" cy="556" rx="40" ry="67" :fill="'url(#' + id + 'p)'" /></g>
      <ellipse cx="464" cy="552" rx="85" ry="100" fill="#ffffff" />
      <g class="pupil"><ellipse cx="450" cy="556" rx="40" ry="67" :fill="'url(#' + id + 'p)'" /></g>
    </g>

    <g transform="translate(64, 612) rotate(-21)"><rect x="-22.5" y="-10.5" width="45" height="21" rx="10.5" fill="#5d9c42" /></g>
    <g transform="translate(73, 658) rotate(-41)"><rect x="-29.7" y="-11.5" width="59.5" height="23" rx="11.5" fill="#6aa94b" /></g>
    <g transform="translate(614, 612) rotate(21)"><rect x="-22.5" y="-10.5" width="45" height="21" rx="10.5" fill="#5d9c42" /></g>
    <g transform="translate(606, 658) rotate(41)"><rect x="-29.7" y="-11.5" width="59.5" height="23" rx="11.5" fill="#6aa94b" /></g>
  </svg>
</template>

<style scoped>
.eyes { transform-box: fill-box; transform-origin: center; transition: transform .07s; }
.blink .eyes { transform: scaleY(.08); }
.pupil { transition: transform .32s cubic-bezier(.3, .7, .3, 1); }
.look .pupil { transform: translate(-27px, -23px); }
</style>
