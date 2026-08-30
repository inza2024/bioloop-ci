import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./tests",
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: "list",
  use: {
    baseURL: "http://localhost:3000",
    trace: "retain-on-failure",
  },
  webServer: [
    {
      command:
        "../../.venv/bin/python -m uvicorn app.main:app --app-dir ../../services/api --host 127.0.0.1 --port 8000",
      url: "http://127.0.0.1:8000/health",
      reuseExistingServer: true,
      timeout: 120_000,
      env: {
        BIOLOOP_DB_PATH: "/tmp/bioloop-ci-e2e.db",
        BIOLOOP_EVIDENCE_DIR: "/tmp/bioloop-ci-e2e-evidence",
        BIOLOOP_WEB_ORIGIN: "http://localhost:3000",
        BIOLOOP_DEMO_IDENTITIES_ENABLED: "true",
        BIOLOOP_SYNTHETIC_PROFILE: "small",
      },
    },
    {
      command: "npm run dev -- --hostname 127.0.0.1 --port 3000",
      url: "http://127.0.0.1:3000",
      reuseExistingServer: true,
      timeout: 120_000,
      env: { NEXT_PUBLIC_API_URL: "http://localhost:8000" },
    },
  ],
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});
