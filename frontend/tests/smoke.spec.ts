// Playwright smoke suite (S4-J4).
//
// These tests boot against a running stack at the URLs in the
// environment. They are NOT meant to test business logic — they
// assert the core routes render without crashing.
//
// Run locally:
//   docker compose up -d
//   cd frontend
//   npx playwright test tests/smoke.spec.ts

import { expect, test } from "@playwright/test";

const BASE = process.env.SMOKE_BASE_URL || "http://localhost:3015";

const ROUTES = [
  "/login",
  "/",
  "/orgs",
  "/integrations",
  "/agents/creatives",
  "/agents/smm",
  "/agents/seo",
  "/agents/paid-media",
  "/agents/analyst",
  "/admin/health",
  "/admin/users",
  "/admin/models",
  "/conductor",
  "/workflows",
  "/workflows/templates",
  "/settings/2fa",
];

for (const path of ROUTES) {
  test(`renders ${path}`, async ({ page }) => {
    const r = await page.goto(`${BASE}${path}`, { waitUntil: "domcontentloaded" });
    expect(r?.status() ?? 0).toBeLessThan(500);
    // No uncaught console errors that crash the page render.
    const errors: string[] = [];
    page.on("pageerror", (e) => errors.push(e.message));
    await page.waitForTimeout(500);
    expect(errors, `console errors on ${path}: ${errors.join("\n")}`).toHaveLength(0);
  });
}
