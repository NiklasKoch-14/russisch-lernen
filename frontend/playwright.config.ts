import { defineConfig, devices } from "@playwright/test";

const FRONTEND_PORT = 5174;
const BACKEND_PORT = 8001;
const E2E_DB = ".e2e/speaker.db";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? "line" : [["list"]],
  use: {
    baseURL: `http://localhost:${FRONTEND_PORT}`,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: [
    {
      // Frische Datenbank je Lauf — die Tests verändern den Lernfortschritt.
      command: `rm -f ${E2E_DB} && DB_PATH=${E2E_DB} .venv/bin/uvicorn app.main:app --port ${BACKEND_PORT} --log-level warning`,
      cwd: "../backend",
      url: `http://localhost:${BACKEND_PORT}/api/health`,
      reuseExistingServer: false,
      timeout: 60_000,
    },
    {
      command: `npm run dev -- --port ${FRONTEND_PORT}`,
      env: { VITE_API_BASE_URL: `http://localhost:${BACKEND_PORT}` },
      url: `http://localhost:${FRONTEND_PORT}`,
      reuseExistingServer: false,
      timeout: 60_000,
    },
  ],
});
