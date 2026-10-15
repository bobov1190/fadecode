import { defineStore } from "pinia";
import { api } from "../api";

// Текущий урок живёт в сторе между этапами (разбор, копирование, вспоминание, итоги).
export const useLesson = defineStore("lesson", {
  state: () => ({ id: null, L: null, order: [], settings: { order: "small", rounds: "all" }, grades: {} }),
  actions: {
    async load(lid) {
      if (this.id === lid && this.L) return;
      this.L = null;
      this.L = await api.get("/lessons/" + encodeURIComponent(lid));
      this.id = lid;
      this.order = [];
      this.grades = {};
    },
    // Новое прохождение: свежий порядок методов и пустые оценки (как открытие урока на старом сайте).
    async begin(lid) {
      this.id = null;
      await this.load(lid);
      await this.shuffle();
      this.grades = {};
    },
    async shuffle() {
      const r = await api.post("/lessons/" + encodeURIComponent(this.id) + "/open");
      this.order = r.order;
      this.settings = r.settings;
    },
    // Зашли сразу на копирование или вспоминание: порядок ещё не выбран.
    async ensure(lid) {
      await this.load(lid);
      if (!this.order.length) await this.shuffle();
    },
    grade(bid, g) {
      if (!(bid in this.grades)) this.grades[bid] = g;
    },
  },
});
