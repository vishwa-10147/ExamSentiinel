"""Real code-execution tests against the self-hosted Piston engine.

Everything here talks to the actual engine (no fakes) and is skipped when it is
not reachable: docker compose -f docker-compose.piston.yml up -d, then
python scripts/install_piston_runtimes.py. These are the checks behind the
claims in docs/SECURITY.md and docs/CODE_EXECUTION.md.
"""

import os
from types import SimpleNamespace

import httpx
import pytest

from app.models.practice import JudgeMode, Verdict
from app.services import practice_judge
from app.services.practice_judge import JudgeCase
from app.services.sandbox_service import sandbox_service


PISTON_BASE = os.getenv("PISTON_URL", "http://localhost:2000/api/v2/execute").split("/api/")[0]


def _piston_available() -> bool:
    try:
        return httpx.get(f"{PISTON_BASE}/api/v2/runtimes", timeout=2).status_code == 200
    except httpx.HTTPError:
        return False


pytestmark = pytest.mark.skipif(not _piston_available(), reason=f"Piston engine not reachable at {PISTON_BASE} (docker compose -f docker-compose.piston.yml up -d)")


async def _run(code: str, language: str = "python", stdin: str = "", timeout: float = 5.0, memory: int = 256):
    return await sandbox_service.execute_async(language, code, stdin, timeout, memory)


# ---------------------------------------------------------------------------
# Custom programs in every language (the playground path)
# ---------------------------------------------------------------------------

ECHO_PROGRAMS = {
    "python": "import sys\nn = int(sys.stdin.readline())\nprint(n * 2)\nprint('warn', file=sys.stderr)\n",
    "javascript": "const n = parseInt(require('fs').readFileSync(0, 'utf8'));\nconsole.log(n * 2);\nconsole.error('warn');\n",
    "java": "import java.util.*;\npublic class Main {\n  public static void main(String[] a) {\n    int n = new Scanner(System.in).nextInt();\n    System.out.println(n * 2);\n    System.err.println(\"warn\");\n  }\n}\n",
    "c": "#include <stdio.h>\nint main(void) { int n; scanf(\"%d\", &n); printf(\"%d\\n\", n * 2); fprintf(stderr, \"warn\\n\"); return 0; }\n",
    "cpp": "#include <bits/stdc++.h>\nint main() { int n; std::cin >> n; std::cout << n * 2 << std::endl; std::cerr << \"warn\" << std::endl; }\n",
}


@pytest.mark.parametrize("language", list(ECHO_PROGRAMS))
async def test_programs_read_stdin_and_write_stdout_and_stderr(language):
    r = await _run(ECHO_PROGRAMS[language], language, stdin="21\n", timeout=10)
    assert r.status == "success", (r.stderr, r.compile_output)
    assert r.stdout.strip() == "42" and "warn" in r.stderr and r.exit_code == 0


@pytest.mark.parametrize(("language", "code"), [
    ("c", "int main(void) { return 0 }\n"),
    ("cpp", "int main() { undefined_name(); }\n"),
    ("java", "public class Main { public static void main(String[] a) { int x = \"s\"; } }\n"),
])
async def test_compile_errors_are_reported(language, code):
    r = await _run(code, language, timeout=10)
    assert r.status in ("compile_error", "error")
    assert "error" in (r.compile_output or r.stderr).lower()


async def test_playground_endpoint_reports_clean_compile_errors(async_client, seed_users):
    from app.models.user import UserRole
    from tests.test_exam_engine import auth_header

    headers = auth_header(next(u for u in seed_users if u.role == UserRole.CANDIDATE))
    for language, code in [("c", "int main(void) { return 0 }"), ("java", "public class Main { public static void main(String[] a) { int x = \"s\"; } }")]:
        r = (await async_client.post("/api/sandbox/execute", headers=headers, json={"language": language, "code": code})).json()
        assert r["status"] == "compile_error", r
        assert "error" in r["compile_output"] and "chmod" not in r["compile_output"] and "compilation failed" not in r["compile_output"]
        assert r["stderr"] == ""


