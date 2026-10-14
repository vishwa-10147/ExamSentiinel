// Captures the README / docs screenshots from a running local stack.
//
//   cd frontend
//   node scripts/capture-screenshots.mjs            # writes ../docs/assets/screenshots/*.png
//
// Needs the backend on :8000 (seeded with seed_admin.py + seed_practice.py), the frontend on
// :3000 and the Piston engine for the "run" shots. Override with APP_URL / API_URL / DEMO_PASSWORD.
import { chromium } from "@playwright/test";
import { mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const APP = process.env.APP_URL || "http://localhost:3000";
const API = process.env.API_URL || "http://localhost:8000";
const PASSWORD = process.env.DEMO_PASSWORD || "DemoPass123!"; // seed_admin.py development value
const OUT = join(dirname(fileURLToPath(import.meta.url)), "..", "..", "docs", "assets", "screenshots");
mkdirSync(OUT, { recursive: true });

async function signIn(page, email) {
  const res = await fetch(`${API}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password: PASSWORD }),
  });
  if (!res.ok) throw new Error(`login failed for ${email}: ${res.status}`);
  const data = await res.json();
  await page.goto(`${APP}/auth/login`);
  await page.evaluate((d) => {
    localStorage.setItem("access_token", d.access_token);
    localStorage.setItem("refresh_token", d.refresh_token);
    localStorage.setItem("user_profile", JSON.stringify(d.user));
    localStorage.setItem("cookieConsent", "declined");
  }, data);
}

async function shot(page, name, { path, waitFor, before, fullPage = false } = {}) {
  if (path) await page.goto(`${APP}${path}`);
  if (waitFor) await page.waitForSelector(waitFor, { timeout: 60000 });
  if (before) await before(page);
  await page.waitForTimeout(1200); // let charts and transitions settle
  await page.screenshot({ path: join(OUT, `${name}.png`), fullPage });
  console.log(`saved ${name}.png`);
}

async function setEditor(page, code) {
  await page.waitForFunction(() => window.monaco?.editor?.getModels().length > 0, null, { timeout: 60000 });
  await page.evaluate((src) => window.monaco.editor.getModels()[0].setValue(src), code);
}

const browser = await chromium.launch();
const context = await browser.newContext({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1, colorScheme: "light" });
const page = await context.newPage();

try {
  await page.goto(`${APP}/auth/login`);
  await page.evaluate(() => localStorage.setItem("cookieConsent", "declined"));
  await shot(page, "login", { path: "/auth/login", waitFor: 'input[type="email"]' });

  await signIn(page, "candidate@sentinel.edu");
  await shot(page, "problem-set", { path: "/candidate/problems", waitFor: "tbody tr td a" });

  await shot(page, "problem-workspace", {
    path: "/candidate/problems/pair-with-target-sum",
    waitFor: "h1",
    before: async (p) => {
      await setEditor(
        p,
        [
          "class Solution:",
          "    def pairSum(self, nums, target):",
          "        seen = {}",
          "        for i, x in enumerate(nums):",
          "            if target - x in seen:",
          "                return [seen[target - x], i]",
          "            seen[x] = i",
          "",
        ].join("\n")
      );
      await p.getByRole("button", { name: "Run", exact: true }).click();
      await p.getByText("Accepted").first().waitFor({ timeout: 60000 });
    },
  });

  await shot(page, "progress", { path: "/candidate/progress", waitFor: "text=By topic" });

  await shot(page, "playground", {
    path: "/candidate/practice",
    waitFor: "#stdin",
    before: async (p) => {
      await p.getByLabel("Language").selectOption("cpp");
      await setEditor(
        p,
        '#include <bits/stdc++.h>\nusing namespace std;\n\nint main() {\n    int n; cin >> n;\n    vector<long long> fib(n + 1, 0);\n    if (n > 0) fib[1] = 1;\n    for (int i = 2; i <= n; i++) fib[i] = fib[i - 1] + fib[i - 2];\n    for (int i = 0; i <= n; i++) cout << fib[i] << (i < n ? " " : "\\n");\n}\n'
      );
      await p.locator("#stdin").fill("15");
      await p.getByRole("button", { name: "Run" }).click();
      await p.getByText("Finished").waitFor({ timeout: 60000 });
    },
  });

  await signIn(page, "admin@sentinel.edu");
  await shot(page, "admin-dashboard", { path: "/admin/dashboard", waitFor: "text=Admin Command Center" });
  await shot(page, "admin-problems", { path: "/admin/problems", waitFor: "tbody tr" });

  await signIn(page, "proctor@sentinel.edu");
  await shot(page, "proctor-dashboard", { path: "/proctor/dashboard", waitFor: "main h1, main h2" });

  await signIn(page, "reviewer@sentinel.edu");
  await shot(page, "reviewer-dashboard", { path: "/reviewer/dashboard", waitFor: "main h1, main h2" });
} finally {
  await browser.close();
}
