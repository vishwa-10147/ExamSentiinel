import { test, expect, Page, APIRequestContext } from "@playwright/test";

/**
 * Production-build checks: the Content-Security-Policy blocks nothing the app needs, and the
 * exam pages load the editor and the face-detection model from this app (no third-party CDN).
 * Run against a production build, e.g. the rehearsal stack (deploy/rehearsal/README.md):
 *
 *   PLAYWRIGHT_BASE_URL=https://exam.localhost:8443 PLAYWRIGHT_IGNORE_HTTPS_ERRORS=1 \
 *   E2E_API_URL=http://127.0.0.1:8080 E2E_PASSWORD=... npx playwright test tests/production.spec.ts
 */
const API = process.env.E2E_API_URL || "http://localhost:8000";
const PASSWORD = process.env.E2E_PASSWORD || "DemoPass123!";

test.describe.configure({ mode: "serial" });
test.use({
  permissions: ["camera", "microphone"],
  launchOptions: { args: ["--use-fake-ui-for-media-stream", "--use-fake-device-for-media-stream"] },
});

test.beforeAll(async ({ request }) => {
  const ok = await request.get(`${API}/api/health/live`).then((r) => r.ok()).catch(() => false);
  test.skip(!ok, `API not reachable at ${API}`);
});

/** Records CSP violations and requests to hosts other than the app and its API. */
function watch(page: Page) {
  const appHost = new URL(process.env.PLAYWRIGHT_BASE_URL || "http://localhost:3000").hostname;
  const violations: string[] = [];
  const foreign: string[] = [];
  page.on("console", (m) => {
    if (/Content Security Policy|Refused to (load|connect|execute|apply|create)/i.test(m.text())) violations.push(m.text());
  });
  page.on("request", (r) => {
    const url = new URL(r.url());
    if (!["http:", "https:", "ws:", "wss:"].includes(url.protocol)) return;
    const host = url.hostname;
    if (host !== appHost && host !== `api.${appHost}` && !["localhost", "127.0.0.1"].includes(host)) foreign.push(r.url());
  });
  return { violations, foreign };
}

async function login(page: Page, email: string) {
  await page.goto("/auth/login");
  await page.locator('input[type="email"]').fill(email);
  await page.locator('input[type="password"]').fill(PASSWORD);
  await page.locator('button[type="submit"]').click();
  await page.waitForURL((url) => !url.pathname.startsWith("/auth/login"), { timeout: 20000 });
}

async function token(request: APIRequestContext, email: string): Promise<string> {
  const r = await request.post(`${API}/api/auth/login`, { data: { email, password: PASSWORD } });
  expect(r.ok()).toBeTruthy();
  return (await r.json()).access_token;
}

test("the editor loads from this app with no CSP violations", async ({ page }) => {
  const seen = watch(page);
  await login(page, "candidate@sentinel.edu");
  await page.goto("/candidate/problems/balanced-brackets");
  await page.waitForFunction(() => (window as any).monaco?.editor?.getModels().length > 0, null, { timeout: 30000 });
  for (const path of ["/candidate/problems", "/candidate/contests", "/candidate/progress", "/candidate/practice"]) {
    await page.goto(path);
    await page.waitForLoadState("networkidle");
  }
  expect(seen.violations).toEqual([]);
  expect(seen.foreign).toEqual([]);
});

test("an exam page loads the face model from this app and starts the camera", async ({ page, request }) => {
  // Arrange an exam through the API (before the browser signs in: a sign-in ends other sessions).
  const admin = { Authorization: `Bearer ${await token(request, "admin@sentinel.edu")}` };
  const candidateToken = await token(request, "candidate@sentinel.edu");
  const me = await (await request.get(`${API}/api/auth/me`, { headers: { Authorization: `Bearer ${candidateToken}` } })).json();
  const now = Date.now();
  const exam = await (await request.post(`${API}/api/exams`, {
    headers: admin,
    data: {
      title: `Production check ${now}`, duration_minutes: 30,
      start_window: new Date(now - 5 * 60_000).toISOString(), end_window: new Date(now + 60 * 60_000).toISOString(),
    },
  })).json();
  const question = await (await request.post(`${API}/api/questions`, {
    headers: admin,
    data: { type: "SHORT_ANSWER", title: "Warm-up", content_rich_text: "Introduce yourself", points: 1.0 },
  })).json();
  await request.post(`${API}/api/exams/${exam.id}/questions`, { headers: admin, data: { question_id: question.id } });
  await request.post(`${API}/api/exams/${exam.id}/publish`, { headers: admin });
  await request.post(`${API}/api/exams/${exam.id}/enroll`, { headers: admin, data: { candidate_ids: [me.id] } });

  const seen = watch(page);
  const model = page.waitForResponse((r) => r.url().endsWith("/models/blazeface/model.json"), { timeout: 60000 });
  await login(page, "candidate@sentinel.edu");
  await page.goto(`/exam/${exam.id}`);
  expect((await model).status()).toBe(200);
  await page.waitForTimeout(5000); // model initialisation and the first webcam frames
  await expect(page.getByText("Failed to load AI tracking model.")).toHaveCount(0);
  expect(await page.evaluate(() => document.querySelectorAll("video").length)).toBeGreaterThan(0);
  expect(seen.violations).toEqual([]);
  expect(seen.foreign).toEqual([]);
});
