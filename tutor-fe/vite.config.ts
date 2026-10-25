import react from "@vitejs/plugin-react";
import path from "node:path";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { "@": path.resolve(__dirname, "./src") },
  },
  server: {
    port: 5173,
    proxy: {
      // Same-origin in the browser, so the WebSocket upgrade for
      // /api/conversations/{id}/live rides through here too (ws: true).
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
        ws: true,
      },
    },
  },
});
