import { defineConfig, devices } from "@playwright/test";

/**
 * End-to-end tests against the real backend: `make e2e`.
 * Starts Django (migrated, with the demo crew) and the Vite dev server unless they already run.
 * Needs Postgres and Redis (the compose services, or your own on localhost).
 */
const backendEnv = {
  DJANGO_SETTINGS_MODULE: "config.settings.local",
  DJANGO_DEBUG: "true",
  ...(process.env.E2E_DATABASE_URL ? { DATABASE_URL: process.env.E2E_DATABASE_URL } : {}),
};

export default defineConfig({
  testDir: "e2e",
  timeout: 30_000,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? "github" : "list",
  use: {
    baseURL: "http://localhost:5173",
    trace: "retain-on-failure",
    locale: "en-US",
  },
  projects: [{ name: "mobile", use: { ...devices["Pixel 7"] } }],
  webServer: [
    {
      command:
        "uv run python manage.py migrate -v0 && uv run python manage.py seed_demo && " +
        "uv run python manage.py runserver 127.0.0.1:8000 --noreload",
      cwd: "../backend",
      url: "http://127.0.0.1:8000/api/health",
      env: backendEnv,
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
    },
    {
      command: "pnpm dev",
      url: "http://localhost:5173",
      env: { VITE_API_PROXY_TARGET: "http://127.0.0.1:8000" },
      reuseExistingServer: !process.env.CI,
      timeout: 60_000,
    },
  ],
});
