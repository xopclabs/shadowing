import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import { resolve } from "path";

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      "@": resolve(__dirname, "src"),
    },
  },
  server: {
    host: "0.0.0.0",
    port: parseInt(process.env.FRONTEND_PORT || "8848"),
    // Allow all hosts for homelab development (secure via reverse proxy)
    allowedHosts: true,
    proxy: {
      "/api": {
        target: `http://localhost:${process.env.BACKEND_PORT || "8847"}`,
        changeOrigin: true,
      },
    },
  },
});