@pytest.mark.parametrize(("language", "code"), [
    ("python", "print('before')\nraise ValueError('boom')\n"),
    ("javascript", "console.log('before'); null.x;\n"),
    ("java", "public class Main { public static void main(String[] a) { System.out.println(\"before\"); int[] x = new int[1]; x[2] = 1; } }\n"),
    ("c", "#include <stdio.h>\nint main(void) { printf(\"before\\n\"); fflush(stdout); return 3; }\n"),
])
async def test_runtime_errors_keep_partial_output_and_exit_code(language, code):
    r = await _run(code, language, timeout=10)
    assert r.status == "error" and r.exit_code != 0
    assert "before" in r.stdout


# ---------------------------------------------------------------------------
# Isolation and resource limits (verified, not assumed)
# ---------------------------------------------------------------------------

async def test_infinite_loop_is_killed_by_the_time_limit():
    r = await _run("while True:\n    pass\n", timeout=2)
    assert r.status == "timeout"


async def test_memory_hog_is_killed():
    r = await _run("x = bytearray(1024 * 1024 * 1024)\nprint('allocated')\n", memory=128)
    assert r.status == "memory_limit" and "allocated" not in r.stdout


async def test_output_flood_is_cut_off():
    r = await _run("import sys\nwhile True:\n    sys.stdout.write('x' * 65536)\n")
    assert r.status == "output_limit"


async def test_fork_bomb_hits_the_process_limit():
    code = (
        "import os, time\nn = 0\ntry:\n    while True:\n        if os.fork() == 0:\n            time.sleep(3); os._exit(0)\n        n += 1\n"
        "except OSError:\n    print('LIMIT', n)\n"
    )
    r = await _run(code)
    assert r.stdout.startswith("LIMIT"), (r.status, r.stdout, r.stderr)
    assert int(r.stdout.split()[1]) < 100


async def test_large_files_are_refused():
    code = "try:\n    f = open('big.bin', 'wb')\n    for _ in range(2048):\n        f.write(b'0' * (1 << 20))\n    print('WROTE')\nexcept OSError as e:\n    print('REFUSED', e.errno)\n"
    r = await _run(code)
    assert r.stdout.startswith("REFUSED"), r.stdout


async def test_no_network_access():
    code = (
        "import socket\n"
        "for target in [('1.1.1.1', 80), ('8.8.8.8', 53)]:\n"
        "    try:\n        socket.create_connection(target, timeout=3); print('CONNECTED', target)\n"
        "    except OSError as e:\n        print('BLOCKED', e.errno)\n"
        "try:\n    socket.gethostbyname('example.com'); print('RESOLVED')\nexcept OSError:\n    print('NO_DNS')\n"
    )
    r = await _run(code, timeout=10)
    assert "CONNECTED" not in r.stdout and "RESOLVED" not in r.stdout
    assert r.stdout.count("BLOCKED") == 2 and "NO_DNS" in r.stdout


async def test_runs_as_unprivileged_user_without_docker_socket_or_secrets():
    code = (
        "import os\nprint('UID', os.getuid())\n"
        "print('SOCK', any(os.path.exists(p) for p in ('/var/run/docker.sock', '/run/docker.sock')))\n"
        "print('ENV', sorted(os.environ))\n"
    )
    r = await _run(code)
    lines = dict(line.split(" ", 1) for line in r.stdout.strip().splitlines())
    assert int(lines["UID"]) != 0
    assert lines["SOCK"] == "False"
    env = lines["ENV"]
    for secret in ("SECRET_KEY", "DATABASE_URL", "OPENAI_API_KEY", "GEMINI_API_KEY", "SMTP_PASSWORD", "AWS_", "PISTON_RUN"):
        assert secret not in env, f"{secret} leaked into the sandbox environment"


