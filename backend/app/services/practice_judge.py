"""LeetCode-style judge for practice problems.

FUNCTION mode
    The student implements a method on ``class Solution``. For each language we
    generate a harness around their code that reads every test case from stdin
    (line 1 = case count, then one compact JSON value per parameter per case),
    calls the method, and prints one ``@@ES@@{json}`` line per case containing
    the result, the case's captured stdout and its runtime. All cases run in a
    single sandbox execution, so compiled languages compile once.

STDIO mode
    Classic competitive-programming style: each case is run separately with its
    input on stdin and the trimmed stdout compared to the expected text.
"""

from __future__ import annotations

import asyncio
import json
import math
import re
from dataclasses import dataclass, field
from typing import Any, Optional

from app.models.practice import JudgeMode, PracticeProblem, Verdict
from app.services.sandbox_service import SandboxResult, sandbox_service

SUPPORTED_LANGUAGES = ("python", "javascript", "java", "cpp")
SUPPORTED_TYPES = (
    "int", "long", "double", "bool", "string",
    "int[]", "long[]", "double[]", "bool[]", "string[]",
    "int[][]", "string[][]",
    # Linked list (JSON array of values) and binary tree (level-order JSON array with nulls).
    "ListNode", "TreeNode",
)
RESULT_MARKER = "@@ES@@"
INPUT_FILE = "es_input.txt"  # FUNCTION-mode test data (Piston truncates stdin beyond ~200 kB)
MAX_STDIO_INPUT_BYTES = 128 * 1024
MAX_TOTAL_RUN_MS = 10_000  # matches PISTON_RUN_TIMEOUT in docker-compose.piston.yml
_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class JudgeSpecError(ValueError):
    """Raised when a problem's function spec or test data is malformed."""


# ---------------------------------------------------------------------------
# Spec validation and test-input normalisation
# ---------------------------------------------------------------------------
#
# function_spec = {
#     "name": "hasCycle",
#     "params": [{"name": "head", "type": "ListNode"},
#                {"name": "pos", "type": "int", "internal": True}],   # harness-only, not passed
#     "return_type": "bool",
#     "cycle": {"list": "head", "pos": "pos"},   # optional: link the tail to node #pos (-1 = no cycle)
# }

def validate_function_spec(spec: Optional[dict]) -> dict:
    if not isinstance(spec, dict):
        raise JudgeSpecError("function_spec is required for FUNCTION mode problems")
    name = spec.get("name", "")
    params = spec.get("params", [])
    return_type = spec.get("return_type", "")
    if not _IDENTIFIER.match(name):
        raise JudgeSpecError(f"Invalid method name: {name!r}")
    if not isinstance(params, list) or not params:
        raise JudgeSpecError("function_spec.params must be a non-empty list")
    for p in params:
        if not _IDENTIFIER.match(p.get("name", "")):
            raise JudgeSpecError(f"Invalid parameter name: {p.get('name')!r}")
        if p.get("type") not in SUPPORTED_TYPES:
            raise JudgeSpecError(f"Unsupported parameter type {p.get('type')!r}; use one of {SUPPORTED_TYPES}")
    if not any(not p.get("internal") for p in params):
        raise JudgeSpecError("At least one parameter must be passed to the method")
    if return_type not in SUPPORTED_TYPES:
        raise JudgeSpecError(f"Unsupported return type {return_type!r}; use one of {SUPPORTED_TYPES}")
    cycle = spec.get("cycle")
    if cycle:
        types = {p["name"]: p["type"] for p in params}
        if types.get(cycle.get("list")) != "ListNode" or types.get(cycle.get("pos")) != "int":
            raise JudgeSpecError("cycle must name a ListNode parameter and an int position parameter")
    return spec


def _visible_params(spec: dict) -> list[dict]:
    return [p for p in spec["params"] if not p.get("internal")]


def normalize_function_input(raw: str, spec: dict) -> str:
    """Validate one case's input (one JSON value per parameter line) and compact it."""
    lines = [ln for ln in raw.strip().splitlines() if ln.strip()]
    expected = len(spec["params"])
    if len(lines) != expected:
        raise JudgeSpecError(f"Expected {expected} input line(s) (one JSON value per parameter), got {len(lines)}")
    try:
        return "\n".join(json.dumps(json.loads(ln), separators=(",", ":")) for ln in lines)
    except json.JSONDecodeError as exc:
        raise JudgeSpecError(f"Test input is not valid JSON: {exc}") from exc


def normalize_function_output(raw: str) -> str:
    try:
        return json.dumps(json.loads(raw.strip()), separators=(",", ":"))
    except json.JSONDecodeError as exc:
        raise JudgeSpecError(f"Expected output is not valid JSON: {exc}") from exc


def describe_function_io(spec: dict, compare_mode: str) -> tuple[str, str]:
    """Default input/output format text for FUNCTION problems (shown when a problem doesn't override it)."""
    lines = []
    for i, p in enumerate(spec["params"], start=1):
        note = {
            "ListNode": "linked list given as a JSON array of node values, e.g. [1,2,3]",
            "TreeNode": "binary tree in level order with null for missing children, e.g. [3,9,20,null,null,15,7]",
        }.get(p["type"], f"{p['type']} as JSON")
        hidden = " (used only to build the input; not passed to your method)" if p.get("internal") else ""
        lines.append(f"{i}. `{p['name']}` — {note}{hidden}")
    input_format = (
        f"Implement `{spec['name']}` on class `Solution`. For custom input, give one JSON value per line, in order:\n\n"
        + "\n".join(lines)
    )
    ret = spec["return_type"]
    output_format = {
        "ListNode": "Return the head of a linked list (shown as a JSON array of values).",
        "TreeNode": "Return the root of a binary tree (shown in level order with nulls).",
    }.get(ret, f"Return a value of type `{ret}`.")
    output_format += {
        "unordered": " The order of elements in the returned list does not matter.",
        "float": " Answers within 1e-5 of the expected value are accepted.",
        "checker": " Any answer that satisfies the problem's conditions is accepted.",
    }.get(compare_mode, "")
    return input_format, output_format


# ---------------------------------------------------------------------------
# Starter code
# ---------------------------------------------------------------------------

