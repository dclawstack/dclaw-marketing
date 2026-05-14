import { defineConfig, devices } from "@playwright/test";

// Sprint 4 S4-J4 smoke harness — boots Chromium against a running
// docker-compose stack at SMOKE_BASE_URL (defaults to localhost:3015).
export default defineConfig({
  testDir: "./tests",
  timeout: 30_000,
  expect: { timeout: 5_000 },
  fullyParallel: true,
  retries: 0,
  reporter: [["list"], ["html", { open: "never" }]],
  use: {
    baseURL: process.env.SMOKE_BASE_URL || "http://localhost:3015",
    trace: "on-first-retry",
  },
  projects: [
    { name: "chromium", use: { ...devices["Desktop Chrome"] } },
  ],
});
