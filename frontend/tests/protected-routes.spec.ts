import { test, expect } from "@playwright/test";

test.describe("protected portal routes", () => {
  const routes = [
    "/candidate/exams",
    "/candidate/results",
    "/admin/settings",
    "/admin/exam/builder",
    "/admin/review",
    "/exam/readiness",
  ];

  for (const route of routes) {
    test(`${route} redirects unauthenticated users`, async ({ page }) => {
      await page.goto(route);
      await page.waitForURL(/\/auth\/login/);
      await expect(page.locator('input[type="email"]')).toBeVisible();
    });
  }
});

test("login page remains usable on a narrow mobile viewport", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 812 });
  await page.goto("/auth/login");
  await expect(page.locator('input[type="email"]')).toBeVisible();
  await expect(page.locator('button[type="submit"]')).toBeVisible();
  await expect(page.locator("body")).toHaveCSS("overflow-x", "hidden");
});