_PY_TYPES = {
    "int": "int", "long": "int", "double": "float", "bool": "bool", "string": "str",
    "int[]": "List[int]", "long[]": "List[int]", "double[]": "List[float]", "bool[]": "List[bool]",
    "string[]": "List[str]", "int[][]": "List[List[int]]", "string[][]": "List[List[str]]",
    "ListNode": "Optional[ListNode]", "TreeNode": "Optional[TreeNode]",
}
_JAVA_TYPES = {
    "int": "int", "long": "long", "double": "double", "bool": "boolean", "string": "String",
    "int[]": "int[]", "long[]": "long[]", "double[]": "double[]", "bool[]": "boolean[]",
    "string[]": "String[]", "int[][]": "int[][]", "string[][]": "String[][]",
    "ListNode": "ListNode", "TreeNode": "TreeNode",
}
_CPP_TYPES = {
    "int": "int", "long": "long long", "double": "double", "bool": "bool", "string": "string",
    "int[]": "vector<int>", "long[]": "vector<long long>", "double[]": "vector<double>",
    "bool[]": "vector<bool>", "string[]": "vector<string>", "int[][]": "vector<vector<int>>",
    "string[][]": "vector<vector<string>>", "ListNode": "ListNode*", "TreeNode": "TreeNode*",
}

_NODE_DOCS = {
    "python": {
        "ListNode": "# ListNode is provided:\n#   class ListNode:\n#       def __init__(self, val=0, next=None): ...\n",
        "TreeNode": "# TreeNode is provided:\n#   class TreeNode:\n#       def __init__(self, val=0, left=None, right=None): ...\n",
    },
    "javascript": {
        "ListNode": "// ListNode is provided: new ListNode(val = 0, next = null)\n",
        "TreeNode": "// TreeNode is provided: new TreeNode(val = 0, left = null, right = null)\n",
    },
    "java": {
        "ListNode": "// ListNode is provided (do not redefine): int val; ListNode next; new ListNode(val), new ListNode(val, next)\n",
        "TreeNode": "// TreeNode is provided (do not redefine): int val; TreeNode left, right; new TreeNode(val)\n",
    },
    "cpp": {
        "ListNode": "// ListNode is provided (do not redefine): struct ListNode { int val; ListNode* next; ListNode(int x); };\n",
        "TreeNode": "// TreeNode is provided (do not redefine): struct TreeNode { int val; TreeNode *left, *right; TreeNode(int x); };\n",
    },
}


def _node_docs(spec: dict, language: str) -> str:
    used = {p["type"] for p in spec["params"]} | {spec["return_type"]}
    return "".join(_NODE_DOCS[language][t] for t in ("ListNode", "TreeNode") if t in used)


def starter_code(spec: dict, language: str) -> str:
    name, params, ret = spec["name"], _visible_params(spec), spec["return_type"]
    docs = _node_docs(spec, language)
    if docs:
        docs += "\n"
    if language == "python":
        args = ", ".join(f"{p['name']}: {_PY_TYPES[p['type']]}" for p in params)
        return f"{docs}class Solution:\n    def {name}(self, {args}) -> {_PY_TYPES[ret]}:\n        pass\n"
    if language == "javascript":
        doc = "\n".join(f"   * @param {{{p['type']}}} {p['name']}" for p in params)
        args = ", ".join(p["name"] for p in params)
        return (
            docs + "class Solution {\n  /**\n" + doc + f"\n   * @return {{{ret}}}\n   */\n"
            f"  {name}({args}) {{\n    \n  }}\n}}\n"
        )
    if language == "java":
        args = ", ".join(f"{_JAVA_TYPES[p['type']]} {p['name']}" for p in params)
        return f"{docs}class Solution {{\n    public {_JAVA_TYPES[ret]} {name}({args}) {{\n        \n    }}\n}}\n"
    if language == "cpp":
        def cpp_param(p):
            t = _CPP_TYPES[p["type"]]
            return f"{t}& {p['name']}" if t.startswith("vector") else f"{t} {p['name']}"
        args = ", ".join(cpp_param(p) for p in params)
        return f"{docs}class Solution {{\npublic:\n    {_CPP_TYPES[ret]} {name}({args}) {{\n        \n    }}\n}};\n"
    raise JudgeSpecError(f"Unsupported language: {language}")


SQL_STARTER = "-- Write a single SQLite SELECT statement.\nSELECT\n"


def starter_code_map(problem: PracticeProblem) -> dict[str, str]:
    if problem.judge_mode == JudgeMode.STDIO:
        return dict(problem.starter_code or {})
    if problem.judge_mode == JudgeMode.SQL:
        return {"sql": (problem.starter_code or {}).get("sql") or SQL_STARTER}
    generated = {lang: starter_code(problem.function_spec, lang) for lang in SUPPORTED_LANGUAGES}
    generated.update(problem.starter_code or {})
    return generated


# ---------------------------------------------------------------------------
# Harness generation (FUNCTION mode)
# ---------------------------------------------------------------------------
#
# Every harness reads all cases from INPUT_FILE (line 1: case count, then one JSON
# line per parameter per case), converts ListNode/TreeNode parameters, links a
# cycle when the spec asks for one, calls the student's method with the
# non-internal arguments, converts node results back to JSON, and prints one
# RESULT_MARKER line per case with the result, the case's stdout and its time.

def _cycle_indices(spec: dict) -> tuple[int, int]:
    cycle = spec.get("cycle")
    if not cycle:
        return -1, -1
    names = [p["name"] for p in spec["params"]]
    return names.index(cycle["list"]), names.index(cycle["pos"])


