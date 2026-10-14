// Screenshots every main page in light and dark mode for a visual theme review.
//
//   cd frontend && node scripts/theme-audit.mjs        # writes test-results/theme-audit/*.png
//
// Needs the stack running locally with seeded demo accounts (see docs/INSTALLATION.md).
import { chromium } from "@playwright/test";
import { mkdirSync } from "node:fs";
import { join } from "node:path";

const APP = process.env.APP_URL || "http://localhost:3000";
const API = process.env.API_URL || "http://localhost:8000";
const PASSWORD = process.env.DEMO_PASSWORD || "DemoPass123!"; // seed_admin.py development value
const OUT = join(process.cwd(), "test-results", "theme-audit");
mkdirSync(OUT, { recursive: true });

const PAGES = {
  "": ["/auth/login", "/auth/register", "/auth/forgot-password", "/privacy", "/terms"],
  "candidate@sentinel.edu": [
    "/candidate/dashboard", "/candidate/exams", "/candidate/problems", "/candidate/problems/pair-with-target-sum",
    "/candidate/practice", "/candidate/progress", "/candidate/results", "/candidate/leaderboard", "/candidate/profile",
    "/exam/readiness",
  ],
  "admin@sentinel.edu": [
    "/admin/dashboard", "/admin/exam", "/admin/exam/builder", "/admin/questions", "/admin/problems", "/admin/results",
    "/admin/review", "/admin/users", "/admin/settings", "/admin/analytics", "/admin/audit", "/admin/broadcast",
    "/admin/interviews", "/admin/live", "/admin/ai-test",
  ],
  "proctor@sentinel.edu": ["/proctor/dashboard", "/proctor/live"],
  "reviewer@sentinel.edu": ["/reviewer/dashboard"],
};

const browser = await chromium.launch();
for (const theme of ["light", "dark"]) {
  const context = await browser.newContext({ viewport: { width: 1280, height: 800 } });
  const page = await context.newPage();
  for (const [email, paths] of Object.entries(PAGES)) {
    await page.goto(`${APP}/auth/login`);
    let session = null;
    if (email) {
      const res = await fetch(`${API}/api/auth/login`, {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ email, password: PASSWORD }),
      });
      session = await res.json();
    }
    await page.evaluate(({ s, t }) => {
      localStorage.clear();
      localStorage.setItem("theme", t);
      localStorage.setItem("cookieConsent", "declined");
      if (s) {
        localStorage.setItem("access_token", s.access_token);
        localStorage.setItem("refresh_token", s.refresh_token);
        localStorage.setItem("user_profile", JSON.stringify(s.user));
      }
    }, { s: session, t: theme });
    for (const path of paths) {
      await page.goto(`${APP}${path}`);
      await page.waitForTimeout(2500);
      const name = `${path.replace(/^\//, "").replace(/[\/\[\]]/g, "_") || "root"}--${theme}.png`;
      await page.screenshot({ path: join(OUT, name) });
    }
  }
  await context.close();
}
await browser.close();
console.log(`saved to ${OUT}`);