async def test_filesystem_is_isolated_and_not_persistent():
    probe = (
        "import os\n"
        "for p in ('/piston/packages/x', '/etc/x', '/piston_api/x'):\n"
        "    try:\n        open(p, 'w').write('x'); print('WROTE', p)\n    except OSError:\n        print('DENIED')\n"
        "try:\n    open('/etc/shadow').read(); print('READ_SHADOW')\nexcept OSError:\n    print('DENIED')\n"
        "open('/tmp/es_marker', 'w').write('x')\n"
    )
    r = await _run(probe)
    assert "WROTE" not in r.stdout and "READ_SHADOW" not in r.stdout and r.stdout.count("DENIED") == 4
    r = await _run("import os\nprint(os.path.exists('/tmp/es_marker'))\n")
    assert r.stdout.strip() == "False", "files must not survive between runs"


# ---------------------------------------------------------------------------
# Judged solutions in Java / C++ / JavaScript for the new data structures
# ---------------------------------------------------------------------------

def _bank_problem(slug: str):
    from practice_bank import PROBLEMS
    from seed_practice import build_cases

    p = next(p for p in PROBLEMS if p["slug"] == slug)
    cases = [JudgeCase(c.input_data, c.expected_output, c.is_sample) for c in build_cases(p)]
    problem = SimpleNamespace(
        slug=slug, judge_mode=JudgeMode.FUNCTION, function_spec=p["spec"], compare_mode=p.get("compare", "exact"),
        checker=p.get("checker"), time_limit_ms=p.get("time_limit_ms", 2000), memory_limit_mb=256,
    )
    return problem, cases


