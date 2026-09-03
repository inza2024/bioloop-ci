import { defineConfig, devices } from "@playwright/test";

const apiPort = 18080;
const webPort = 13080;
const runId = process.pid;
const apiUrl = `http://localhost:${apiPort}`;
const webUrl = `http://localhost:${webPort}`;

export default defineConfig({
  testDir: "./tests",
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: "list",
  use: {
    baseURL: webUrl,
    trace: "retain-on-failure",
  },
  webServer: [
    {
      command:
        `../../.venv/bin/python -m uvicorn app.main:app --app-dir ../../services/api --host 127.0.0.1 --port ${apiPort}`,
      url: `http://127.0.0.1:${apiPort}/health`,
      reuseExistingServer: false,
      timeout: 120_000,
      env: {
        BIOLOOP_DB_PATH: `/tmp/bioloop-ci-e2e-${runId}.db`,
        BIOLOOP_EVIDENCE_DIR: `/tmp/bioloop-ci-e2e-evidence-${runId}`,
        BIOLOOP_WEB_ORIGIN: webUrl,
        BIOLOOP_DEMO_IDENTITIES_ENABLED: "true",
        BIOLOOP_SYNTHETIC_PROFILE: "small",
      },
    },
    {
      command: `npm run dev -- --hostname 127.0.0.1 --port ${webPort}`,
      url: `http://127.0.0.1:${webPort}`,
      reuseExistingServer: false,
      timeout: 120_000,
      env: {
        NEXT_PUBLIC_API_URL: apiUrl,
        BIOLOOP_NEXT_DIST_DIR: ".next-e2e",
      },
    },
  ],
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});
