import { defineStore } from "pinia";
import { api, hooks, tokenStore } from "../api";

export const useAuth = defineStore("auth", {
  state: () => ({ token: tokenStore.get(), user: null, due: 0, ready: false }),
  actions: {
    async load() {
      if (this.token) {
        try {
          const r = await api.get("/me");
          this.user = r.user;
          this.due = r.due;
        } catch (e) {
          if (e.status === 401) this.drop();
        }
      }
      this.ready = true;
    },
    async enter(path, username, password, name) {
      const r = await api.auth(path, name ? { username, password, name } : { username, password });
      this.token = r.token;
      tokenStore.set(r.token);
      this.user = r.user;
      await this.refreshDue();
    },
    login(u, p) { return this.enter("/auth/login", u, p); },
    register(u, p, name) { return this.enter("/auth/register", u, p, name); },
    async refreshDue() {
      try { this.due = (await api.get("/me")).due; } catch (e) { /* счётчик не критичен */ }
    },
    drop() {
      this.token = "";
      this.user = null;
      this.due = 0;
      tokenStore.set("");
    },
  },
});

export function bindUnauthorized(router) {
  hooks.onUnauthorized = () => {
    const a = useAuth();
    if (!a.token) return;
    a.drop();
    router.push({ name: "login" });
  };
}