SOLUTIONS = [
    ("reverse-linked-list", "java",
     "class Solution { public ListNode reverseList(ListNode head) { ListNode prev = null; while (head != null) { ListNode n = head.next; head.next = prev; prev = head; head = n; } return prev; } }"),
    ("reverse-linked-list", "cpp",
     "class Solution { public: ListNode* reverseList(ListNode* head) { ListNode* prev = nullptr; while (head) { ListNode* n = head->next; head->next = prev; prev = head; head = n; } return prev; } };"),
    ("reverse-linked-list", "javascript",
     "class Solution { reverseList(head) { let prev = null; while (head) { const n = head.next; head.next = prev; prev = head; head = n; } return prev; } }"),
    ("detect-list-cycle", "java",
     "class Solution { public boolean hasCycle(ListNode head) { ListNode s = head, f = head; while (f != null && f.next != null) { s = s.next; f = f.next.next; if (s == f) return true; } return false; } }"),
    ("mirror-tree", "cpp",
     "class Solution { public: TreeNode* mirror(TreeNode* root) { vector<TreeNode*> st; if (root) st.push_back(root); while (!st.empty()) { TreeNode* n = st.back(); st.pop_back(); swap(n->left, n->right); if (n->left) st.push_back(n->left); if (n->right) st.push_back(n->right); } return root; } };"),
    ("mirror-tree", "java",
     "import java.util.*;\nclass Solution { public TreeNode mirror(TreeNode root) { Deque<TreeNode> st = new ArrayDeque<>(); if (root != null) st.push(root); while (!st.isEmpty()) { TreeNode n = st.pop(); TreeNode t = n.left; n.left = n.right; n.right = t; if (n.left != null) st.push(n.left); if (n.right != null) st.push(n.right); } return root; } }"),
    ("running-medians", "cpp",
     "class Solution { public: vector<double> runningMedians(vector<int>& nums) { priority_queue<int> lo; priority_queue<int, vector<int>, greater<int>> hi; vector<double> out; for (int x : nums) { lo.push(x); hi.push(lo.top()); lo.pop(); if (hi.size() > lo.size()) { lo.push(hi.top()); hi.pop(); } out.push_back(lo.size() > hi.size() ? lo.top() : (lo.top() + (double)hi.top()) / 2.0); } return out; } };"),
    ("cheapest-routes", "cpp",
     "class Solution { public: vector<long long> cheapestRoutes(int n, vector<vector<int>>& edges, int source) { vector<vector<pair<int,int>>> adj(n); for (auto& e : edges) adj[e[0]].push_back({e[1], e[2]}); vector<long long> d(n, -1); priority_queue<pair<long long,int>, vector<pair<long long,int>>, greater<>> pq; pq.push({0, source}); while (!pq.empty()) { auto [w, u] = pq.top(); pq.pop(); if (d[u] >= 0) continue; d[u] = w; for (auto [v, c] : adj[u]) if (d[v] < 0) pq.push({w + c, v}); } return d; } };"),
    ("task-ordering", "java",
     "import java.util.*;\nclass Solution { public int[] taskOrder(int n, int[][] deps) { List<List<Integer>> adj = new ArrayList<>(); for (int i = 0; i < n; i++) adj.add(new ArrayList<>()); int[] in = new int[n]; for (int[] d : deps) { adj.get(d[0]).add(d[1]); in[d[1]]++; } Deque<Integer> st = new ArrayDeque<>(); for (int i = 0; i < n; i++) if (in[i] == 0) st.push(i); int[] out = new int[n]; int k = 0; while (!st.isEmpty()) { int u = st.pop(); out[k++] = u; for (int v : adj.get(u)) if (--in[v] == 0) st.push(v); } return out; } }"),
    ("queens-boards", "javascript",
     "class Solution { queensBoards(n) { const out = [], cols = []; const go = (r, used, d1, d2) => { if (r === n) { out.push(cols.map(c => '.'.repeat(c) + 'Q' + '.'.repeat(n - c - 1))); return; } for (let c = 0; c < n; c++) { if (used.has(c) || d1.has(r - c) || d2.has(r + c)) continue; cols.push(c); go(r + 1, new Set([...used, c]), new Set([...d1, r - c]), new Set([...d2, r + c])); cols.pop(); } }; go(0, new Set(), new Set(), new Set()); return out; } }"),
    # C, using LeetCode's C conventions (pointer + size, returnSize, returnColumnSizes).
    ("pair-with-target-sum", "c", """
typedef struct { int v, i; } P;
static int cmp(const void *a, const void *b) { const P *x = a, *y = b; return (x->v > y->v) - (x->v < y->v); }
int* pairSum(int* nums, int numsSize, int target, int* returnSize) {
    P *p = malloc(sizeof(P) * numsSize);
    for (int i = 0; i < numsSize; i++) { p[i].v = nums[i]; p[i].i = i; }
    qsort(p, numsSize, sizeof(P), cmp);
    int *res = malloc(2 * sizeof(int)), l = 0, r = numsSize - 1;
    *returnSize = 0;
    while (l < r) {
        long long s = (long long) p[l].v + p[r].v;
        if (s == target) { res[0] = p[l].i; res[1] = p[r].i; *returnSize = 2; break; }
        if (s < target) l++; else r--;
    }
    return res;
}
"""),
    ("reverse-linked-list", "c", """
struct ListNode* reverseList(struct ListNode* head) {
    struct ListNode *prev = NULL;
    while (head) { struct ListNode *n = head->next; head->next = prev; prev = head; head = n; }
    return prev;
}
"""),
    ("detect-list-cycle", "c", """
bool hasCycle(struct ListNode *head) {
    struct ListNode *s = head, *f = head;
    while (f && f->next) { s = s->next; f = f->next->next; if (s == f) return true; }
    return false;
}
"""),
    ("remove-adjacent-pairs", "c", """
char* removePairs(char* s) {
    size_t n = strlen(s), k = 0; char *st = malloc(n + 1);
    for (size_t i = 0; i < n; i++) { if (k && st[k - 1] == s[i]) k--; else st[k++] = s[i]; }
    st[k] = 0; return st;
}
"""),
    ("fast-power-mod", "c", """
int powerMod(int base, long long exponent, int m) {
    long long r = 1 % m, b = base % m;
    while (exponent) { if (exponent & 1) r = r * b % m; b = b * b % m; exponent >>= 1; }
    return (int) r;
}
"""),
    ("level-order", "c", """
int** levelOrder(struct TreeNode* root, int* returnSize, int** returnColumnSizes) {
    int cap = 10001, h = 0, t = 0;
    struct TreeNode **q = malloc(sizeof(*q) * cap);
    int **res = malloc(sizeof(int*) * cap);
    *returnColumnSizes = malloc(sizeof(int) * cap); *returnSize = 0;
    if (root) q[t++] = root;
    while (h < t) {
        int end = t, size = t - h, k = 0; int *row = malloc(sizeof(int) * size);
        for (; h < end; h++) { row[k++] = q[h]->val; if (q[h]->left) q[t++] = q[h]->left; if (q[h]->right) q[t++] = q[h]->right; }
        res[*returnSize] = row; (*returnColumnSizes)[(*returnSize)++] = size;
    }
    return res;
}
"""),
    ("queens-boards", "c", """
static char ***qb_out; static int qb_n, qb_cnt, qb_cap, qb_cols[9];
static void qb_go(int r, int used, int d1, int d2) {
    if (r == qb_n) {
        if (qb_cnt == qb_cap) { qb_cap = qb_cap ? qb_cap * 2 : 16; qb_out = realloc(qb_out, sizeof(char**) * qb_cap); }
        char **board = malloc(sizeof(char*) * qb_n);
        for (int i = 0; i < qb_n; i++) { board[i] = malloc(qb_n + 1); memset(board[i], '.', qb_n); board[i][qb_cols[i]] = 'Q'; board[i][qb_n] = 0; }
        qb_out[qb_cnt++] = board; return;
    }
    for (int c = 0; c < qb_n; c++) {
        int a = 1 << c, b = 1 << (r - c + qb_n), d = 1 << (r + c);
        if ((used & a) || (d1 & b) || (d2 & d)) continue;
        qb_cols[r] = c; qb_go(r + 1, used | a, d1 | b, d2 | d);
    }
}
char*** queensBoards(int n, int* returnSize, int** returnColumnSizes) {
    qb_n = n; qb_cnt = 0; qb_cap = 0; qb_out = NULL; qb_go(0, 0, 0, 0);
    *returnSize = qb_cnt; *returnColumnSizes = malloc(sizeof(int) * (qb_cnt ? qb_cnt : 1));
    for (int i = 0; i < qb_cnt; i++) (*returnColumnSizes)[i] = n;
    return qb_out;
}
"""),
    ("task-ordering", "c", """
int* taskOrder(int n, int** deps, int depsSize, int* depsColSize, int* returnSize) {
    int *deg = calloc(n, sizeof(int)), *start = calloc(n + 1, sizeof(int)), *adj = malloc(sizeof(int) * (depsSize ? depsSize : 1));
    for (int i = 0; i < depsSize; i++) { start[deps[i][0] + 1]++; deg[deps[i][1]]++; }
    for (int i = 0; i < n; i++) start[i + 1] += start[i];
    int *fill = malloc(sizeof(int) * n); memcpy(fill, start, sizeof(int) * n);
    for (int i = 0; i < depsSize; i++) adj[fill[deps[i][0]]++] = deps[i][1];
    int *q = malloc(sizeof(int) * n), h = 0, t = 0;
    for (int i = n - 1; i >= 0; i--) if (!deg[i]) q[t++] = i;  /* a different valid order than the reference */
    while (h < t) { int u = q[h++]; for (int k = start[u]; k < start[u + 1]; k++) if (--deg[adj[k]] == 0) q[t++] = adj[k]; }
    *returnSize = t; return q;
}
"""),
    ("count-groups", "c", """
static int *uf;
static int find(int x) { while (uf[x] != x) { uf[x] = uf[uf[x]]; x = uf[x]; } return x; }
int countGroups(int n, int** edges, int edgesSize, int* edgesColSize) {
    uf = malloc(sizeof(int) * n); for (int i = 0; i < n; i++) uf[i] = i;
    int groups = n;
    for (int i = 0; i < edgesSize; i++) { int a = find(edges[i][0]), b = find(edges[i][1]); if (a != b) { uf[a] = b; groups--; } }
    return groups;
}
"""),
]


