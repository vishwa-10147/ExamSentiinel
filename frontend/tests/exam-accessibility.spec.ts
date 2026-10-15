import { test, expect, APIRequestContext } from "@playwright/test";

/** A student who cannot use a mouse can still answer and navigate an exam. */
const API = process.env.E2E_API_URL || "http://localhost:8000";
const PASSWORD = process.env.E2E_PASSWORD || "DemoPass123!";

test.use({
  permissions: ["camera", "microphone"],
  launchOptions: { args: ["--use-fake-ui-for-media-stream", "--use-fake-device-for-media-stream"] },
});

test.beforeAll(async ({ request }) => {
  const ok = await request.get(`${API}/api/health/live`).then((r) => r.ok()).catch(() => false);
  test.skip(!ok, `API not reachable at ${API}`);
});

async function token(request: APIRequestContext, email: string) {
  return (await (await request.post(`${API}/api/auth/login`, { data: { email, password: PASSWORD } })).json()).access_token as string;
}

test("multiple-choice answers can be chosen with the keyboard alone", async ({ page, request }) => {
  const admin = { Authorization: `Bearer ${await token(request, "admin@sentinel.edu")}` };
  const me = await (await request.get(`${API}/api/auth/me`, { headers: { Authorization: `Bearer ${await token(request, "candidate@sentinel.edu")}` } })).json();
  const now = Date.now();
  const exam = await (await request.post(`${API}/api/exams`, {
    headers: admin,
    data: { title: `Keyboard ${now}`, duration_minutes: 30, start_window: new Date(now - 300_000).toISOString(), end_window: new Date(now + 3_600_000).toISOString() },
  })).json();
  const q = await (await request.post(`${API}/api/questions`, {
    headers: admin,
    data: { type: "MCQ_SINGLE", title: "Complexity", content_rich_text: "Binary search runs in?", points: 1.0,
            options: [{ id: "1", text: "O(log n)" }, { id: "2", text: "O(n)" }], correct_answer: "1" },
  })).json();
  await request.post(`${API}/api/exams/${exam.id}/questions`, { headers: admin, data: { question_id: q.id } });
  await request.post(`${API}/api/exams/${exam.id}/publish`, { headers: admin });
  await request.post(`${API}/api/exams/${exam.id}/enroll`, { headers: admin, data: { candidate_ids: [me.id] } });

  await page.goto("/auth/login");
  await page.locator('input[type="email"]').fill("candidate@sentinel.edu");
  await page.locator('input[type="password"]').fill(PASSWORD);
  await page.locator('button[type="submit"]').click();
  await page.waitForURL((url) => !url.pathname.startsWith("/auth/login"), { timeout: 20000 });
  const started = page.waitForResponse((r) => r.url().includes("/api/exam/sessions/start") && r.ok());
  await page.goto(`/exam/${exam.id}`);
  const sessionId = (await (await started).json()).session_id;

  const group = page.getByRole("radiogroup", { name: /Answer options/ });
  await expect(group).toBeVisible({ timeout: 30000 });
  const choice = group.getByRole("radio", { name: "O(log n)" });
  await choice.focus(); // reached with Tab; focus it directly to keep the test independent of tab order
  await page.keyboard.press("Space");
  await expect(choice).toHaveAttribute("aria-checked", "true");
  await expect(group.getByRole("radio", { name: "O(n)" })).toHaveAttribute("aria-checked", "false");

  await expect.poll(async () => {
    const state = await (await request.get(`${API}/api/exam/sessions/${sessionId}`, { headers: admin })).json();
    return Object.values(state.responses || {}).map((r: any) => String(r.response_data?.selected_option_id));
  }, { timeout: 15000 }).toEqual(["1"]);

  // The submit dialog is announced as a dialog, takes focus, and Escape closes it.
  await page.getByRole("button", { name: "Submit Exam" }).click();
  const dialog = page.getByRole("dialog", { name: "Submit Examination?" });
  await expect(dialog).toBeVisible();
  await expect(dialog.getByRole("button", { name: "Confirm & Submit" })).toBeFocused();
  await page.keyboard.press("Escape");
  await expect(dialog).toHaveCount(0);
});
