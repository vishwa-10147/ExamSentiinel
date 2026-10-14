import { test, expect, Page } from "@playwright/test";

/**
 * Role journeys against a running stack (backend on :8000 with seed_admin.py and
 * seed_practice.py applied, Piston up). Skipped when the API isn't reachable.
 *
 *   PLAYWRIGHT_BASE_URL=http://localhost:3000 npx playwright test tests/roles.spec.ts
 */
const API = process.env.E2E_API_URL || "http://localhost:8000";
const PASSWORD = process.env.E2E_PASSWORD || "DemoPass123!"; // seed_admin.py demo value

// Logging in as a user revokes their other sessions, so these run one at a time.
test.describe.configure({ mode: "serial" });

test.beforeAll(async ({ request }) => {
  const ok = await request.get(`${API}/api/health/live`).then((r) => r.ok()).catch(() => false);
  test.skip(!ok, `API not reachable at ${API}`);
});

async function login(page: Page, email: string) {
  await page.goto("/auth/login");
  await page.evaluate(() => localStorage.clear());
  await page.goto("/auth/login");
  await page.locator('input[type="email"]').fill(email);
  await page.locator('input[type="password"]').fill(PASSWORD);
  await page.locator('button[type="submit"]').click();
  await page.waitForURL((url) => !url.pathname.startsWith("/auth/login"), { timeout: 20000 });
}

async function setEditorCode(page: Page, code: string) {
  await page.waitForFunction(() => (window as any).monaco?.editor?.getModels().length > 0, null, { timeout: 30000 });
  await page.evaluate((src) => (window as any).monaco.editor.getModels()[0].setValue(src), code);
}

test("candidate solves a practice problem: run then submit", async ({ page }) => {
  await login(page, "candidate@sentinel.edu");
  await page.goto("/candidate/problems");
  await expect(page.getByRole("heading", { name: "Problem Set" })).toBeVisible({ timeout: 20000 });
  await expect(page.getByRole("tab", { name: /Hard/ })).toBeVisible();

  await page.goto("/candidate/problems/balanced-brackets");
  await expect(page.getByRole("heading", { name: "Balanced Brackets" })).toBeVisible({ timeout: 20000 });
  await setEditorCode(
    page,
    [
      "class Solution:",
      "    def isBalanced(self, s):",
      "        pairs = {')': '(', ']': '[', '}': '{'}",
      "        stack = []",
      "        for ch in s:",
      "            if ch in pairs:",
      "                if not stack or stack.pop() != pairs[ch]:",
      "                    return False",
      "            else:",
      "                stack.append(ch)",
      "        return not stack",
      "",
    ].join("\n")
  );

  await page.getByRole("button", { name: "Run", exact: true }).click();
  await expect(page.getByText(/sample tests passed/)).toBeVisible({ timeout: 30000 });
  await expect(page.getByText("Accepted").first()).toBeVisible();

  await page.getByRole("button", { name: "Submit" }).click();
  await expect(page.getByText("Solution recorded in your submissions.")).toBeVisible({ timeout: 30000 });
});

test("candidate browses the DSA bank by topic and ID", async ({ page }) => {
  await login(page, "candidate@sentinel.edu");
  await page.goto("/candidate/problems?topic=Linked%20Lists");
  const rows = page.locator("tbody tr");
  await expect(rows).toHaveCount(8, { timeout: 20000 });
  await expect(rows.first()).toContainText("Reverse a Linked List");

  await page.getByLabel("Filter by topic").selectOption("");
  await page.getByLabel("Search problems").fill("#111");
  await expect(rows).toHaveCount(1);
  await expect(rows.first()).toContainText("Order the Tasks");

  await page.getByLabel("Search problems").fill("");
  await page.getByLabel("Sort problems").selectOption("number");
  await expect(rows.first()).toContainText("Pair With Target Sum");
  expect(await rows.count()).toBeGreaterThanOrEqual(127);
});

