import { test, expect, Page, APIRequestContext, Browser } from "@playwright/test";

/**
 * Every page of the web app, opened by the role that uses it, with real data behind the detail
 * pages. A page fails if it crashes (uncaught error, error screen, 404), if the API answers it
 * with a server error (5xx), or if a signed-in user is sent back to the sign-in page.
 *
 *   PLAYWRIGHT_BASE_URL=http://localhost:3000 npx playwright test tests/all-pages.spec.ts --workers=1
 */
const API = process.env.E2E_API_URL || "http://localhost:8000";
const PASSWORD = process.env.E2E_PASSWORD || "DemoPass123!";

test.describe.configure({ mode: "serial" });
test.setTimeout(600_000);
test.use({
  permissions: ["camera", "microphone"],
  launchOptions: { args: ["--use-fake-ui-for-media-stream", "--use-fake-device-for-media-stream"] },
});

const data: Record<string, string> = {};

async function token(request: APIRequestContext, email: string): Promise<Record<string, string>> {
  const r = await request.post(`${API}/api/auth/login`, { data: { email, password: PASSWORD } });
  expect(r.ok(), `sign-in ${email}`).toBeTruthy();
  return { Authorization: `Bearer ${(await r.json()).access_token}` };
}

async function publishedExam(request: APIRequestContext, admin: Record<string, string>, candidateId: string, title: string) {
  const now = Date.now();
  const exam = await (await request.post(`${API}/api/exams`, {
    headers: admin,
    data: { title, duration_minutes: 30, start_window: new Date(now - 300_000).toISOString(), end_window: new Date(now + 3_600_000).toISOString() },
  })).json();
  const q = await (await request.post(`${API}/api/questions`, {
    headers: admin, data: { type: "SHORT_ANSWER", title: "Warm-up", content_rich_text: "Introduce yourself", points: 1.0 },
  })).json();
  await request.post(`${API}/api/exams/${exam.id}/questions`, { headers: admin, data: { question_id: q.id } });
  await request.post(`${API}/api/exams/${exam.id}/publish`, { headers: admin });
  await request.post(`${API}/api/exams/${exam.id}/enroll`, { headers: admin, data: { candidate_ids: [candidateId] } });
  return exam.id as string;
}

test.beforeAll(async ({ request }) => {
  const ok = await request.get(`${API}/api/health/live`).then((r) => r.ok()).catch(() => false);
  test.skip(!ok, `API not reachable at ${API}`);

  // Arranged through the API before any browser sign-in (signing in ends other sessions).
  const admin = await token(request, "admin@sentinel.edu");
  const candidate = await token(request, "candidate@sentinel.edu");
  const me = await (await request.get(`${API}/api/auth/me`, { headers: candidate })).json();
  const stamp = Date.now();

  data.exam = await publishedExam(request, admin, me.id, `Pages ${stamp} open`);           // pages that open an exam
  const finished = await publishedExam(request, admin, me.id, `Pages ${stamp} finished`);
  const done = await (await request.post(`${API}/api/exam/sessions/start`, { headers: candidate, data: { exam_id: finished } })).json();
  await request.post(`${API}/api/exam/sessions/${done.session_id}/submit`, { headers: candidate, data: { confirm: true } });
  data.resultSession = done.session_id;

  const interviewExam = await publishedExam(request, admin, me.id, `Pages ${stamp} interview`);
  const s = await (await request.post(`${API}/api/exam/sessions/start`, { headers: candidate, data: { exam_id: interviewExam } })).json();
  const interview = await (await request.post(`${API}/api/interviews/sessions`, { headers: candidate, data: { exam_session_id: s.session_id } })).json();
  await request.post(`${API}/api/interviews/${interview.id}/consent`, { headers: candidate, data: { consent: true, notice_version: "pages" } });
  data.interview = interview.id;

  const problems = await (await request.get(`${API}/api/practice/admin/problems`, { headers: admin })).json();
  data.problemId = problems[0].id;
  data.problemSlug = (problems.find((p: any) => p.slug === "balanced-brackets") || problems[0]).slug;
  const contest = await (await request.post(`${API}/api/admin/contests`, {
    headers: admin,
    data: {
      slug: `pages-${stamp}`, title: `Pages contest ${stamp}`, starts_at: new Date(stamp - 60_000).toISOString(), duration_minutes: 60,
      is_published: true, problems: [{ problem_id: problems.find((p: any) => !p.is_published)?.id || problems[problems.length - 1].id, points: 100 }],
    },
  })).json();
  data.contestId = contest.id;
  data.contestSlug = contest.slug;

  const reviews = await (await request.get(`${API}/api/reviews`, { headers: admin })).json();
  data.review = (reviews.items || reviews)[0]?.id || "";
});

