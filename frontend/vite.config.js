import vue from "@vitejs/plugin-vue";
import { defineConfig } from "vite";

// В разработке запросы /api идут на Flask (порт 5000), так что CORS не мешает.
export default defineConfig({
  plugins: [vue()],
  server: { port: 5173, proxy: { "/api": "http://127.0.0.1:5000" } },
});