@pytest.mark.parametrize(("slug", "language", "code"), SOLUTIONS, ids=[f"{s}-{lang}" for s, lang, _ in SOLUTIONS])
async def test_correct_solutions_in_other_languages_are_accepted(slug, language, code):
    problem, cases = _bank_problem(slug)
    outcome = await practice_judge.judge(problem, language, code, cases)
    assert outcome.verdict == Verdict.ACCEPTED, (outcome.compile_output, outcome.error, [c for c in outcome.cases if not c.passed][:1])


async def test_wrong_and_slow_solutions_get_the_right_verdicts():
    problem, cases = _bank_problem("reverse-linked-list")
    wrong = await practice_judge.judge(problem, "python", "class Solution:\n    def reverseList(self, head):\n        return head\n", cases)
    assert wrong.verdict == Verdict.WRONG_ANSWER
    slow = await practice_judge.judge(problem, "python", "class Solution:\n    def reverseList(self, head):\n        while True:\n            pass\n", cases)
    assert slow.verdict == Verdict.TIME_LIMIT_EXCEEDED
    broken = await practice_judge.judge(problem, "cpp", "class Solution { public: ListNode* reverseList(ListNode* h) { return h->missing; } };", cases)
    assert broken.verdict == Verdict.COMPILE_ERROR
    crash = await practice_judge.judge(problem, "java", "class Solution { public ListNode reverseList(ListNode h) { return h.next.next.next.next.next.next.next.next.next.next.next; } }", cases)
    assert crash.verdict == Verdict.RUNTIME_ERROR


