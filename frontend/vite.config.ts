/// <reference types="vitest/config" />
import { fileURLToPath, URL } from "node:url";

import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";
import { VitePWA } from "vite-plugin-pwa";

// One origin: the dev server forwards API and admin requests to Django, so session cookies and
// CSRF work exactly as in production behind Caddy. No CORS.
const apiTarget = process.env.VITE_API_PROXY_TARGET ?? "http://localhost:8000";
const proxy = {
  "/api": { target: apiTarget },
  "/admin": { target: apiTarget },
  "/static": { target: apiTarget },
};

// Placeholder brand colors: keep in sync with --palette-accent-500 / --palette-neutral-50 in
// src/styles/tokens.css (manifest values cannot use CSS variables).
const THEME_COLOR = "#5b4cf0";
const BACKGROUND_COLOR = "#f7f7f8";

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      // A new version waits until the user taps "Update" (never reloads under their feet).
      registerType: "prompt",
      injectRegister: false, // registered from src/pwa/usePwaUpdate.ts
      includeManifestIcons: false, // the workbox glob below already precaches public/icons
      manifest: {
        id: "/",
        name: "Crew Challenges",
        short_name: "Crew",
        description: "One shared challenge a month, checked in every day.",
        lang: "ro",
        start_url: "/",
        scope: "/",
        display: "standalone",
        orientation: "portrait",
        theme_color: THEME_COLOR,
        background_color: BACKGROUND_COLOR,
        icons: [
          { src: "/icons/icon-192.png", sizes: "192x192", type: "image/png" },
          { src: "/icons/icon-512.png", sizes: "512x512", type: "image/png" },
          {
            src: "/icons/icon-maskable-512.png",
            sizes: "512x512",
            type: "image/png",
            purpose: "maskable",
          },
        ],
      },
      workbox: {
        // Precache the app shell; every navigation falls back to it (offline start works).
        globPatterns: ["**/*.{js,css,html,png,svg,woff2}"],
        navigateFallback: "/index.html",
        // Never answer API, admin, Django static or media requests from the service worker.
        navigateFallbackDenylist: [/^\/api\//, /^\/admin/, /^\/static\//],
        runtimeCaching: [],
        cleanupOutdatedCaches: true,
      },
      devOptions: { enabled: false },
    }),
  ],
  resolve: {
    alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) },
  },
  server: {
    port: 5173,
    strictPort: true,
    host: true,
    // Allows `make tunnel` (Cloudflare quick tunnel) to reach the dev server.
    allowedHosts: [".trycloudflare.com"],
    proxy,
  },
  preview: {
    port: 4173,
    strictPort: true,
    host: true,
    allowedHosts: [".trycloudflare.com"],
    proxy,
  },
  build: {
    sourcemap: true,
    target: "es2022",
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
    alias: {
      // The service worker registration module only exists in real builds.
      "virtual:pwa-register/react": fileURLToPath(
        new URL("./src/test/pwaRegisterMock.ts", import.meta.url),
      ),
    },
    css: { modules: { classNameStrategy: "non-scoped" } },
    include: ["src/**/*.test.{ts,tsx}"],
    restoreMocks: true,
  },
});