def _python_harness(code: str, spec: dict) -> str:
    params = spec["params"]
    in_conv = "[" + ", ".join({"ListNode": "__es_list", "TreeNode": "__es_tree"}.get(p["type"], "None") for p in params) + "]"
    visible = "[" + ", ".join("False" if p.get("internal") else "True" for p in params) + "]"
    out_conv = {"ListNode": "__es_list_out", "TreeNode": "__es_tree_out"}.get(spec["return_type"], "None")
    list_i, pos_i = _cycle_indices(spec)
    return f'''import sys, json, io, time, contextlib
from typing import *
import collections, heapq, bisect, itertools, functools, math, string
sys.setrecursionlimit(100000)


class ListNode:
    def __init__(self, val=0, next=None):
        self.val = val
        self.next = next


class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val = val
        self.left = left
        self.right = right


{code}


def __es_list(values):
    dummy = ListNode()
    cur = dummy
    for v in values:
        cur.next = ListNode(v)
        cur = cur.next
    return dummy.next


def __es_list_out(head):
    out = []
    while head is not None and len(out) < 100000:
        out.append(head.val)
        head = head.next
    return out


def __es_tree(values):
    if not values or values[0] is None:
        return None
    root = TreeNode(values[0])
    queue, i = collections.deque([root]), 1
    while queue and i < len(values):
        node = queue.popleft()
        if i < len(values) and values[i] is not None:
            node.left = TreeNode(values[i])
            queue.append(node.left)
        i += 1
        if i < len(values) and values[i] is not None:
            node.right = TreeNode(values[i])
            queue.append(node.right)
        i += 1
    return root


def __es_tree_out(root):
    out, queue, i = [], [root], 0
    while i < len(queue) and len(out) < 200000:
        node = queue[i]
        i += 1
        if node is None:
            out.append(None)
        else:
            out.append(node.val)
            queue.append(node.left)
            queue.append(node.right)
    while out and out[-1] is None:
        out.pop()
    return out


def __es_main():
    in_conv, visible, out_conv = {in_conv}, {visible}, {out_conv}
    with open("{INPUT_FILE}") as f:
        data = f.read().split("\\n")
    n, k, pos = int(data[0]), {len(params)}, 1
    out = sys.__stdout__
    for i in range(n):
        raw = [json.loads(data[pos + j]) for j in range(k)]
        pos += k
        args = [conv(v) if conv else v for conv, v in zip(in_conv, raw)]
        if {list_i} >= 0 and raw[{pos_i}] >= 0 and args[{list_i}] is not None:
            node, target, idx = args[{list_i}], None, 0
            while True:
                if idx == raw[{pos_i}]:
                    target = node
                if node.next is None:
                    break
                node, idx = node.next, idx + 1
            node.next = target
        call = [a for a, v in zip(args, visible) if v]
        buf = io.StringIO()
        t0 = time.perf_counter()
        try:
            with contextlib.redirect_stdout(buf):
                res = Solution().{spec["name"]}(*call)
            rec = {{"i": i, "ok": True, "result": out_conv(res) if out_conv else res}}
        except BaseException as e:
            rec = {{"i": i, "ok": False, "error": type(e).__name__ + ": " + str(e)}}
        rec["ms"] = (time.perf_counter() - t0) * 1000
        rec["stdout"] = buf.getvalue()[:2000]
        out.write("{RESULT_MARKER}" + json.dumps(rec) + "\\n")
        out.flush()


__es_main()
'''


def _javascript_harness(code: str, spec: dict) -> str:
    params = spec["params"]
    in_conv = "[" + ", ".join({"ListNode": "__esList", "TreeNode": "__esTree"}.get(p["type"], "null") for p in params) + "]"
    visible = "[" + ", ".join("false" if p.get("internal") else "true" for p in params) + "]"
    out_conv = {"ListNode": "__esListOut", "TreeNode": "__esTreeOut"}.get(spec["return_type"], "null")
    list_i, pos_i = _cycle_indices(spec)
    # Node classes are global properties (not declarations) so a student's own
    # `class ListNode` doesn't collide with them.
    return f'''globalThis.ListNode = class ListNode {{ constructor(val = 0, next = null) {{ this.val = val; this.next = next; }} }};
globalThis.TreeNode = class TreeNode {{ constructor(val = 0, left = null, right = null) {{ this.val = val; this.left = left; this.right = right; }} }};

{code}

;(function () {{
  const __esList = (a) => {{ const d = new ListNode(); let c = d; for (const v of a) {{ c.next = new ListNode(v); c = c.next; }} return d.next; }};
  const __esListOut = (h) => {{ const o = []; while (h && o.length < 100000) {{ o.push(h.val); h = h.next; }} return o; }};
  const __esTree = (a) => {{
    if (!a.length || a[0] === null) return null;
    const root = new TreeNode(a[0]); const q = [root]; let qi = 0, i = 1;
    while (qi < q.length && i < a.length) {{
      const node = q[qi++];
      if (i < a.length && a[i] !== null) {{ node.left = new TreeNode(a[i]); q.push(node.left); }} i++;
      if (i < a.length && a[i] !== null) {{ node.right = new TreeNode(a[i]); q.push(node.right); }} i++;
    }}
    return root;
  }};
  const __esTreeOut = (root) => {{
    const o = [], q = [root]; let i = 0;
    while (i < q.length && o.length < 200000) {{ const n = q[i++]; if (!n) o.push(null); else {{ o.push(n.val); q.push(n.left); q.push(n.right); }} }}
    while (o.length && o[o.length - 1] === null) o.pop();
    return o;
  }};
  const inConv = {in_conv}, visible = {visible}, outConv = {out_conv};
  const lines = require("fs").readFileSync("{INPUT_FILE}", "utf8").split("\\n");
  const n = parseInt(lines[0], 10), k = {len(params)};
  let pos = 1;
  const realLog = console.log;
  for (let i = 0; i < n; i++) {{
    const raw = [];
    for (let j = 0; j < k; j++) raw.push(JSON.parse(lines[pos + j]));
    pos += k;
    const args = raw.map((v, j) => (inConv[j] ? inConv[j](v) : v));
    if ({list_i} >= 0 && raw[{pos_i}] >= 0 && args[{list_i}]) {{
      let node = args[{list_i}], target = null, idx = 0;
      while (true) {{ if (idx === raw[{pos_i}]) target = node; if (!node.next) break; node = node.next; idx++; }}
      node.next = target;
    }}
    const call = args.filter((_, j) => visible[j]);
    let buf = "";
    console.log = (...a) => {{ buf += a.map(x => typeof x === "string" ? x : JSON.stringify(x)).join(" ") + "\\n"; }};
    const t0 = process.hrtime.bigint();
    let rec;
    try {{
      const res = new Solution().{spec["name"]}(...call);
      rec = {{ i, ok: true, result: res === undefined ? null : (outConv ? outConv(res) : res) }};
    }} catch (e) {{
      rec = {{ i, ok: false, error: String(e) }};
    }}
    rec.ms = Number(process.hrtime.bigint() - t0) / 1e6;
    rec.stdout = buf.slice(0, 2000);
    console.log = realLog;
    process.stdout.write("{RESULT_MARKER}" + JSON.stringify(rec) + "\\n");
  }}
}})();
'''


_JAVA_CONVERTERS = {
    "int": "((Number) {v}).intValue()",
    "long": "((Number) {v}).longValue()",
    "double": "((Number) {v}).doubleValue()",
    "bool": "(Boolean) {v}",
    "string": "(String) {v}",
    "int[]": "__J.intArr({v})",
    "long[]": "__J.longArr({v})",
    "double[]": "__J.doubleArr({v})",
    "bool[]": "__J.boolArr({v})",
    "string[]": "__J.strArr({v})",
    "int[][]": "__J.intArr2({v})",
    "string[][]": "__J.strArr2({v})",
    "ListNode": "__J.list({v})",
    "TreeNode": "__J.tree({v})",
}

