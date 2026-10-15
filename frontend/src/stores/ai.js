import { defineStore } from "pinia";
import { api } from "../api";
import { play } from "../lib/sfx";

// Функция, которая отдаёт текст из поля, где сейчас курсор. В стейте её не держим: это не данные.
let attemptGetter = null;

export const useAi = defineStore("ai", {
  state: () => ({
    open: false,
    busy: false,
    msgs: [], // { role: "user" | "bot", text, cls }
    history: [], // то, что уходит модели: { role, content }
    left: null,
    lesson: "", // урок, который сейчас на экране (ставит LessonListing)
    chatLesson: "", // урок, к которому относится нынешний диалог
    block: "", // метод, в поле которого стоит курсор
    missing: [],
  }),
  actions: {
    focus(block, getter) {
      this.block = block;
      attemptGetter = getter;
    },
    setListing(lesson, missing) {
      this.lesson = lesson;
      this.missing = missing;
    },
    clearListing() {
      this.lesson = "";
      this.block = "";
      this.missing = [];
      attemptGetter = null;
    },
    // Новый урок: старый диалог про другой код только путает модель.
    resetFor(lesson) {
      if (this.chatLesson === lesson) return;
      this.chatLesson = lesson;
      this.msgs = [];
      this.history = [];
    },
    async ask(text, extra) {
      text = (text || "").trim();
      const lesson = (extra && extra.lesson) || this.lesson;
      if (!text || this.busy || !lesson) return;
      this.resetFor(lesson);
      this.open = true;
      this.busy = true;
      this.msgs.push({ role: "user", text });
      const wait = { role: "bot", text: "Думаю…", cls: "typing" };
      this.msgs.push(wait);
      try {
        const ctx = { lesson, block: this.block, attempt: attemptGetter ? attemptGetter() : "", missing: this.missing };
        const body = Object.assign(ctx, extra || {}, { message: text, history: this.history.slice(-6) });
        const r = await api.post("/ai/chat", body);
        this.msgs.splice(this.msgs.indexOf(wait), 1, { role: "bot", text: r.text });
        this.history.push({ role: "user", content: text }, { role: "assistant", content: r.text });
        if (typeof r.left === "number") this.left = r.left;
        play("ok");
      } catch (e) {
        this.msgs.splice(this.msgs.indexOf(wait), 1, { role: "bot", text: e.message, cls: "err" });
        play("err");
      } finally {
        this.busy = false;
      }
    },
  },
});