test("candidate solves a linked-list problem in C++ and unlocks the editorial", async ({ page }) => {
  await login(page, "candidate@sentinel.edu");
  await page.goto("/candidate/problems/middle-node");
  await expect(page.getByRole("heading", { name: /77\. / })).toBeVisible({ timeout: 20000 });
  await expect(page.getByText("Input format")).toBeVisible();

  await page.getByLabel("Language").selectOption("cpp");
  await setEditorCode(
    page,
    "class Solution {\npublic:\n    ListNode* middleNode(ListNode* head) {\n        ListNode *slow = head, *fast = head;\n        while (fast && fast->next) { slow = slow->next; fast = fast->next->next; }\n        return slow;\n    }\n};\n"
  );
  await page.getByRole("button", { name: "Submit" }).click();
  await expect(page.getByText("Solution recorded in your submissions.")).toBeVisible({ timeout: 60000 });

  await page.getByRole("tab", { name: "Editorial" }).click();
  await expect(page.getByText("Approach")).toBeVisible({ timeout: 15000 });
  await expect(page.getByText(/Solve this problem to unlock/)).toHaveCount(0);
});

test("candidate sees progress by topic and submission history", async ({ page }) => {
  await login(page, "candidate@sentinel.edu");
  await page.goto("/candidate/progress");
  await expect(page.getByRole("heading", { name: "Practice Progress" })).toBeVisible({ timeout: 20000 });
  await expect(page.getByRole("heading", { name: "By topic" })).toBeVisible();
  await expect(page.getByRole("link", { name: /Graphs/ })).toBeVisible();
  await expect(page.getByText(/Submission history \(\d+\)/)).toBeVisible();
});

test("candidate runs a C program with stdin in the playground", async ({ page }) => {
  await login(page, "candidate@sentinel.edu");
  await page.goto("/candidate/practice");
  await page.getByLabel("Language").selectOption("c");
  await setEditorCode(page, '#include <stdio.h>\nint main(void) {\n    int a, b;\n    scanf("%d %d", &a, &b);\n    printf("%d\\n", a * b);\n    return 0;\n}\n');
  await page.getByLabel("Standard input").fill("6 7");
  await page.getByRole("button", { name: "Run" }).click();
  await expect(page.locator("pre").filter({ hasText: "42" })).toBeVisible({ timeout: 30000 });
  await expect(page.getByText("Finished")).toBeVisible();
});

test("candidate is kept out of staff areas", async ({ page }) => {
  await login(page, "candidate@sentinel.edu");
  for (const path of ["/proctor/dashboard", "/admin/users", "/reviewer/dashboard"]) {
    await page.goto(path);
    await page.waitForURL(/\/candidate\/dashboard|\/dashboard/, { timeout: 15000 });
  }
});

test("admin creates a user and sees the one-time password", async ({ page }) => {
  await login(page, "admin@sentinel.edu");
  await page.goto("/admin/users/create");
  await page.locator('input[name="fullName"]').fill("Playwright Student");
  await page.locator('input[name="email"]').fill(`pw-${Date.now()}@example.edu`);
  await page.getByRole("button", { name: "Create User" }).click();
  await expect(page.getByText(/Account created for/)).toBeVisible({ timeout: 15000 });
  await expect(page.locator("code")).toHaveText(/.{12,}/);
});

test("admin opens practice authoring and the add-to-exam dialog", async ({ page }) => {
  await login(page, "admin@sentinel.edu");
  await page.goto("/admin/problems");
  await expect(page.getByRole("heading", { name: "Practice Problems" })).toBeVisible();
  await page.getByTitle("Use in an exam").first().click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await expect(page.getByLabel("Points")).toHaveValue(/\d+/);
  await page.getByRole("button", { name: "Cancel" }).click();
});

test("reviewer and proctor dashboards load their queues", async ({ page }) => {
  await login(page, "reviewer@sentinel.edu");
  await expect(page).toHaveURL(/reviewer\/dashboard/);
  await expect(page.getByText(/Review Queue/).first()).toBeVisible();

  await login(page, "proctor@sentinel.edu");
  await page.goto("/admin/interviews");
  await expect(page.getByRole("heading", { name: "Live Interviews" })).toBeVisible();
});