_JAVA_SUPPORT = r'''
class ListNode {
    int val; ListNode next;
    ListNode() {}
    ListNode(int val) { this.val = val; }
    ListNode(int val, ListNode next) { this.val = val; this.next = next; }
}
class TreeNode {
    int val; TreeNode left; TreeNode right;
    TreeNode() {}
    TreeNode(int val) { this.val = val; }
    TreeNode(int val, TreeNode left, TreeNode right) { this.val = val; this.left = left; this.right = right; }
}
class __J {
    static String src; static int p;
    static Object parse(String s) { src = s; p = 0; return val(); }
    static void ws() { while (p < src.length() && Character.isWhitespace(src.charAt(p))) p++; }
    static Object val() {
        ws(); char c = src.charAt(p);
        if (c == '[') { p++; List<Object> l = new ArrayList<>(); ws();
            if (src.charAt(p) == ']') { p++; return l; }
            while (true) { l.add(val()); ws(); if (src.charAt(p) == ',') { p++; continue; } p++; return l; } }
        if (c == '"') { p++; StringBuilder b = new StringBuilder();
            while (src.charAt(p) != '"') { char ch = src.charAt(p++);
                if (ch == '\\') { char e = src.charAt(p++);
                    switch (e) { case 'n': b.append('\n'); break; case 't': b.append('\t'); break;
                        case 'r': b.append('\r'); break; case 'b': b.append('\b'); break; case 'f': b.append('\f'); break;
                        case 'u': b.append((char) Integer.parseInt(src.substring(p, p + 4), 16)); p += 4; break;
                        default: b.append(e); } }
                else b.append(ch); }
            p++; return b.toString(); }
        if (src.startsWith("true", p)) { p += 4; return Boolean.TRUE; }
        if (src.startsWith("false", p)) { p += 5; return Boolean.FALSE; }
        if (src.startsWith("null", p)) { p += 4; return null; }
        int st = p; while (p < src.length() && "+-0123456789.eE".indexOf(src.charAt(p)) >= 0) p++;
        String num = src.substring(st, p);
        if (num.contains(".") || num.contains("e") || num.contains("E")) return Double.parseDouble(num);
        return Long.parseLong(num);
    }
    @SuppressWarnings("unchecked") static List<Object> L(Object o) { return (List<Object>) o; }
    static int[] intArr(Object o) { List<Object> l = L(o); int[] r = new int[l.size()]; for (int i = 0; i < r.length; i++) r[i] = ((Number) l.get(i)).intValue(); return r; }
    static long[] longArr(Object o) { List<Object> l = L(o); long[] r = new long[l.size()]; for (int i = 0; i < r.length; i++) r[i] = ((Number) l.get(i)).longValue(); return r; }
    static double[] doubleArr(Object o) { List<Object> l = L(o); double[] r = new double[l.size()]; for (int i = 0; i < r.length; i++) r[i] = ((Number) l.get(i)).doubleValue(); return r; }
    static boolean[] boolArr(Object o) { List<Object> l = L(o); boolean[] r = new boolean[l.size()]; for (int i = 0; i < r.length; i++) r[i] = (Boolean) l.get(i); return r; }
    static String[] strArr(Object o) { List<Object> l = L(o); String[] r = new String[l.size()]; for (int i = 0; i < r.length; i++) r[i] = (String) l.get(i); return r; }
    static int[][] intArr2(Object o) { List<Object> l = L(o); int[][] r = new int[l.size()][]; for (int i = 0; i < r.length; i++) r[i] = intArr(l.get(i)); return r; }
    static String[][] strArr2(Object o) { List<Object> l = L(o); String[][] r = new String[l.size()][]; for (int i = 0; i < r.length; i++) r[i] = strArr(l.get(i)); return r; }
    static ListNode list(Object o) { ListNode d = new ListNode(0), c = d;
        for (Object x : L(o)) { c.next = new ListNode(((Number) x).intValue()); c = c.next; } return d.next; }
    static void cycle(ListNode h, int pos) { if (h == null || pos < 0) return; ListNode t = h, target = null; int i = 0;
        while (true) { if (i == pos) target = t; if (t.next == null) break; t = t.next; i++; } t.next = target; }
    static TreeNode tree(Object o) { List<Object> l = L(o); if (l.isEmpty() || l.get(0) == null) return null;
        TreeNode root = new TreeNode(((Number) l.get(0)).intValue()); ArrayDeque<TreeNode> q = new ArrayDeque<>(); q.add(root); int i = 1;
        while (!q.isEmpty() && i < l.size()) { TreeNode n = q.poll();
            if (i < l.size() && l.get(i) != null) { n.left = new TreeNode(((Number) l.get(i)).intValue()); q.add(n.left); } i++;
            if (i < l.size() && l.get(i) != null) { n.right = new TreeNode(((Number) l.get(i)).intValue()); q.add(n.right); } i++; }
        return root; }
    static String str(String s) { StringBuilder b = new StringBuilder("\"");
        for (char c : s.toCharArray()) { switch (c) { case '"': b.append("\\\""); break; case '\\': b.append("\\\\"); break;
            case '\n': b.append("\\n"); break; case '\r': b.append("\\r"); break; case '\t': b.append("\\t"); break;
            default: if (c < 0x20) b.append(String.format("\\u%04x", (int) c)); else b.append(c); } }
        return b.append('"').toString(); }
    static String json(Object o) {
        if (o == null) return "null";
        if (o instanceof ListNode) { StringBuilder b = new StringBuilder("["); ListNode h = (ListNode) o; int n = 0;
            while (h != null && n < 100000) { if (n++ > 0) b.append(','); b.append(h.val); h = h.next; } return b.append(']').toString(); }
        if (o instanceof TreeNode) { List<TreeNode> q = new ArrayList<>(); q.add((TreeNode) o); List<String> out = new ArrayList<>();
            for (int i = 0; i < q.size() && out.size() < 200000; i++) { TreeNode n = q.get(i);
                if (n == null) out.add("null"); else { out.add(String.valueOf(n.val)); q.add(n.left); q.add(n.right); } }
            while (!out.isEmpty() && out.get(out.size() - 1).equals("null")) out.remove(out.size() - 1);
            return "[" + String.join(",", out) + "]"; }
        if (o instanceof String) return str((String) o);
        if (o instanceof Character) return str(String.valueOf(o));
        if (o instanceof Double || o instanceof Float) { double d = ((Number) o).doubleValue();
            if (Double.isNaN(d) || Double.isInfinite(d)) return "null"; return Double.toString(d); }
        if (o instanceof Number || o instanceof Boolean) return o.toString();
        if (o.getClass().isArray()) { int n = java.lang.reflect.Array.getLength(o); StringBuilder b = new StringBuilder("[");
            for (int i = 0; i < n; i++) { if (i > 0) b.append(','); b.append(json(java.lang.reflect.Array.get(o, i))); } return b.append(']').toString(); }
        if (o instanceof Iterable) { StringBuilder b = new StringBuilder("["); boolean first = true;
            for (Object x : (Iterable<?>) o) { if (!first) b.append(','); first = false; b.append(json(x)); } return b.append(']').toString(); }
        return str(o.toString());
    }
}
'''


