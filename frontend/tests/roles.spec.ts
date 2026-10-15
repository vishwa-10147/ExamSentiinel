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

test("candidate solves an array problem in C with LeetCode-style signatures", async ({ page }) => {
  await login(page, "candidate@sentinel.edu");
  await page.goto("/candidate/problems/sorted-squares");
  await expect(page.getByRole("heading", { name: /59\. / })).toBeVisible({ timeout: 20000 });
  await page.getByLabel("Language").selectOption("c");
  await page.waitForFunction(() => (window as any).monaco?.editor?.getModels()[0]?.getValue().includes("returnSize"), null, {
    timeout: 30000,
  });
  await setEditorCode(
    page,
    [
      "int* sortedSquares(int* nums, int numsSize, int* returnSize) {",
      "    int *res = malloc(sizeof(int) * (numsSize ? numsSize : 1));",
      "    int l = 0, r = numsSize - 1;",
      "    for (int k = numsSize - 1; k >= 0; k--) {",
      "        int a = nums[l] * nums[l], b = nums[r] * nums[r];",
      "        if (a > b) { res[k] = a; l++; } else { res[k] = b; r--; }",
      "    }",
      "    *returnSize = numsSize;",
      "    return res;",
      "}",
      "",
    ].join("\n")
  );
  await page.getByRole("button", { name: "Submit" }).click();
  await expect(page.getByText("Solution recorded in your submissions.")).toBeVisible({ timeout: 60000 });
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

test("admin schedules a contest; candidate registers, solves and is ranked", async ({ page, request }) => {
  const title = `Playwright Contest ${Date.now()}`;
  const slug = title.toLowerCase().replace(/[^a-z0-9]+/g, "-");
  try {
    await login(page, "admin@sentinel.edu");
    await page.goto("/admin/contests");
    await page.getByRole("button", { name: "New contest" }).click();
    await page.getByPlaceholder("Weekly Contest 1").fill(title);
    // Started a minute ago, so it is running now.
    const start = await page.evaluate(() => {
      const d = new Date(Date.now() - 60_000);
      const p = (n: number) => String(n).padStart(2, "0");
      return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}T${p(d.getHours())}:${p(d.getMinutes())}`;
    });
    await page.locator('input[type="datetime-local"]').fill(start);
    const picker = page.getByLabel("Problem to add");
    const value = await picker.locator("option", { hasText: "Balanced Brackets" }).first().getAttribute("value");
    await picker.selectOption(value!);
    await page.getByRole("button", { name: "Add", exact: true }).click();
    await page.getByLabel("Published (visible to students)").check();
    await page.getByRole("button", { name: "Save contest" }).click();
    await expect(page.getByRole("table", { name: "Contests" }).getByText(title)).toBeVisible({ timeout: 15000 });

    await login(page, "candidate@sentinel.edu");
    await page.goto("/candidate/contests");
    const card = page.getByRole("listitem").filter({ hasText: title });
    await card.getByRole("button", { name: "Register" }).click();
    await expect(card.getByText("Registered")).toBeVisible({ timeout: 15000 });
    await card.getByRole("link", { name: "Enter" }).click();
    await expect(page.getByRole("heading", { name: title })).toBeVisible({ timeout: 20000 });
    await expect(page.getByRole("timer")).toHaveText(/\d\d:\d\d:\d\d/);

    await page.getByRole("link", { name: "A. Balanced Brackets" }).click();
    await expect(page.getByRole("link", { name: "Contest", exact: true })).toBeVisible({ timeout: 20000 });
    // The sidebar shows the student is inside the contest, not the practice problem set.
    await expect(page.getByRole("link", { name: "Contests", exact: true })).toHaveAttribute("aria-current", "page");
    await expect(page.getByRole("link", { name: "Problem Set", exact: true })).not.toHaveAttribute("aria-current", "page");
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
    await page.getByRole("button", { name: "Submit" }).click();
    await expect(page.getByText("Solution recorded in your submissions.")).toBeVisible({ timeout: 30000 });

    await page.getByRole("link", { name: "Contest", exact: true }).click();
    await page.getByRole("tab", { name: "Leaderboard" }).click();
    const me = page.getByRole("table", { name: "Leaderboard" }).getByRole("row").filter({ hasText: "(you)" });
    await expect(me).toContainText("Test Candidate", { timeout: 15000 });
    await expect(me.getByRole("cell").nth(2)).toHaveText(/^[1-9]\d*$/); // a positive score
  } finally {
    // A running contest hides its problems from practice: always remove it.
    const auth = await request.post(`${API}/api/auth/login`, { data: { email: "admin@sentinel.edu", password: PASSWORD } });
    const headers = { Authorization: `Bearer ${(await auth.json()).access_token}` };
    const contests = await (await request.get(`${API}/api/admin/contests`, { headers })).json();
    for (const c of contests.filter((c: { slug: string }) => c.slug === slug)) {
      await request.delete(`${API}/api/admin/contests/${c.id}`, { headers });
    }
  }
});