# Every spec type, round-tripped through the C harness: parse JSON -> C value -> JSON.
C_ECHO = {
    "int": ("int echo(int x) { return x; }", [7, -2147483648]),
    "long": ("long long echo(long long x) { return x; }", [9007199254740991, -5]),
    "double": ("double echo(double x) { return x; }", [2.5, -0.125]),
    "bool": ("bool echo(bool x) { return x; }", [True, False]),
    "string": ("char* echo(char* x) { return x; }", ['hi "there"\n\\', ""]),
    "int[]": ("int* echo(int* x, int xSize, int* returnSize) { *returnSize = xSize; return x; }", [[1, 2, 3], []]),
    "long[]": ("long long* echo(long long* x, int xSize, int* returnSize) { *returnSize = xSize; return x; }", [[10**15, -1], []]),
    "double[]": ("double* echo(double* x, int xSize, int* returnSize) { *returnSize = xSize; return x; }", [[0.5, 1.5], []]),
    "bool[]": ("bool* echo(bool* x, int xSize, int* returnSize) { *returnSize = xSize; return x; }", [[True, False], []]),
    "string[]": ("char** echo(char** x, int xSize, int* returnSize) { *returnSize = xSize; return x; }", [["a", "b c"], []]),
    "int[][]": ("int** echo(int** x, int xSize, int* xColSize, int* returnSize, int** returnColumnSizes) { *returnSize = xSize; *returnColumnSizes = xColSize; return x; }", [[[1, 2], [], [3]], []]),
    "string[][]": ("char*** echo(char*** x, int xSize, int* xColSize, int* returnSize, int** returnColumnSizes) { *returnSize = xSize; *returnColumnSizes = xColSize; return x; }", [[["a"], ["b", "c"]], []]),
    "ListNode": ("struct ListNode* echo(struct ListNode* x) { return x; }", [[1, 2, 3], []]),
    "TreeNode": ("struct TreeNode* echo(struct TreeNode* x) { return x; }", [[3, 9, 20, None, None, 15, 7], [], [1, None, 2]]),
}