def _java_harness(code: str, spec: dict) -> str:
    # Hoist the student's import lines above the generated classes.
    imports, body = [], []
    for line in code.splitlines():
        (imports if line.strip().startswith("import ") else body).append(line)
    params = spec["params"]
    decls = "\n".join(
        f"                {_JAVA_TYPES[p['type']]} __a{j} = "
        + _JAVA_CONVERTERS[p["type"]].format(v=f"__J.parse(lines[pos + {j}])") + ";"
        for j, p in enumerate(params)
    )
    list_i, pos_i = _cycle_indices(spec)
    if list_i >= 0:
        decls += f"\n                __J.cycle(__a{list_i}, __a{pos_i});"
    call_args = ", ".join(f"__a{j}" for j, p in enumerate(params) if not p.get("internal"))
    # A null list/tree has no runtime type to dispatch on: serialise it as [] like the other languages.
    result_json = '(res == null ? "[]" : __J.json(res))' if spec["return_type"] in ("ListNode", "TreeNode") else "__J.json(res)"
    # Java's single-file source launcher runs the FIRST top-level class, so Main
    # goes first; the student's Solution and the helpers follow it.
    return (
        "import java.util.*;\nimport java.io.*;\n" + "\n".join(imports) + "\n" + f'''
public class Main {{
    public static void main(String[] argv) throws Exception {{
        BufferedReader in = new BufferedReader(new FileReader("{INPUT_FILE}"));
        List<String> all = new ArrayList<>(); String ln;
        while ((ln = in.readLine()) != null) all.add(ln);
        String[] lines = all.toArray(new String[0]);
        int n = Integer.parseInt(lines[0].trim()), k = {len(params)}, pos = 1;
        PrintStream realOut = System.out;
        for (int i = 0; i < n; i++) {{
            ByteArrayOutputStream buf = new ByteArrayOutputStream();
            System.setOut(new PrintStream(buf, true));
            long t0 = System.nanoTime();
            String rec;
            try {{
{decls}
                Object res = new Solution().{spec["name"]}({call_args});
                rec = "{{\\"i\\":" + i + ",\\"ok\\":true,\\"result\\":" + {result_json};
            }} catch (Throwable e) {{
                rec = "{{\\"i\\":" + i + ",\\"ok\\":false,\\"error\\":" + __J.str(e.toString());
            }}
            double ms = (System.nanoTime() - t0) / 1e6;
            System.setOut(realOut);
            String so = buf.toString();
            if (so.length() > 2000) so = so.substring(0, 2000);
            realOut.println("{RESULT_MARKER}" + rec + ",\\"ms\\":" + ms + ",\\"stdout\\":" + __J.str(so) + "}}");
            realOut.flush();
            pos += k;
        }}
    }}
}}
''' + "\n".join(body) + "\n" + _JAVA_SUPPORT
    )


# Node types must be declared before the student's code (C++ needs declarations first).
_CPP_NODES = r'''
struct ListNode {
    int val; ListNode *next;
    ListNode() : val(0), next(nullptr) {}
    ListNode(int x) : val(x), next(nullptr) {}
    ListNode(int x, ListNode *next) : val(x), next(next) {}
};
struct TreeNode {
    int val; TreeNode *left; TreeNode *right;
    TreeNode() : val(0), left(nullptr), right(nullptr) {}
    TreeNode(int x) : val(x), left(nullptr), right(nullptr) {}
    TreeNode(int x, TreeNode *left, TreeNode *right) : val(x), left(left), right(right) {}
};
'''

