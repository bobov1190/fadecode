import { defineStore } from "pinia";
import { api } from "../api";

// Идущее задание с таймером. Время считает сервер (дедлайн), клиент только показывает остаток.
export const useAssign = defineStore("assign", {
  state: () => ({ active: null, offset: 0, left: 0, over: false }),
  actions: {
    async load() {
      try {
        const r = await api.get("/assign/active");
        this.offset = r.now - Date.now();
        this.active = r.active;
        this.over = false;
        this.tick();
      } catch (e) { /* таймер не критичен для остальных экранов */ }
    },
    tick() {
      if (!this.active) { this.left = 0; return; }
      this.left = Math.max(0, Math.ceil((this.active.deadline - (Date.now() + this.offset)) / 1000));
      if (this.left === 0) this.over = true;
    },
    clear() {
      this.active = null;
      this.over = false;
      this.left = 0;
    },
  },
});
