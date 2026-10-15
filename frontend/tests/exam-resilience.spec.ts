import { test, expect, Page, APIRequestContext } from "@playwright/test";

/**
 * Exam-day failures: answers must reach the server despite a failing API, a dropped connection,
 * a page reload, or a submit right after typing. What the server holds is checked through the
 * API as an admin (services/answerSync.ts is the code under test).
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

async function token(request: APIRequestContext, email: string): Promise<string> {
  const r = await request.post(`${API}/api/auth/login`, { data: { email, password: PASSWORD } });
  expect(r.ok()).toBeTruthy();
  return (await r.json()).access_token;
}

/** A published two-question exam the candidate is enrolled in. Returns its id and an admin header. */
async function arrangeExam(request: APIRequestContext, endsInMs = 60 * 60_000) {
  const admin = { Authorization: `Bearer ${await token(request, "admin@sentinel.edu")}` };
  const candidate = { Authorization: `Bearer ${await token(request, "candidate@sentinel.edu")}` };
  const me = await (await request.get(`${API}/api/auth/me`, { headers: candidate })).json();
  const now = Date.now();
  const exam = await (await request.post(`${API}/api/exams`, {
    headers: admin,
    data: {
      title: `Resilience ${now}`, duration_minutes: 30,
      start_window: new Date(now - 5 * 60_000).toISOString(), end_window: new Date(now + endsInMs).toISOString(),
    },
  })).json();
  for (const title of ["First", "Second"]) {
    const q = await (await request.post(`${API}/api/questions`, {
      headers: admin, data: { type: "SHORT_ANSWER", title, content_rich_text: `${title} question`, points: 1.0 },
    })).json();
    await request.post(`${API}/api/exams/${exam.id}/questions`, { headers: admin, data: { question_id: q.id } });
  }
  await request.post(`${API}/api/exams/${exam.id}/publish`, { headers: admin });
  await request.post(`${API}/api/exams/${exam.id}/enroll`, { headers: admin, data: { candidate_ids: [me.id] } });
  return { examId: exam.id as string, admin };
}

async function login(page: Page) {
  await page.goto("/auth/login");
  await page.locator('input[type="email"]').fill("candidate@sentinel.edu");
  await page.locator('input[type="password"]').fill(PASSWORD);
  await page.locator('button[type="submit"]').click();
  await page.waitForURL((url) => !url.pathname.startsWith("/auth/login"), { timeout: 20000 });
}

/** Opens the exam and returns its session id. */
async function openExam(page: Page, examId: string): Promise<string> {
  let starts = 0;
  const count = (r: { url(): string; method(): string }) => {
    if (r.url().includes("/api/exam/sessions/start") && r.method() === "POST") starts += 1;
  };
  page.on("request", count);
  const started = page.waitForResponse((r) => r.url().includes("/api/exam/sessions/start") && r.ok());
  await page.goto(`/exam/${examId}`);
  const session = await (await started).json();
  await expect(page.getByPlaceholder("Type your brief answer here...")).toBeVisible({ timeout: 30000 });
  page.off("request", count);
  expect(starts).toBe(1); // the page starts the session once (two at once created duplicate sessions)
  return session.session_id;
}

async function serverAnswers(request: APIRequestContext, admin: Record<string, string>, sessionId: string) {
  const state = await (await request.get(`${API}/api/exam/sessions/${sessionId}`, { headers: admin })).json();
  return Object.values(state.responses || {}).map((r: any) => r.response_data?.text).filter(Boolean).sort();
}

const saveStatus = (page: Page) => page.locator("[data-save-status]");