_CPP_SUPPORT = r'''
struct __JV { char t = 'n'; std::string raw; std::vector<__JV> a; };
struct __JP {
    const std::string& s; size_t p = 0;
    explicit __JP(const std::string& src) : s(src) {}
    void ws() { while (p < s.size() && isspace((unsigned char) s[p])) p++; }
    __JV val() {
        ws(); __JV v; char c = s[p];
        if (c == '[') { p++; v.t = 'a'; ws(); if (s[p] == ']') { p++; return v; }
            while (true) { v.a.push_back(val()); ws(); if (s[p] == ',') { p++; continue; } p++; return v; } }
        if (c == '"') { p++; v.t = 's';
            while (s[p] != '"') { char ch = s[p++];
                if (ch == '\\') { char e = s[p++];
                    if (e == 'n') v.raw += '\n'; else if (e == 't') v.raw += '\t'; else if (e == 'r') v.raw += '\r';
                    else if (e == 'u') { v.raw += (char) std::stoi(s.substr(p, 4), nullptr, 16); p += 4; }
                    else v.raw += e; }
                else v.raw += ch; }
            p++; return v; }
        if (s.compare(p, 4, "true") == 0) { p += 4; v.t = 'b'; v.raw = "1"; return v; }
        if (s.compare(p, 5, "false") == 0) { p += 5; v.t = 'b'; v.raw = "0"; return v; }
        if (s.compare(p, 4, "null") == 0) { p += 4; return v; }
        size_t st = p; while (p < s.size() && std::string("+-0123456789.eE").find(s[p]) != std::string::npos) p++;
        v.t = 'd'; v.raw = s.substr(st, p - st); return v;
    }
};
template <typename T> struct __Cv;
template <> struct __Cv<int> { static int f(const __JV& v) { return (int) std::stoll(v.raw); } };
template <> struct __Cv<long long> { static long long f(const __JV& v) { return std::stoll(v.raw); } };
template <> struct __Cv<double> { static double f(const __JV& v) { return std::stod(v.raw); } };
template <> struct __Cv<bool> { static bool f(const __JV& v) { return v.raw == "1"; } };
template <> struct __Cv<std::string> { static std::string f(const __JV& v) { return v.raw; } };
template <typename T> struct __Cv<std::vector<T>> { static std::vector<T> f(const __JV& v) {
    std::vector<T> r; for (const auto& e : v.a) r.push_back(__Cv<T>::f(e)); return r; } };
template <> struct __Cv<ListNode*> { static ListNode* f(const __JV& v) {
    ListNode d; ListNode* c = &d; for (const auto& e : v.a) { c->next = new ListNode((int) std::stoll(e.raw)); c = c->next; } return d.next; } };
template <> struct __Cv<TreeNode*> { static TreeNode* f(const __JV& v) {
    if (v.a.empty() || v.a[0].t == 'n') return nullptr;
    TreeNode* root = new TreeNode((int) std::stoll(v.a[0].raw)); std::deque<TreeNode*> q{root}; size_t i = 1;
    while (!q.empty() && i < v.a.size()) { TreeNode* n = q.front(); q.pop_front();
        if (i < v.a.size() && v.a[i].t != 'n') { n->left = new TreeNode((int) std::stoll(v.a[i].raw)); q.push_back(n->left); } i++;
        if (i < v.a.size() && v.a[i].t != 'n') { n->right = new TreeNode((int) std::stoll(v.a[i].raw)); q.push_back(n->right); } i++; }
    return root; } };
inline void __es_cycle(ListNode* h, int pos) { if (!h || pos < 0) return; ListNode* t = h; ListNode* target = nullptr; int i = 0;
    while (true) { if (i == pos) target = t; if (!t->next) break; t = t->next; i++; } t->next = target; }
inline std::string __js(const std::string& x) { std::string o = "\"";
    for (char c : x) { if (c == '"') o += "\\\""; else if (c == '\\') o += "\\\\"; else if (c == '\n') o += "\\n";
        else if (c == '\r') o += "\\r"; else if (c == '\t') o += "\\t";
        else if ((unsigned char) c < 0x20) { char b[8]; snprintf(b, sizeof b, "\\u%04x", c); o += b; } else o += c; }
    return o + "\""; }
inline std::string __js(int x) { return std::to_string(x); }
inline std::string __js(long long x) { return std::to_string(x); }
inline std::string __js(bool x) { return x ? "true" : "false"; }
inline std::string __js(double x) { if (std::isnan(x) || std::isinf(x)) return "null";
    char b[64]; snprintf(b, sizeof b, "%.17g", x); return b; }
inline std::string __js(ListNode* h) { std::string o = "["; int n = 0;
    while (h && n < 100000) { if (n++) o += ","; o += std::to_string(h->val); h = h->next; } return o + "]"; }
inline std::string __js(TreeNode* root) { std::vector<TreeNode*> q{root}; std::vector<std::string> out;
    for (size_t i = 0; i < q.size() && out.size() < 200000; i++) { TreeNode* n = q[i];
        if (!n) out.push_back("null"); else { out.push_back(std::to_string(n->val)); q.push_back(n->left); q.push_back(n->right); } }
    while (!out.empty() && out.back() == "null") out.pop_back();
    std::string o = "["; for (size_t i = 0; i < out.size(); i++) { if (i) o += ","; o += out[i]; } return o + "]"; }
template <typename T> std::string __js(const std::vector<T>& v) { std::string o = "[";
    for (size_t i = 0; i < v.size(); i++) { if (i) o += ","; T x = v[i]; o += __js(x); } return o + "]"; }
'''


def _cpp_harness(code: str, spec: dict) -> str:
    params = spec["params"]
    decls = "\n".join(
        f"            auto __a{j} = __Cv<{_CPP_TYPES[p['type']]}>::f(__JP(lines[pos + {j}]).val());"
        for j, p in enumerate(params)
    )
    list_i, pos_i = _cycle_indices(spec)
    if list_i >= 0:
        decls += f"\n            __es_cycle(__a{list_i}, __a{pos_i});"
    call_args = ", ".join(f"__a{j}" for j, p in enumerate(params) if not p.get("internal"))
    return (
        "#include <bits/stdc++.h>\nusing namespace std;\n" + _CPP_NODES + "\n" + code + "\n" + _CPP_SUPPORT + f'''
int main() {{
    ios::sync_with_stdio(true);
    vector<string> lines; string ln;
    ifstream __in("{INPUT_FILE}");
    while (getline(__in, ln)) lines.push_back(ln);
    int n = stoi(lines[0]), k = {len(params)}, pos = 1;
    streambuf* realBuf = cout.rdbuf();
    for (int i = 0; i < n; i++) {{
        ostringstream buf;
        cout.rdbuf(buf.rdbuf());
        auto t0 = chrono::steady_clock::now();
        string rec;
        try {{
{decls}
            Solution __sol;
            auto __res = __sol.{spec["name"]}({call_args});
            rec = "{{\\"i\\":" + to_string(i) + ",\\"ok\\":true,\\"result\\":" + __js(__res);
        }} catch (const exception& e) {{
            rec = "{{\\"i\\":" + to_string(i) + ",\\"ok\\":false,\\"error\\":" + __js(string(e.what()));
        }} catch (...) {{
            rec = "{{\\"i\\":" + to_string(i) + ",\\"ok\\":false,\\"error\\":\\"unknown exception\\"";
        }}
        double ms = chrono::duration<double, milli>(chrono::steady_clock::now() - t0).count();
        cout.rdbuf(realBuf);
        string so = buf.str().substr(0, 2000);
        cout << "{RESULT_MARKER}" << rec << ",\\"ms\\":" << ms << ",\\"stdout\\":" << __js(so) << "}}" << endl;
        pos += k;
    }}
    return 0;
}}
'''
    )


_HARNESS = {
    "python": _python_harness,
    "javascript": _javascript_harness,
    "java": _java_harness,
    "cpp": _cpp_harness,
}


def build_harness(code: str, spec: dict, language: str) -> str:
    if language not in _HARNESS:
        raise JudgeSpecError(f"Unsupported language: {language}")
    return _HARNESS[language](code, spec)


# ---------------------------------------------------------------------------
# Comparison
# ---------------------------------------------------------------------------

def _close(a: Any, b: Any) -> bool:
    if isinstance(a, bool) or isinstance(b, bool):
        return a is b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return math.isclose(a, b, rel_tol=1e-5, abs_tol=1e-5)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(_close(x, y) for x, y in zip(a, b))
    return a == b


def _strict_equal(a: Any, b: Any) -> bool:
    # JSON true must not equal 1, but 2 and 2.0 are the same number.
    if isinstance(a, bool) or isinstance(b, bool):
        return a is b
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(_strict_equal(x, y) for x, y in zip(a, b))
    return a == b


