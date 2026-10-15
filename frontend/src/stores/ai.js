import { defineStore } from "pinia";
import { api } from "../api";
import { play } from "../lib/sfx";

let attemptGetter = null;
let errorGetter = null;

export const useAi = defineStore("ai", {
  state: () => ({
    open: false,
    busy: false,
    msgs: [],
    history: [],
    left: null,
    lesson: "",
    chatLesson: "",
    block: "",
    missing: [],
    problem: "",
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
    setProblem(id, attempt, error) {
      this.problem = id;
      attemptGetter = attempt;
      errorGetter = error;
    },
    clearProblem() {
      this.problem = "";
      attemptGetter = null;
      errorGetter = null;
    },
    resetFor(key) {
      if (this.chatLesson === key) return;
      this.chatLesson = key;
      this.msgs = [];
      this.history = [];
    },
    async ask(text, extra) {
      text = (text || "").trim();
      const prob = this.problem;
      const lesson = (extra && extra.lesson) || this.lesson;
      const key = prob || lesson;
      if (!text || this.busy || !key) return;
      this.resetFor(key);
      this.open = true;
      this.busy = true;
      this.msgs.push({ role: "user", text });
      const wait = { role: "bot", text: "Думаю…", cls: "typing" };
      this.msgs.push(wait);
      try {
        let r;
        if (prob) {
          r = await api.post("/ai/problem", {
            problem: prob,
            attempt: attemptGetter ? attemptGetter() : "",
            error: errorGetter ? errorGetter() : "",
            message: text,
            history: this.history.slice(-6),
          });
        } else {
          const ctx = { lesson, block: this.block, attempt: attemptGetter ? attemptGetter() : "", missing: this.missing };
          const body = Object.assign(ctx, extra || {}, { message: text, history: this.history.slice(-6) });
          r = await api.post("/ai/chat", body);
        }
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
