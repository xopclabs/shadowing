import { createApp } from "vue";
import { createPinia } from "pinia";
import { registerSW } from "virtual:pwa-register";
import App from "./App.vue";
import router from "./router";
import "./style.css";

// Register service worker for PWA
const updateSW = registerSW({
  onNeedRefresh() {
    // Show a prompt to user about new content available
    if (confirm("New content available. Reload?")) {
      updateSW(true);
    }
  },
  onOfflineReady() {
    console.log("App ready to work offline");
  },
});

const app = createApp(App);

app.use(createPinia());
app.use(router);

app.mount("#app");