_checker_cache: dict[str, Any] = {}


def run_checker(problem: PracticeProblem, case_input: str, actual: Any, expected: Any) -> bool:
    """Problem-specific validation for questions with several valid answers.

    ``problem.checker`` is Python source defining ``check(args, output, expected) -> bool``.
    Checkers come only from the repository's question bank (the admin API never
    accepts them), because they run inside the API process, not the sandbox.
    """
    source = getattr(problem, "checker", None)
    if not source:
        raise JudgeSpecError("compare_mode 'checker' requires a checker")
    fn = _checker_cache.get(source)
    if fn is None:
        namespace: dict[str, Any] = {}
        exec(compile(source, f"<checker {getattr(problem, 'slug', '?')}>", "exec"), namespace)  # noqa: S102 (trusted bank code)
        fn = _checker_cache[source] = namespace["check"]
    args = [json.loads(line) for line in case_input.splitlines() if line.strip()]
    try:
        return bool(fn(args, actual, expected))
    except Exception:
        return False  # malformed output (wrong type/shape) is a wrong answer


def outputs_match(actual: Any, expected: Any, compare_mode: str) -> bool:
    if compare_mode == "float":
        return _close(actual, expected)
    if compare_mode == "unordered" and isinstance(actual, list) and isinstance(expected, list):
        key = lambda x: json.dumps(x, sort_keys=True)  # noqa: E731
        return _strict_equal(sorted(actual, key=key), sorted(expected, key=key))
    return _strict_equal(actual, expected)


def _normalize_text(s: str) -> str:
    return "\n".join(line.rstrip() for line in s.strip().splitlines())


# ---------------------------------------------------------------------------
# Running
# ---------------------------------------------------------------------------

@dataclass
class JudgeCase:
    input: str
    expected: Optional[str]  # None for custom input with no reference answer
    is_sample: bool = True


@dataclass
class CaseResult:
    index: int
    passed: Optional[bool]
    output: Optional[str] = None
    stdout: str = ""
    runtime_ms: Optional[float] = None
    error: Optional[str] = None


@dataclass
class JudgeOutcome:
    verdict: Verdict
    cases: list[CaseResult] = field(default_factory=list)
    passed_count: int = 0
    total_count: int = 0
    runtime_ms: Optional[int] = None
    compile_output: Optional[str] = None
    error: Optional[str] = None
    failed_index: Optional[int] = None


def _is_launcher_compile_error(result: SandboxResult, language: str) -> bool:
    # Piston runs Java via the single-file source launcher, which compiles at
    # run time and reports failures on stderr with this trailer.
    return language == "java" and "error: compilation failed" in (result.stderr or "")


def _clean_compile_output(text: str) -> str:
    noise = ("chmod: cannot access", "error: compilation failed")
    lines = [ln for ln in (text or "").splitlines() if not ln.startswith(noise)]
    return "\n".join(lines).strip()[-4000:]


def _crash_verdict(sandbox_status: str) -> Verdict:
    return {
        "timeout": Verdict.TIME_LIMIT_EXCEEDED,
        "memory_limit": Verdict.MEMORY_LIMIT_EXCEEDED,
        "output_limit": Verdict.OUTPUT_LIMIT_EXCEEDED,
    }.get(sandbox_status, Verdict.RUNTIME_ERROR)


async def _run_function_mode(
    problem: PracticeProblem, language: str, code: str, cases: list[JudgeCase], stop_on_failure: bool
) -> JudgeOutcome:
    spec = problem.function_spec
    test_data = "\n".join([str(len(cases))] + [c.input for c in cases]) + "\n"
    total_timeout_ms = min(MAX_TOTAL_RUN_MS, max(3000, problem.time_limit_ms * len(cases) + 1000))
    result: SandboxResult = await sandbox_service.execute_async(
        language, build_harness(code, spec, language), "", total_timeout_ms / 1000, problem.memory_limit_mb,
        extra_files={INPUT_FILE: test_data},
    )
    outcome = JudgeOutcome(verdict=Verdict.ACCEPTED, total_count=len(cases))
    if result.status == "compile_error" or _is_launcher_compile_error(result, language):
        outcome.verdict = Verdict.COMPILE_ERROR
        outcome.compile_output = _clean_compile_output(result.compile_output or result.stderr)
        return outcome
    if result.status == "system_error":
        outcome.verdict, outcome.error = Verdict.SYSTEM_ERROR, result.stderr
        return outcome

    records: dict[int, dict] = {}
    for line in result.stdout.splitlines():
        if line.startswith(RESULT_MARKER):
            try:
                rec = json.loads(line[len(RESULT_MARKER):])
                records[int(rec["i"])] = rec
            except (ValueError, KeyError):
                continue

    total_ms = 0.0
    for i, case in enumerate(cases):
        rec = records.get(i)
        if rec is None:
            # Process died (or was killed) before finishing this case.
            verdict = _crash_verdict(result.status)
            stderr_tail = (result.stderr or "").strip()[-1500:]
            outcome.cases.append(CaseResult(i, False, error=stderr_tail or verdict.value))
            outcome.verdict, outcome.failed_index, outcome.error = verdict, i, stderr_tail or None
            break
        ms = float(rec.get("ms") or 0.0)
        total_ms += ms
        if not rec.get("ok"):
            outcome.cases.append(CaseResult(i, False, stdout=rec.get("stdout", ""), runtime_ms=ms, error=rec.get("error")))
            if outcome.verdict == Verdict.ACCEPTED:
                outcome.verdict, outcome.failed_index, outcome.error = Verdict.RUNTIME_ERROR, i, rec.get("error")
            if stop_on_failure:
                break
            continue
        output = json.dumps(rec.get("result"), separators=(",", ":"))
        passed: Optional[bool] = None
        if case.expected is not None:
            if problem.compare_mode == "checker":
                passed = run_checker(problem, case.input, rec.get("result"), json.loads(case.expected))
            else:
                passed = outputs_match(rec.get("result"), json.loads(case.expected), problem.compare_mode)
        if passed and ms > problem.time_limit_ms:
            passed = False
            if outcome.verdict == Verdict.ACCEPTED:
                outcome.verdict, outcome.failed_index = Verdict.TIME_LIMIT_EXCEEDED, i
        outcome.cases.append(CaseResult(i, passed, output=output, stdout=rec.get("stdout", ""), runtime_ms=ms))
        if passed:
            outcome.passed_count += 1
        elif passed is False and outcome.verdict == Verdict.ACCEPTED:
            outcome.verdict, outcome.failed_index = Verdict.WRONG_ANSWER, i
        if passed is False and stop_on_failure:
            break
    outcome.runtime_ms = int(round(total_ms))
    return outcome


