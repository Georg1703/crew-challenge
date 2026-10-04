/// <reference types="vitest/config" />
import { fileURLToPath, URL } from "node:url";

import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// One origin: the dev server forwards API and admin requests to Django, so session cookies and
// CSRF work exactly as in production behind Caddy. No CORS.
const apiTarget = process.env.VITE_API_PROXY_TARGET ?? "http://localhost:8000";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) },
  },
  server: {
    port: 5173,
    strictPort: true,
    host: true,
    // Allows `make tunnel` (Cloudflare quick tunnel) to reach the dev server.
    allowedHosts: [".trycloudflare.com"],
    proxy: {
      "/api": { target: apiTarget },
      "/admin": { target: apiTarget },
      "/static": { target: apiTarget },
    },
  },
  build: {
    sourcemap: true,
    target: "es2022",
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
    css: { modules: { classNameStrategy: "non-scoped" } },
    include: ["src/**/*.test.{ts,tsx}"],
    restoreMocks: true,
  },
});
