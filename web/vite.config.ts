import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// During `npm run dev`, proxy API + websocket to a running node service so the
// SPA can call /api/... and /ws exactly as it will in production (same-origin).
const NODE_TARGET = process.env.USBIP_NODE_DEV_TARGET ?? "http://127.0.0.1:4820";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      "/api": NODE_TARGET,
      "/health": NODE_TARGET,
      "/ws": { target: NODE_TARGET, ws: true },
    },
  },
  build: {
    outDir: "dist",
  },
});