async def _run_stdio_mode(
    problem: PracticeProblem, language: str, code: str, cases: list[JudgeCase], stop_on_failure: bool
) -> JudgeOutcome:
    timeout_sec = problem.time_limit_ms / 1000
    results = await asyncio.gather(*[
        sandbox_service.execute_async(language, code, c.input, timeout_sec, problem.memory_limit_mb) for c in cases
    ])
    outcome = JudgeOutcome(verdict=Verdict.ACCEPTED, total_count=len(cases))
    total_ms = 0
    for i, (case, res) in enumerate(zip(cases, results)):
        if res.status == "compile_error" or _is_launcher_compile_error(res, language):
            outcome.verdict = Verdict.COMPILE_ERROR
            outcome.compile_output = _clean_compile_output(res.compile_output or res.stderr)
            return outcome
        if res.status == "system_error":
            outcome.verdict, outcome.error = Verdict.SYSTEM_ERROR, res.stderr
            return outcome
        total_ms += res.wall_time_ms
        if res.status != "success":
            verdict = _crash_verdict(res.status)
            outcome.cases.append(CaseResult(i, False, stdout=res.stdout[:2000], runtime_ms=res.wall_time_ms, error=res.stderr[-1500:]))
            if outcome.verdict == Verdict.ACCEPTED:
                outcome.verdict, outcome.failed_index, outcome.error = verdict, i, res.stderr[-1500:]
            if stop_on_failure:
                break
            continue
        passed = None if case.expected is None else _normalize_text(res.stdout) == _normalize_text(case.expected)
        outcome.cases.append(CaseResult(i, passed, output=res.stdout[:2000], runtime_ms=res.wall_time_ms))
        if passed:
            outcome.passed_count += 1
        elif passed is False:
            if outcome.verdict == Verdict.ACCEPTED:
                outcome.verdict, outcome.failed_index = Verdict.WRONG_ANSWER, i
            if stop_on_failure:
                break
    outcome.runtime_ms = total_ms
    return outcome


def sql_rows_match(actual: list, expected: list, ordered: bool) -> bool:
    """Compare result rows; numbers within 1e-6 (SQLite and Python print floats differently)."""
    if len(actual) != len(expected):
        return False
    if not ordered:
        key = lambda row: json.dumps([round(v, 6) if isinstance(v, float) else v for v in row], default=str)  # noqa: E731
        actual, expected = sorted(actual, key=key), sorted(expected, key=key)
    return all(_close(a, e) for a, e in zip(actual, expected))


def _parse_sql_rows(stdout: str) -> list[list]:
    """`.mode json` prints one array of row objects per statement; exactly one is expected."""
    text = stdout.strip()
    if not text:
        return []  # no rows
    decoder = json.JSONDecoder()
    rows, end = decoder.raw_decode(text)
    if text[end:].strip():
        raise ValueError("Your query produced more than one result set. Submit a single SELECT statement.")
    return [list(row.values()) for row in rows]


async def _run_sql_mode(
    problem: PracticeProblem, code: str, cases: list[JudgeCase], stop_on_failure: bool
) -> JudgeOutcome:
    query = code.strip()
    if not query:
        return JudgeOutcome(verdict=Verdict.COMPILE_ERROR, compile_output="Empty query", total_count=len(cases))
    timeout_sec = problem.time_limit_ms / 1000
    scripts = [
        f"{problem.sql_schema or ''}\n{case.input}\n.bail on\n.mode json\n{query}\n"
        for case in cases
    ]
    results = await asyncio.gather(*[
        sandbox_service.execute_async("sql", script, "", timeout_sec, problem.memory_limit_mb) for script in scripts
    ])
    outcome = JudgeOutcome(verdict=Verdict.ACCEPTED, total_count=len(cases))
    total_ms = 0
    ordered = problem.compare_mode == "exact"
    for i, (case, res) in enumerate(zip(cases, results)):
        if res.status == "system_error":
            outcome.verdict, outcome.error = Verdict.SYSTEM_ERROR, res.stderr
            return outcome
        total_ms += res.wall_time_ms
        error = None
        if res.status in ("timeout", "memory_limit", "output_limit"):
            verdict = _crash_verdict(res.status)
            error = verdict.value
        elif res.status != "success" or res.stderr.strip():
            # sqlite3 reports syntax/semantic errors as "Error: near line N: …"
            verdict, error = Verdict.RUNTIME_ERROR, re.sub(r"near line \d+: ", "", res.stderr.strip())[:1500]
        else:
            try:
                rows = _parse_sql_rows(res.stdout)
            except ValueError as exc:
                verdict, error = Verdict.RUNTIME_ERROR, str(exc)
            else:
                output = json.dumps(rows, separators=(",", ":"), default=str)
                passed = None if case.expected is None else sql_rows_match(rows, json.loads(case.expected), ordered)
                outcome.cases.append(CaseResult(i, passed, output=output, runtime_ms=res.wall_time_ms))
                if passed:
                    outcome.passed_count += 1
                elif passed is False:
                    if outcome.verdict == Verdict.ACCEPTED:
                        outcome.verdict, outcome.failed_index = Verdict.WRONG_ANSWER, i
                    if stop_on_failure:
                        break
                continue
        outcome.cases.append(CaseResult(i, False, runtime_ms=res.wall_time_ms, error=error))
        if outcome.verdict == Verdict.ACCEPTED:
            outcome.verdict, outcome.failed_index, outcome.error = verdict, i, error
        if stop_on_failure:
            break
    outcome.runtime_ms = total_ms
    return outcome


async def judge(
    problem: PracticeProblem, language: str, code: str, cases: list[JudgeCase], stop_on_failure: bool = False
) -> JudgeOutcome:
    language = "cpp" if language in ("c++", "cpp") else language
    if problem.judge_mode == JudgeMode.SQL:
        if language != "sql":
            raise JudgeSpecError("SQL problems are answered in SQL")
        return await _run_sql_mode(problem, code, cases, stop_on_failure)
    if problem.judge_mode == JudgeMode.FUNCTION:
        if language not in SUPPORTED_LANGUAGES:
            raise JudgeSpecError(f"{language} is not supported for this problem")
        return await _run_function_mode(problem, language, code, cases, stop_on_failure)
    return await _run_stdio_mode(problem, language, code, cases, stop_on_failure)
