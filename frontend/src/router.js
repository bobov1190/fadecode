import { createRouter, createWebHistory } from "vue-router";
import { useAuth } from "./stores/auth";

const Soon = () => import("./views/SoonView.vue");

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", name: "home", component: () => import("./views/PacksView.vue"), meta: { auth: true, tab: "home" } },
    { path: "/login", name: "login", component: () => import("./views/AuthView.vue"), meta: { guest: true } },
    { path: "/register", name: "register", component: () => import("./views/AuthView.vue"), meta: { guest: true } },
    { path: "/packs/:pid", name: "pack", component: () => import("./views/PackView.vue"), meta: { auth: true, tab: "home" } },
    { path: "/lessons/:lid", name: "lesson", component: () => import("./views/LessonReadView.vue"), meta: { ai: true, auth: true, tab: "home" } },
    { path: "/lessons/:lid/copy", name: "lesson-copy", component: () => import("./views/LessonCopyView.vue"), meta: { ai: true, auth: true, tab: "home" } },
    { path: "/lessons/:lid/recall", name: "lesson-recall", component: () => import("./views/LessonRecallView.vue"), meta: { ai: true, auth: true, tab: "home" } },
    { path: "/lessons/:lid/done", name: "lesson-done", component: () => import("./views/LessonDoneView.vue"), meta: { auth: true, tab: "home" } },
        { path: "/review", name: "review", component: () => import("./views/ReviewView.vue"), meta: { ai: true, auth: true, tab: "review" } },
        { path: "/stats", name: "stats", component: () => import("./views/StatsView.vue"), meta: { auth: true, tab: "stats" } },
    { path: "/algos/:aid", name: "algo", component: () => import("./views/AlgoView.vue"), meta: { auth: true, tab: "home" } },
    { path: "/problems/:pid", name: "problem", component: () => import("./views/ProblemView.vue"), meta: { ai: true, auth: true, tab: "home" } },
    { path: "/:rest(.*)*", name: "404", component: Soon, props: { title: "Страница не найдена" } },
  ],
  scrollBehavior: () => ({ top: 0 }),
});

router.beforeEach(async to => {
  const a = useAuth();
  if (!a.ready) await a.load();
  if (to.meta.auth && !a.user) return { name: "login" };
  if (to.meta.guest && a.user) return { name: "home" };
});

export default router;