@pytest.mark.parametrize("type_name", list(C_ECHO))
async def test_c_harness_round_trips_every_type(type_name):
    import json

    code, values = C_ECHO[type_name]
    spec = {"name": "echo", "params": [{"name": "x", "type": type_name}], "return_type": type_name}
    assert code.split("{")[0].strip() == practice_judge.starter_code(spec, "c").strip().splitlines()[-3].rstrip(" {")
    problem = SimpleNamespace(judge_mode=JudgeMode.FUNCTION, function_spec=spec, compare_mode="exact", checker=None,
                              time_limit_ms=2000, memory_limit_mb=256, slug="echo")
    cases = [JudgeCase(json.dumps(v, separators=(",", ":")), json.dumps(v, separators=(",", ":"))) for v in values]
    outcome = await practice_judge.judge(problem, "c", code, cases)
    assert outcome.verdict == Verdict.ACCEPTED, (outcome.compile_output, outcome.error, [(c.output, c.error) for c in outcome.cases])


async def test_c_specific_verdicts_and_stdout_capture():
    problem, cases = _bank_problem("reverse-linked-list")
    noisy = await practice_judge.judge(problem, "c", """
struct ListNode* reverseList(struct ListNode* head) {
    printf("debug %d\\n", head ? head->val : -1);
    struct ListNode *prev = NULL;
    while (head) { struct ListNode *n = head->next; head->next = prev; prev = head; head = n; }
    return prev;
}
""", cases)
    assert noisy.verdict == Verdict.ACCEPTED, (noisy.compile_output, noisy.error)
    assert noisy.cases[0].stdout.startswith("debug "), "each case's printf output is captured separately"
    assert "@@ES@@" not in noisy.cases[0].stdout

    segfault = await practice_judge.judge(problem, "c", "struct ListNode* reverseList(struct ListNode* head) { int *p = NULL; *p = 1; return head; }", cases)
    assert segfault.verdict == Verdict.RUNTIME_ERROR
    broken = await practice_judge.judge(problem, "c", "struct ListNode* reverseList(struct ListNode* head) { return head->missing; }", cases)
    assert broken.verdict == Verdict.COMPILE_ERROR and "missing" in broken.compile_output
    slow = await practice_judge.judge(problem, "c", "struct ListNode* reverseList(struct ListNode* head) { volatile int x = 0; for (;;) x++; return head; }", cases)
    assert slow.verdict == Verdict.TIME_LIMIT_EXCEEDED

    pairs, pair_cases = _bank_problem("pair-with-target-sum")
    null_result = await practice_judge.judge(pairs, "c", "int* pairSum(int* nums, int numsSize, int target, int* returnSize) { *returnSize = 2; return NULL; }", pair_cases)
    assert null_result.verdict == Verdict.RUNTIME_ERROR and "returnSize" in (null_result.error or "")


# ---------------------------------------------------------------------------
# Every reference solution in the bank passes its own tests on the engine
# ---------------------------------------------------------------------------

def _all_slugs():
    from practice_bank import PROBLEMS

    return [p["slug"] for p in PROBLEMS]


@pytest.mark.parametrize("slug", _all_slugs())
async def test_reference_solution_passes_on_the_engine(slug):
    from practice_bank import PROBLEMS
    from seed_practice import build_cases

    p = next(p for p in PROBLEMS if p["slug"] == slug)
    mode = p.get("judge_mode", JudgeMode.FUNCTION)
    problem = SimpleNamespace(
        slug=slug, judge_mode=mode, function_spec=p.get("spec"), sql_schema=p.get("sql_schema"),
        compare_mode=p.get("compare", "exact"), checker=p.get("checker"), time_limit_ms=p.get("time_limit_ms", 2000), memory_limit_mb=256,
    )
    cases = [JudgeCase(c.input_data, c.expected_output, c.is_sample) for c in build_cases(p)]
    language = "sql" if mode == JudgeMode.SQL else "python"
    outcome = await practice_judge.judge(problem, language, p["reference"].strip() + "\n", cases)
    assert outcome.verdict == Verdict.ACCEPTED, (outcome.verdict, outcome.compile_output, outcome.error)
    assert outcome.passed_count == len(cases)
