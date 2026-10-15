import { createPinia } from "pinia";
import { createApp } from "vue";
import App from "./App.vue";
import { installClickSounds } from "./lib/sfx";
import router from "./router";
import { bindUnauthorized } from "./stores/auth";
import "./styles/style.css";
import "./styles/extra.css";
import "./styles/spa.css";

const app = createApp(App);
app.use(createPinia());
app.use(router);
bindUnauthorized(router);
installClickSounds();
app.mount("#root");
