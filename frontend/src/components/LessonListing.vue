<script setup>
/* Листинг класса: целые методы показаны, пропавшие заменены полем ввода. */
import { onBeforeUnmount, onMounted } from "vue";
import SlotBox from "./SlotBox.vue";
import { highlight, indent } from "../lib/core";
import { useAi } from "../stores/ai";

const props = defineProps({
  L: { type: Object, required: true },
  missing: { type: Array, default: () => [] },
  whole: Boolean,
  mode: { type: String, default: "recall" },
});
defineEmits(["resolved"]);

const ai = useAi();
onMounted(() => ai.setListing(props.L.id, props.whole ? [] : props.missing));
onBeforeUnmount(() => ai.clearListing());

const firstId = (props.L.blocks.find(b => props.missing.includes(b.id)) || {}).id;

function label(id) {
  if (props.missing.length <= 1) return "ПРОПАЛ МЕТОД";
  return props.missing[props.missing.length - 1] === id ? "НОВЫЙ ПРОПАВШИЙ МЕТОД" : "ПРОПАЛ РАНЬШЕ, ВСПОМНИ СНОВА";
}
</script>

<template>
  <div>
    <pre class="code" v-html="highlight(L.imports)"></pre><div class="gap"></div>
    <SlotBox v-if="whole" :lesson="L.id" bid="whole" whole :rows="L.rows_whole" :mode="mode" autofocus
             @resolved="e => $emit('resolved', e)" />
    <template v-else>
      <pre class="code" v-html="highlight(L.cls)"></pre>
      <template v-for="b in L.blocks" :key="b.id">
        <SlotBox v-if="missing.includes(b.id)" :lesson="L.id" :bid="b.id" :rows="b.rows" :label="label(b.id)"
                 :mode="mode" :why="b.why" :autofocus="firstId === b.id" @resolved="e => $emit('resolved', e)" />
        <pre v-else class="code" v-html="highlight(indent(b.code))"></pre>
        <div class="gap"></div>
      </template>
    </template>
  </div>
</template>