test("answers typed while the API fails reach the server once it recovers", async ({ page, request }) => {
  const { examId, admin } = await arrangeExam(request);
  // Installed before the page loads: Chromium does not intercept some cross-origin requests
  // (after a cached CORS preflight) when a route is added later.
  let failing = false;
  let refused = 0;
  await page.route("**/answers", (route) => {
    if (!failing) return route.continue();
    refused += 1;
    const origin = route.request().headers()["origin"] || "";
    return route.fulfill({
      status: 503, body: '{"detail":"busy"}', contentType: "application/json",
      headers: { "Access-Control-Allow-Origin": origin, "Access-Control-Allow-Credentials": "true" },
    });
  });
  await login(page);
  const sessionId = await openExam(page, examId);

  // The API fails (e.g. a deploy, a 503 from a saturated database) but the browser stays "online".
  failing = true;
  await page.getByPlaceholder("Type your brief answer here...").fill("written during an outage");
  await expect(saveStatus(page)).toHaveAttribute("data-save-status", "offline", { timeout: 10000 });
  await expect.poll(() => refused, { timeout: 10000 }).toBeGreaterThan(1); // it keeps retrying
  expect(await serverAnswers(request, admin, sessionId)).toEqual([]);

  failing = false; // recovery: picked up by the next retry, no "online" event needed
  await expect(saveStatus(page)).toHaveAttribute("data-save-status", "saved", { timeout: 20000 });
  expect(await serverAnswers(request, admin, sessionId)).toEqual(["written during an outage"]);
});

test("answers survive a reload while the connection is down", async ({ page, request }) => {
  const { examId, admin } = await arrangeExam(request);
  await login(page);
  let failing = false;
  await page.route("**/answers", (route) => (failing ? route.abort("internetdisconnected") : route.continue()));
  const sessionId = await openExam(page, examId);

  failing = true;
  await page.getByPlaceholder("Type your brief answer here...").fill("kept on this device");
  await expect(saveStatus(page)).toHaveAttribute("data-save-status", "offline", { timeout: 10000 });

  await page.reload(); // e.g. the student refreshes, or the browser restarts
  await expect(page.getByPlaceholder("Type your brief answer here...")).toHaveValue("kept on this device", { timeout: 30000 });
  expect(await serverAnswers(request, admin, sessionId)).toEqual([]);

  failing = false;
  await expect.poll(() => serverAnswers(request, admin, sessionId), { timeout: 30000 }).toEqual(["kept on this device"]);
});

test("the last edit is saved before the exam is submitted", async ({ page, request }) => {
  const { examId, admin } = await arrangeExam(request);
  await login(page);
  const sessionId = await openExam(page, examId);

  // Slow saves: the answer is still in flight when the student submits.
  await page.route("**/answers", async (route) => {
    await new Promise((r) => setTimeout(r, 1500));
    await route.continue();
  });
  await page.getByPlaceholder("Type your brief answer here...").fill("typed right before submitting");
  await page.getByRole("button", { name: "Submit Exam" }).click();
  await page.getByRole("button", { name: "Confirm & Submit" }).click();
  await expect(page.getByText("Exam Submitted Successfully")).toBeVisible({ timeout: 30000 });

  const state = await (await request.get(`${API}/api/exam/sessions/${sessionId}`, { headers: admin })).json();
  expect(state.status).toBe("SUBMITTED");
  expect(await serverAnswers(request, admin, sessionId)).toEqual(["typed right before submitting"]);
});

test("when time runs out, the exam is submitted even if the first attempts fail", async ({ page, request }) => {
  test.setTimeout(180_000);
  const { examId, admin } = await arrangeExam(request, 75_000); // the exam window closes in 75 s
  let refusals = 2;
  await page.route("**/submit", (route) => {
    if (refusals-- > 0) return route.abort("internetdisconnected");
    return route.continue();
  });
  await login(page);
  const sessionId = await openExam(page, examId);
  await page.getByPlaceholder("Type your brief answer here...").fill("answered before time ran out");

  // At zero the page submits by itself; the first attempts fail, so it must say it is still submitting.
  await expect(page.getByText(/Time is up/)).toBeVisible({ timeout: 120_000 });
  await expect(page.getByText("Exam Submitted Successfully")).toBeVisible({ timeout: 60_000 });
  const state = await (await request.get(`${API}/api/exam/sessions/${sessionId}`, { headers: admin })).json();
  expect(state.status).toBe("SUBMITTED");
  expect(await serverAnswers(request, admin, sessionId)).toEqual(["answered before time ran out"]);
});