test.afterAll(async ({ request }) => {
  if (!data.contestId) return;
  const admin = await token(request, "admin@sentinel.edu");
  await request.delete(`${API}/api/admin/contests/${data.contestId}`, { headers: admin });
});

async function signIn(browser: Browser, email: string): Promise<Page> {
  const page = await (await browser.newContext()).newPage();
  await page.goto("/auth/login");
  await page.locator('input[type="email"]').fill(email);
  await page.locator('input[type="password"]').fill(PASSWORD);
  await page.locator('button[type="submit"]').click();
  await page.waitForURL((url) => !url.pathname.startsWith("/auth/login"), { timeout: 30000 });
  return page;
}

/** Opens each path and returns a description of every problem found. */
async function visitAll(page: Page, paths: string[], signedIn = true): Promise<string[]> {
  const problems: string[] = [];
  for (const path of paths) {
    const errors: string[] = [];
    const onError = (e: Error) => errors.push(`uncaught: ${e.message.slice(0, 160)}`);
    const onResponse = (r: { url(): string; status(): number }) => {
      if (r.status() >= 500 && r.url().includes("/api/")) errors.push(`API ${r.status()} ${new URL(r.url()).pathname}`);
    };
    page.on("pageerror", onError);
    page.on("response", onResponse);
    try {
      const response = await page.goto(path, { waitUntil: "domcontentloaded", timeout: 120_000 });
      if (response && response.status() >= 400) errors.push(`HTTP ${response.status()}`);
      await page.waitForLoadState("networkidle", { timeout: 15_000 }).catch(() => undefined);
      await page.waitForTimeout(500);
      const text = await page.locator("body").innerText().catch(() => "");
      if (/404 - Page Not Found|Application error|Unhandled Runtime Error|Something went wrong/i.test(text)) errors.push("error screen");
      if (signedIn && new URL(page.url()).pathname.startsWith("/auth/login")) errors.push("sent to sign-in");
    } catch (e: any) {
      errors.push(`navigation: ${String(e.message).split("\n")[0]}`);
    } finally {
      page.off("pageerror", onError);
      page.off("response", onResponse);
    }
    if (errors.length) problems.push(`${path}: ${[...new Set(errors)].join("; ")}`);
  }
  return problems;
}

test("public pages", async ({ page }) => {
  const problems = await visitAll(page, ["/", "/auth/login", "/auth/register", "/auth/forgot-password", "/auth/sso-callback", "/privacy", "/terms"], false);
  expect(problems).toEqual([]);
});

test("admin pages", async ({ browser }) => {
  const page = await signIn(browser, "admin@sentinel.edu");
  const problems = await visitAll(page, [
    "/dashboard", "/admin/dashboard", "/admin/live", "/dashboard/live", "/admin/exam", "/admin/exam/builder",
    `/admin/exam/${data.exam}/edit`, `/admin/exam/${data.exam}/manage`, `/admin/exam/${data.exam}/grading`,
    "/admin/questions", "/admin/problems", `/admin/problems/${data.problemId}`, "/admin/contests", "/admin/results",
    "/admin/review", ...(data.review ? [`/admin/review/${data.review}`] : []), "/admin/interviews", "/admin/broadcast",
    "/admin/audit", "/admin/analytics", "/admin/users", "/admin/users/create", "/admin/settings", "/admin/ai-test",
    `/interview/${data.interview}`,
  ]);
  expect(problems).toEqual([]);
});

test("proctor pages", async ({ browser }) => {
  const page = await signIn(browser, "proctor@sentinel.edu");
  const problems = await visitAll(page, ["/proctor/dashboard", "/proctor/live", "/admin/interviews", `/interview/${data.interview}`]);
  expect(problems).toEqual([]);
});

test("reviewer pages", async ({ browser }) => {
  const page = await signIn(browser, "reviewer@sentinel.edu");
  const problems = await visitAll(page, ["/reviewer/dashboard", "/admin/review", ...(data.review ? [`/admin/review/${data.review}`] : [])]);
  expect(problems).toEqual([]);
});

test("candidate pages", async ({ browser }) => {
  const page = await signIn(browser, "candidate@sentinel.edu");
  const problems = await visitAll(page, [
    "/candidate/dashboard", "/candidate/exams", "/candidate/problems", `/candidate/problems/${data.problemSlug}`,
    "/candidate/progress", "/candidate/practice", "/candidate/contests", `/candidate/contests/${data.contestSlug}`,
    "/candidate/leaderboard", "/candidate/results", `/candidate/results/${data.resultSession}`, "/candidate/profile",
    `/exam/readiness?exam_id=${data.exam}`, `/exam/${data.exam}`, `/exam/${data.exam}/lab`, `/exam/${data.exam}/interview`, "/exam/completed",
    `/interview/${data.interview}`,
  ]);
  expect(problems).toEqual([]);
});
