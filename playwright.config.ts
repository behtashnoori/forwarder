import { defineConfig } from "@playwright/test";
import { randomBytes } from "node:crypto";

const databaseUrl = process.env.E2E_DATABASE_URL;
if (!databaseUrl) throw new Error("E2E_DATABASE_URL must name an explicit disposable PostgreSQL database.");
const ephemeralSecret = () => randomBytes(32).toString("hex");

const appEnv = {
  APP_ENV: "uat",
  DATABASE_URL: databaseUrl,
  SECRET_KEY: process.env.E2E_SECRET_KEY || ephemeralSecret(),
  JWT_SECRET_KEY: process.env.E2E_JWT_SECRET_KEY || ephemeralSecret(),
  PORT: "5001",
  CORS_ORIGINS: "http://127.0.0.1:4173",
};

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: [["list"], ["html", { outputFolder: "playwright-report", open: "never" }]],
  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL || "http://127.0.0.1:4173",
    browserName: "chromium",
    channel: process.env.PLAYWRIGHT_CHANNEL || "chrome",
    locale: "fa-IR",
    screenshot: "only-on-failure",
    trace: "retain-on-failure",
    video: "off",
  },
  webServer: process.env.PLAYWRIGHT_EXTERNAL_SERVER ? undefined : [
    { command: "npm run backend", url: "http://127.0.0.1:5001/api/health", env: appEnv, reuseExistingServer: false, timeout: 120_000 },
    { command: "npm run dev -- --host 127.0.0.1 --port 4173", url: "http://127.0.0.1:4173", env: appEnv, reuseExistingServer: false, timeout: 120_000 },
  ],
});
