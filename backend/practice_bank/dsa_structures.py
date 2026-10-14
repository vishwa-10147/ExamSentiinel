"""#82–#103: Stacks & Queues, Recursion & Backtracking, Trees & BST, Heaps."""

import math

from practice_bank.common import E, H, M, JudgeMode, problem, rand_ints, rng, spec

# ---------------------------------------------------------------- helpers

def _ops_queue(n: int) -> str:
    ops, size = [], 0
    for _ in range(n):
        r = rng.random()
        if size == 0 or r < 0.45:
            ops.append(f"push {rng.randint(-10**9, 10**9)}")
            size += 1
        elif r < 0.7:
            ops.append("pop")
            size -= 1
        elif r < 0.9:
            ops.append("peek")
        else:
            ops.append("empty")
    return f"{len(ops)}\n" + "\n".join(ops) + "\n"


def _ops_minstack(n: int) -> str:
    ops, size = [], 0
    for _ in range(n):
        r = rng.random()
        if size == 0 or r < 0.45:
            ops.append(f"push {rng.randint(-10**9, 10**9)}")
            size += 1
        elif r < 0.65:
            ops.append("pop")
            size -= 1
        elif r < 0.82:
            ops.append("top")
        else:
            ops.append("min")
    return f"{len(ops)}\n" + "\n".join(ops) + "\n"


def _stdio_starters(comment: str) -> dict:
    return {
        "python": f"import sys\n\n# {comment}\nlines = sys.stdin.read().split('\\n')\nq = int(lines[0])\nfor line in lines[1:q + 1]:\n    parts = line.split()\n    \n",
        "javascript": f"// {comment}\nconst lines = require('fs').readFileSync(0, 'utf8').split('\\n');\nconst q = parseInt(lines[0], 10);\nconst out = [];\nfor (let i = 1; i <= q; i++) {{\n  const parts = lines[i].trim().split(' ');\n  \n}}\nconsole.log(out.join('\\n'));\n",
        "java": f"import java.util.*;\nimport java.io.*;\n\n// {comment}\npublic class Main {{\n    public static void main(String[] args) throws IOException {{\n        BufferedReader in = new BufferedReader(new InputStreamReader(System.in));\n        int q = Integer.parseInt(in.readLine().trim());\n        StringBuilder out = new StringBuilder();\n        for (int i = 0; i < q; i++) {{\n            String[] parts = in.readLine().trim().split(\" \");\n            \n        }}\n        System.out.print(out);\n    }}\n}}\n",
        "cpp": f"#include <bits/stdc++.h>\nusing namespace std;\n\n// {comment}\nint main() {{\n    ios::sync_with_stdio(false); cin.tie(nullptr);\n    int q; cin >> q;\n    while (q--) {{\n        string op; cin >> op;\n        \n    }}\n    return 0;\n}}\n",
        "c": f"#include <stdio.h>\n#include <string.h>\n\n/* {comment} */\nint main(void) {{\n    int q; scanf(\"%d\", &q);\n    char op[16];\n    while (q-- > 0) {{\n        scanf(\"%15s\", op);\n        \n    }}\n    return 0;\n}}\n",
    }


def _random_tree(n: int, lo: int = -1000, hi: int = 1000, null_rate: float = 0.25) -> list:
    """Level-order array (with nulls) of a random binary tree with n nodes."""
    if n == 0:
        return []
    out, open_slots, made = [rng.randint(lo, hi)], 2, 1
    while made < n:
        if rng.random() < null_rate and open_slots > 1:
            out.append(None)
            open_slots -= 1
        else:
            out.append(rng.randint(lo, hi))
            made += 1
            open_slots += 1
    return out


def _bst_level_order(values: list[int]) -> list:
    """Level-order array of the BST obtained by inserting values in the given order."""
    left, right, root = {}, {}, None
    for v in values:
        if root is None:
            root = v
            continue
        cur = root
        while True:
            side = left if v < cur else right
            if cur not in side:
                side[cur] = v
                break
            cur = side[cur]
    out, queue, i = [], [root], 0
    while i < len(queue):
        node = queue[i]
        i += 1
        if node is None:
            out.append(None)
        else:
            out.append(node)
            queue.append(left.get(node))
            queue.append(right.get(node))
    while out and out[-1] is None:
        out.pop()
    return out


def _unique_values_tree(n: int) -> tuple[list, list[int]]:
    values = rng.sample(range(-10**5, 10**5), n)
    tree, idx = [], 0
    for v in _random_tree(n):
        if v is None:
            tree.append(None)
        else:
            tree.append(values[idx])
            idx += 1
    return tree, values


# ================================================================ Stacks & Queues

problem(
    number=82, topic="Stacks & Queues", slug="queue-from-two-stacks", title="Queue From Two Stacks", difficulty=M,
    tags=["stack", "queue", "design"], complexity="Amortised O(1) per operation",
    statement=(
        "Implement a first-in-first-out queue **using only two stacks** (push to top, pop from top, look at top, size). "
        "Process the operations from standard input:\n\n"
        "- `push x` — add x to the back of the queue\n- `pop` — remove the front element and print it\n"
        "- `peek` — print the front element\n- `empty` — print `true` or `false`\n\n"
        "`pop` and `peek` are only issued when the queue is non-empty. This problem is judged on output; using two stacks is the intended technique."
    ),
    input_format="Line 1: number of operations `q`.\nNext `q` lines: one operation each.",
    output_format="One line for every `pop`, `peek` and `empty` operation, in order.",
    constraints="- `1 <= q <= 10^5`\n- `-10^9 <= x <= 10^9`",
    hints=["Push onto an 'in' stack. When the 'out' stack is empty, move everything from 'in' to 'out' — that reverses the order."],
    editorial="Keep `inbox` and `outbox` stacks. Push to inbox. For pop/peek, if outbox is empty move all of inbox into it (reversing the order), then use outbox's top. Each element moves at most once, so every operation is amortised O(1).",
    judge_mode=JudgeMode.STDIO, starter_code=_stdio_starters("Operations: push x | pop | peek | empty"),
    reference="""
import sys
lines = sys.stdin.read().split('\\n')
q = int(lines[0])
inbox, outbox, out = [], [], []
for line in lines[1:q + 1]:
    parts = line.split()
    if parts[0] == 'push':
        inbox.append(parts[1])
        continue
    if parts[0] == 'empty':
        out.append('true' if not inbox and not outbox else 'false')
        continue
    if not outbox:
        while inbox:
            outbox.append(inbox.pop())
    out.append(outbox.pop() if parts[0] == 'pop' else outbox[-1])
print('\\n'.join(out))
""",
    stdio_samples=[("5\npush 1\npush 2\npeek\npop\nempty\n", "Front is 1; after popping it, 2 remains."), ("3\npush 7\npop\nempty\n", None)],
    stdio_hidden=["1\npush 5\n", _ops_queue(2000), _ops_queue(9000)],
)

problem(
    number=83, topic="Stacks & Queues", slug="min-stack", title="Stack With Minimum", difficulty=M,
    tags=["stack", "design"], complexity="O(1) per operation",
    statement=(
        "Implement a stack that also reports its minimum in O(1). Process the operations from standard input:\n\n"
        "- `push x` — push x\n- `pop` — remove the top element (prints nothing)\n- `top` — print the top element\n"
        "- `min` — print the smallest element currently in the stack\n\n`pop`, `top` and `min` are only issued on a non-empty stack."
    ),
    input_format="Line 1: number of operations `q`.\nNext `q` lines: one operation each.",
    output_format="One line for every `top` and `min` operation, in order.",
    constraints="- `1 <= q <= 10^5`\n- `-10^9 <= x <= 10^9`",
    hints=["Store, with every element, the minimum of the stack at the moment it was pushed."],
    editorial="Push pairs (value, min(value, current minimum)). The minimum of the whole stack is always the second field of the top pair, and popping restores the previous minimum automatically.",
    judge_mode=JudgeMode.STDIO, starter_code=_stdio_starters("Operations: push x | pop | top | min"),
    reference="""
import sys
lines = sys.stdin.read().split('\\n')
q = int(lines[0])
stack, out = [], []
for line in lines[1:q + 1]:
    parts = line.split()
    if parts[0] == 'push':
        x = int(parts[1])
        stack.append((x, min(x, stack[-1][1]) if stack else x))
    elif parts[0] == 'pop':
        stack.pop()
    elif parts[0] == 'top':
        out.append(str(stack[-1][0]))
    else:
        out.append(str(stack[-1][1]))
print('\\n'.join(out))
""",
    stdio_samples=[("6\npush 5\npush 2\npush 8\nmin\npop\ntop\n", "Minimum is 2; after popping 8 the top is 2."), ("4\npush -1\npush -1\npop\nmin\n", None)],
    stdio_hidden=["2\npush 3\nmin\n", _ops_minstack(2000), _ops_minstack(9000)],
)

problem(
    number=84, topic="Stacks & Queues", slug="evaluate-postfix", title="Evaluate a Postfix Expression", difficulty=M,
    tags=["stack", "math"], complexity="O(n) time",
    statement=(
        "`tokens` is an arithmetic expression in **postfix** (reverse Polish) notation using integers and the operators "
        "`+`, `-`, `*`, `/`. Division truncates toward zero. Return the value. The expression is valid and never divides by zero."
    ),
    constraints="- `1 <= tokens.length <= 10^4`\n- every intermediate value fits in a 32-bit signed integer",
    hints=["Push numbers; an operator pops two numbers (right operand first) and pushes the result."],
    editorial="Scan the tokens with a stack: numbers are pushed; an operator pops b then a and pushes `a op b`. Be careful that integer division truncates toward zero (Python's `//` floors, so use `int(a / b)` or adjust the sign).",
    spec=spec("evalPostfix", [("tokens", "string[]")], "int"),
    reference="""
class Solution:
    def evalPostfix(self, tokens):
        stack = []
        for t in tokens:
            if t in ('+', '-', '*', '/'):
                b, a = stack.pop(), stack.pop()
                if t == '+':
                    stack.append(a + b)
                elif t == '-':
                    stack.append(a - b)
                elif t == '*':
                    stack.append(a * b)
                else:
                    q = abs(a) // abs(b)
                    stack.append(q if (a >= 0) == (b > 0) else -q)
            else:
                stack.append(int(t))
        return stack[0]
""",
    samples=[((["2", "1", "+", "3", "*"],), "(2 + 1) × 3 = 9."), ((["4", "13", "5", "/", "+"],), "13 / 5 = 2, then 4 + 2."), ((["7", "-3", "/"],), "−2.33 truncates to −2.")],
    hidden=[(["42"],), (["10", "6", "9", "3", "+", "-11", "*", "/", "*", "17", "+", "5", "+"],),
            (["1"] + ["1", "+"] * 4999,), (["-7", "2", "/", "3", "*"],)],
)

problem(
    number=85, topic="Stacks & Queues", slug="remove-adjacent-pairs", title="Remove Adjacent Equal Pairs", difficulty=E,
    tags=["stack", "string"], complexity="O(n) time",
    statement="Repeatedly remove two **adjacent equal letters** from `s` until no such pair remains, and return the final string (which is unique).",
    constraints="- `1 <= s.length <= 10^5`\n- lowercase English letters",
    hints=["Use the result as a stack: a letter equal to the top cancels it."],
    editorial="Build the answer as a stack: if the next letter equals the top, pop (the pair vanishes); otherwise push. Removals in any order lead to the same result, and the stack handles chains like 'abba' in one pass.",
    spec=spec("removePairs", [("s", "string")], "string"),
    reference="""
class Solution:
    def removePairs(self, s):
        stack = []
        for ch in s:
            if stack and stack[-1] == ch:
                stack.pop()
            else:
                stack.append(ch)
        return ''.join(stack)
""",
    samples=[(("abbaca",), "'bb' vanishes, then 'aa', leaving 'ca'."), (("azxxzy",), None)],
    hidden=[("a",), ("aa",), ("ab" * 50000,), ("".join(rng.choice("ab") for _ in range(100000)),)],
)

# ================================================================ Recursion & Backtracking

problem(
    number=86, topic="Recursion & Backtracking", slug="all-subsets", title="All Subsets", difficulty=M,
    tags=["backtracking", "bit-manipulation"], complexity="O(n · 2^n) time",
    statement="`nums` contains distinct integers. Return **all** of its subsets (including the empty set). Write each subset in increasing order; the subsets may be returned in any order.",
    constraints="- `1 <= nums.length <= 12`\n- `-10 <= nums[i] <= 10`, distinct",
    hints=["Each element is either in or out: recurse on that choice, or enumerate bitmasks 0 … 2^n − 1."],
    editorial="Sort first so every subset comes out increasing. Backtracking: at index i either skip nums[i] or include it, recording the current subset at each leaf (or at every node in the 'build incrementally' form). There are 2^n subsets.",
    spec=spec("allSubsets", [("nums", "int[]")], "int[][]"), compare="unordered",
    reference="""
class Solution:
    def allSubsets(self, nums):
        nums = sorted(nums)
        out = []
        def go(i, cur):
            if i == len(nums):
                out.append(list(cur))
                return
            go(i + 1, cur)
            cur.append(nums[i])
            go(i + 1, cur)
            cur.pop()
        go(0, [])
        return out
""",
    samples=[(([1, 2, 3],), "2^3 = 8 subsets."), (([0],), None)],
    hidden=[([5, -5],), (rng.sample(range(-10, 11), 10),), (rng.sample(range(-10, 11), 12),)],
)

problem(
    number=87, topic="Recursion & Backtracking", slug="all-orderings", title="All Orderings", difficulty=M,
    tags=["backtracking", "recursion"], complexity="O(n · n!) time",
    statement="`nums` contains distinct integers. Return every possible ordering (permutation) of `nums`, in any order.",
    constraints="- `1 <= nums.length <= 7`\n- distinct values",
    hints=["Choose each unused value for the next position, recurse, then undo the choice."],
    editorial="Backtracking with a `used` array: for each position try every unused value, recurse, and undo. Swapping in place is an alternative. There are n! results.",
    spec=spec("allOrderings", [("nums", "int[]")], "int[][]"), compare="unordered",
    reference="""
class Solution:
    def allOrderings(self, nums):
        out, used, cur = [], [False] * len(nums), []
        def go():
            if len(cur) == len(nums):
                out.append(list(cur))
                return
            for i, x in enumerate(nums):
                if not used[i]:
                    used[i] = True
                    cur.append(x)
                    go()
                    cur.pop()
                    used[i] = False
        go()
        return out
""",
    samples=[(([1, 2, 3],), "3! = 6 orderings."), (([7],), None)],
    hidden=[([0, 1],), (rng.sample(range(-50, 50), 6),), (rng.sample(range(-50, 50), 7),)],
)

problem(
    number=88, topic="Recursion & Backtracking", slug="sum-combinations", title="Combinations That Sum to a Target", difficulty=M,
    tags=["backtracking"], complexity="Exponential; pruned by sorting",
    statement=(
        "`candidates` are distinct positive integers. Return every combination of candidates (each may be used **any number of times**) "
        "that adds up to `target`. Write each combination in non-decreasing order; combinations may be returned in any order."
    ),
    constraints="- `1 <= candidates.length <= 30`\n- `2 <= candidates[i] <= 40`\n- `1 <= target <= 40`",
    hints=["Recurse with a start index so each combination is built in non-decreasing order (no duplicates)."],
    editorial="Sort candidates. From index i, try each candidate c ≥ the previous one: append it and recurse with target − c, staying at the same index so it can repeat. Stop a branch when the remaining target is negative (sorting lets you break early).",
    spec=spec("sumCombinations", [("candidates", "int[]"), ("target", "int")], "int[][]"), compare="unordered",
    reference="""
class Solution:
    def sumCombinations(self, candidates, target):
        cands = sorted(candidates)
        out, cur = [], []
        def go(start, remaining):
            if remaining == 0:
                out.append(list(cur))
                return
            for i in range(start, len(cands)):
                if cands[i] > remaining:
                    break
                cur.append(cands[i])
                go(i, remaining - cands[i])
                cur.pop()
        go(0, target)
        return out
""",
    samples=[(([2, 3, 6, 7], 7), "[2,2,3] and [7]."), (([2, 3, 5], 8), None), (([2], 1), "Impossible: no combinations.")],
    hidden=[([3], 9), ([2, 3, 4, 5, 6, 7, 8], 30), (rng.sample(range(2, 41), 30), 40)],
)

problem(
    number=89, topic="Recursion & Backtracking", slug="balanced-parentheses-strings", title="All Balanced Parentheses Strings", difficulty=M,
    tags=["backtracking", "string"], complexity="O(4^n / √n) results",
    statement="Return every string of `n` pairs of parentheses that is **balanced**, in any order.",
    constraints="- `1 <= n <= 9`",
    hints=["Add '(' while fewer than n are used; add ')' only while there are more '(' than ')'."],
    editorial="Backtrack while tracking open and close counts: an opening bracket is allowed while open < n, a closing one while close < open. Every leaf is balanced, so nothing is generated and discarded. The count is the n-th Catalan number.",
    spec=spec("balancedStrings", [("n", "int")], "string[]"), compare="unordered",
    reference="""
class Solution:
    def balancedStrings(self, n):
        out = []
        def go(cur, opened, closed):
            if len(cur) == 2 * n:
                out.append(cur)
                return
            if opened < n:
                go(cur + '(', opened + 1, closed)
            if closed < opened:
                go(cur + ')', opened, closed + 1)
        go('', 0, 0)
        return out
""",
    samples=[((3,), "Five strings."), ((1,), None)],
    hidden=[(2,), (6,), (9,)],
)

problem(
    number=90, topic="Recursion & Backtracking", slug="word-in-grid", title="Word in a Letter Grid", difficulty=M,
    tags=["backtracking", "matrix", "dfs"], complexity="O(rows · cols · 3^L) worst case",
    statement=(
        "`grid` is a list of equal-length strings (rows of letters). Return `true` if `word` can be traced through "
        "horizontally or vertically adjacent cells, using each cell at most once."
    ),
    constraints="- `1 <= rows, cols <= 6`\n- `1 <= word.length <= 15`\n- English letters",
    hints=["DFS from every cell, marking cells as used on the way down and unmarking on the way back."],
    editorial="For each starting cell run a DFS that matches word[i] and explores the four neighbours for word[i + 1], marking the cell visited during the call and restoring it afterwards. Pruning: stop as soon as a character mismatches.",
    spec=spec("existsInGrid", [("grid", "string[]"), ("word", "string")], "bool"),
    reference="""
class Solution:
    def existsInGrid(self, grid, word):
        rows, cols = len(grid), len(grid[0])
        used = [[False] * cols for _ in range(rows)]
        def dfs(r, c, i):
            if i == len(word):
                return True
            if not (0 <= r < rows and 0 <= c < cols) or used[r][c] or grid[r][c] != word[i]:
                return False
            used[r][c] = True
            found = any(dfs(r + dr, c + dc, i + 1) for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)))
            used[r][c] = False
            return found
        return any(dfs(r, c, 0) for r in range(rows) for c in range(cols))
""",
    samples=[((["ABCE", "SFCS", "ADEE"], "ABCCED"), None), ((["ABCE", "SFCS", "ADEE"], "ABCB"), "Would need to reuse the B.")],
    hidden=[(["A"], "A"), (["A"], "B"), (["AAAAAA"] * 6, "A" * 15), (["AAAAAA"] * 5 + ["AAAAAB"], "B" + "A" * 14),
            (["".join(rng.choice("AB") for _ in range(6)) for _ in range(6)], "ABBA")],
)

problem(
    number=91, topic="Recursion & Backtracking", slug="fast-power-mod", title="Fast Modular Power", difficulty=E,
    tags=["recursion", "math", "divide-and-conquer"], complexity="O(log exponent)",
    statement="Return `(base ^ exponent) mod m`. Multiplying `base` by itself `exponent` times is far too slow for large exponents.",
    constraints="- `0 <= base <= 10^9`\n- `0 <= exponent <= 10^15`\n- `2 <= m <= 3 * 10^4`",
    hints=["x^e = (x^(e/2))² when e is even, and x · x^(e−1) when e is odd."],
    editorial="Exponentiation by squaring: halve the exponent each step, squaring the base and multiplying it into the result whenever the current bit is 1, reducing modulo m every time. O(log e) multiplications; the small m keeps every product within 64 bits (and exact in JavaScript).",
    spec=spec("powerMod", [("base", "int"), ("exponent", "long"), ("m", "int")], "int"),
    reference="""
class Solution:
    def powerMod(self, base, exponent, m):
        result, b, e = 1 % m, base % m, exponent
        while e:
            if e & 1:
                result = result * b % m
            b = b * b % m
            e >>= 1
        return result
""",
    samples=[((2, 10, 1000), "2^10 = 1024."), ((3, 0, 7), "Anything to the power 0 is 1."), ((10**9, 10**15, 29989), None)],
    hidden=[(0, 0, 2), (0, 5, 13), (7, 1, 30000), (123456789, 987654321012345, 30000), (999999999, 10**15, 2)],
)

problem(
    number=92, topic="Recursion & Backtracking", slug="queens-boards", title="Queens Boards", difficulty=H,
    tags=["backtracking"], complexity="O(n!) worst case",
    statement=(
        "Place `n` queens on an `n × n` board so that no two attack each other. Return every such board as a list of `n` strings "
        "where `Q` marks a queen and `.` an empty square. Boards may be returned in any order."
    ),
    constraints="- `1 <= n <= 8`",
    hints=["Place one queen per row and track attacked columns and diagonals."],
    editorial="Same search as Peaceful Queens (#45) but record the board at every complete placement: build each row as '.' * col + 'Q' + '.' * (n − col − 1).",
    spec=spec("queensBoards", [("n", "int")], "string[][]"), compare="unordered",
    reference="""
class Solution:
    def queensBoards(self, n):
        out, cols = [], []
        def go(row, used, d1, d2):
            if row == n:
                out.append(['.' * c + 'Q' + '.' * (n - c - 1) for c in cols])
                return
            for c in range(n):
                if c not in used and row - c not in d1 and row + c not in d2:
                    cols.append(c)
                    go(row + 1, used | {c}, d1 | {row - c}, d2 | {row + c})
                    cols.pop()
        go(0, frozenset(), frozenset(), frozenset())
        return out
""",
    samples=[((4,), "The two solutions on a 4 × 4 board."), ((1,), None)],
    hidden=[(2,), (3,), (6,), (8,)],
)

# ================================================================ Trees & BST

problem(
    number=93, topic="Trees & BST", slug="tree-depth", title="Depth of a Binary Tree", difficulty=E,
    tags=["tree", "dfs", "recursion"], complexity="O(n) time, O(height) space",
    statement="Return the number of nodes on the longest path from the root down to a leaf (0 for an empty tree).",
    constraints="- `0 <= number of nodes <= 10^4`",
    hints=["depth(node) = 1 + max(depth(left), depth(right))."],
    editorial="Recursively, an empty tree has depth 0 and any other node has 1 + the larger depth of its children. An iterative BFS that counts levels also works and avoids deep recursion.",
    spec=spec("maxDepth", [("root", "TreeNode")], "int"),
    reference="""
class Solution:
    def maxDepth(self, root):
        depth, level = 0, [root] if root else []
        while level:
            depth += 1
            level = [c for n in level for c in (n.left, n.right) if c]
        return depth
""",
    samples=[(([3, 9, 20, None, None, 15, 7],), None), (([1, None, 2],), None), (([],), None)],
    hidden=[([0],), (_random_tree(10000),), (_random_tree(3000, null_rate=0.45),)],
)

problem(
    number=94, topic="Trees & BST", slug="inorder-traversal", title="In-Order Traversal", difficulty=E,
    tags=["tree", "stack", "recursion"], complexity="O(n) time",
    statement="Return the values of the tree's nodes in **in-order** (left subtree, node, right subtree).",
    constraints="- `0 <= number of nodes <= 10^4`",
    hints=["Recursion is direct; an explicit stack avoids stack overflow on deep trees."],
    editorial="Iteratively: push left children until null, pop a node, record it, then move to its right child. Each node is pushed and popped once.",
    spec=spec("inorder", [("root", "TreeNode")], "int[]"),
    reference="""
class Solution:
    def inorder(self, root):
        out, stack, node = [], [], root
        while stack or node:
            while node:
                stack.append(node)
                node = node.left
            node = stack.pop()
            out.append(node.val)
            node = node.right
        return out
""",
    samples=[(([1, None, 2, 3],), None), (([4, 2, 6, 1, 3, 5, 7],), "A BST's in-order traversal is sorted.")],
    hidden=[([],), ([1],), (_random_tree(10000),)],
)

problem(
    number=95, topic="Trees & BST", slug="mirror-tree", title="Mirror a Binary Tree", difficulty=E,
    tags=["tree", "recursion"], complexity="O(n) time",
    statement="Mirror the tree (swap the left and right child of every node) and return its root.",
    constraints="- `0 <= number of nodes <= 10^4`",
    hints=["Swap the children of the root, then mirror both subtrees."],
    editorial="Visit every node (recursively or with a queue) and swap its two children. Each node is touched once.",
    spec=spec("mirror", [("root", "TreeNode")], "TreeNode"),
    reference="""
class Solution:
    def mirror(self, root):
        stack = [root] if root else []
        while stack:
            node = stack.pop()
            node.left, node.right = node.right, node.left
            stack.extend(c for c in (node.left, node.right) if c)
        return root
""",
    samples=[(([4, 2, 7, 1, 3, 6, 9],), None), (([2, 1, 3],), None), (([],), None)],
    hidden=[([1],), ([1, 2],), (_random_tree(10000),)],
)

problem(
    number=96, topic="Trees & BST", slug="level-order", title="Level-Order Traversal", difficulty=M,
    tags=["tree", "bfs"], complexity="O(n) time",
    statement="Return the node values level by level, from top to bottom and left to right within each level.",
    constraints="- `0 <= number of nodes <= 10^4`",
    hints=["Breadth-first search with a queue; process one level at a time."],
    editorial="BFS: the queue holds the current level; read all of its values into one list, then replace it with the next level's children.",
    spec=spec("levelOrder", [("root", "TreeNode")], "int[][]"),
    reference="""
class Solution:
    def levelOrder(self, root):
        out, level = [], [root] if root else []
        while level:
            out.append([n.val for n in level])
            level = [c for n in level for c in (n.left, n.right) if c]
        return out
""",
    samples=[(([3, 9, 20, None, None, 15, 7],), None), (([1],), None)],
    hidden=[([],), (_random_tree(10000),)],
)

problem(
    number=97, topic="Trees & BST", slug="valid-search-tree", title="Valid Binary Search Tree", difficulty=M,
    tags=["tree", "bst", "dfs"], complexity="O(n) time",
    statement=(
        "Return `true` if the tree is a valid binary search tree: for every node, all values in its left subtree are **strictly less** "
        "and all values in its right subtree are **strictly greater** than the node's value."
    ),
    constraints="- `1 <= number of nodes <= 10^4`\n- `-2^31 <= node.val <= 2^31 - 1`",
    hints=["Checking only direct children is not enough — pass down the allowed (low, high) range."],
    editorial="Recurse with bounds: the root may be anything; a left child must be below its parent and above the parent's lower bound, and so on. Equivalently, an in-order traversal must be strictly increasing.",
    spec=spec("isValidBST", [("root", "TreeNode")], "bool"),
    reference="""
class Solution:
    def isValidBST(self, root):
        prev, stack, node = None, [], root
        while stack or node:
            while node:
                stack.append(node)
                node = node.left
            node = stack.pop()
            if prev is not None and node.val <= prev:
                return False
            prev = node.val
            node = node.right
        return True
""",
    samples=[(([2, 1, 3],), None), (([5, 1, 4, None, None, 3, 6],), "3 is in the right subtree of 5 but smaller than 5."), (([2, 2],), "Values must be strictly ordered.")],
    hidden=[([1],), (_bst_level_order(rng.sample(range(-10**6, 10**6), 5000)),),
            (_bst_level_order(rng.sample(range(-10**6, 10**6), 5000)) + [10**7],), ([-2**31, None, 2**31 - 1],)],
)

problem(
    number=98, topic="Trees & BST", slug="lowest-common-ancestor", title="Lowest Common Ancestor", difficulty=M,
    tags=["tree", "dfs", "recursion"], complexity="O(n) time",
    statement=(
        "All node values in the tree are distinct, and `p` and `q` are values of two nodes in it. Return the value of their "
        "**lowest common ancestor**: the deepest node that has both as descendants (a node counts as its own descendant)."
    ),
    constraints="- `2 <= number of nodes <= 10^4`\n- distinct values; `p != q`, both present",
    hints=["If p and q are found in different subtrees of a node, that node is the answer."],
    editorial="Post-order DFS returning whether a subtree contains p or q: the first node where both sides (or the node itself and one side) report a match is the LCA. Iteratively, record parents with BFS, collect p's ancestors in a set, and walk up from q until one is in the set.",
    spec=spec("lowestCommonAncestor", [("root", "TreeNode"), ("p", "int"), ("q", "int")], "int"),
    reference="""
class Solution:
    def lowestCommonAncestor(self, root, p, q):
        parent, queue = {root.val: None}, [root]
        for node in queue:
            for child in (node.left, node.right):
                if child:
                    parent[child.val] = node.val
                    queue.append(child)
        ancestors = set()
        while p is not None:
            ancestors.add(p)
            p = parent[p]
        while q not in ancestors:
            q = parent[q]
        return q
""",
    samples=[(([3, 5, 1, 6, 2, 0, 8, None, None, 7, 4], 5, 1), None), (([3, 5, 1, 6, 2, 0, 8, None, None, 7, 4], 5, 4), "5 is an ancestor of 4.")],
    hidden=[([1, 2], 1, 2)] + [
        (lambda tv: (tv[0], *rng.sample(tv[1], 2)))(_unique_values_tree(10000)) for _ in range(3)
    ],
)

problem(
    number=99, topic="Trees & BST", slug="kth-smallest-in-bst", title="K-th Smallest in a BST", difficulty=M,
    tags=["tree", "bst", "inorder"], complexity="O(h + k) time",
    statement="`root` is a binary search tree with distinct values. Return its `k`-th smallest value (1-indexed).",
    constraints="- `1 <= k <= number of nodes <= 10^4`",
    hints=["In-order traversal visits a BST's values in sorted order; stop after k nodes."],
    editorial="Run an iterative in-order traversal and stop at the k-th popped node — only O(h + k) work. (Storing subtree sizes would answer repeated queries in O(h).)",
    spec=spec("kthSmallest", [("root", "TreeNode"), ("k", "int")], "int"),
    reference="""
class Solution:
    def kthSmallest(self, root, k):
        stack, node = [], root
        while True:
            while node:
                stack.append(node)
                node = node.left
            node = stack.pop()
            k -= 1
            if k == 0:
                return node.val
            node = node.right
""",
    samples=[(([3, 1, 4, None, 2], 1), None), (([5, 3, 6, 2, 4, None, None, 1], 3), None)],
    hidden=[([7], 1), (_bst_level_order(rng.sample(range(10**6), 10000)), 1), (_bst_level_order(rng.sample(range(10**6), 10000)), 5000),
            (_bst_level_order(list(range(1, 3001))), 3000)],
)

problem(
    number=100, topic="Trees & BST", slug="max-path-sum", title="Maximum Path Sum", difficulty=H,
    tags=["tree", "dfs", "dynamic-programming"], complexity="O(n) time",
    statement=(
        "A path is any sequence of nodes connected by edges, each node used at most once; it need not pass through the root. "
        "Return the largest possible sum of node values on a non-empty path."
    ),
    constraints="- `1 <= number of nodes <= 3 * 10^4`\n- `-1000 <= node.val <= 1000`",
    hints=["For each node, compute the best downward path starting there; the best path through the node joins two of those."],
    editorial="Post-order DFS returning the best downward path sum starting at each node (negative branches are dropped, i.e. max(0, child)). At every node update the answer with node + left gain + right gain. Visit children before parents (an explicit stack avoids recursion limits on deep trees).",
    spec=spec("maxPathSum", [("root", "TreeNode")], "int"),
    reference="""
class Solution:
    def maxPathSum(self, root):
        order, stack = [], [root]
        while stack:
            node = stack.pop()
            order.append(node)
            stack.extend(c for c in (node.left, node.right) if c)
        gain, best = {}, -10**18
        for node in reversed(order):
            left = max(0, gain.get(id(node.left), 0)) if node.left else 0
            right = max(0, gain.get(id(node.right), 0)) if node.right else 0
            best = max(best, node.val + left + right)
            gain[id(node)] = node.val + max(left, right)
        return best
""",
    samples=[(([1, 2, 3],), "2 → 1 → 3."), (([-10, 9, 20, None, None, 15, 7],), "15 → 20 → 7 = 42."), (([-3],), None)],
    hidden=[([-1, -2, -3],), (_random_tree(30000),), (_random_tree(30000, -1000, 100),)],
)

# ================================================================ Heaps

problem(
    number=101, topic="Heaps", slug="smash-stones", title="Smash the Stones", difficulty=E,
    tags=["heap", "simulation"], complexity="O(n log n) time",
    statement=(
        "Each turn, take the two heaviest stones x ≤ y and smash them: if x == y both are destroyed, otherwise a stone of weight "
        "y − x remains. Return the weight of the last remaining stone, or 0 if none remain."
    ),
    constraints="- `1 <= stones.length <= 10^4`\n- `1 <= stones[i] <= 1000`",
    hints=["A max-heap gives the two heaviest stones in O(log n)."],
    editorial="Keep the stones in a max-heap (in Python, a min-heap of negatives). Pop the two largest, push their difference if non-zero, and repeat until at most one stone remains.",
    spec=spec("lastStone", [("stones", "int[]")], "int"),
    reference="""
import heapq
class Solution:
    def lastStone(self, stones):
        heap = [-s for s in stones]
        heapq.heapify(heap)
        while len(heap) > 1:
            y, x = -heapq.heappop(heap), -heapq.heappop(heap)
            if y != x:
                heapq.heappush(heap, -(y - x))
        return -heap[0] if heap else 0
""",
    samples=[(([2, 7, 4, 1, 8, 1],), "8,7 → 1; 4,2 → 2; 2,1 → 1; 1,1 → 0; 1 remains."), (([3, 3],), None)],
    hidden=[([5],), (rand_ints(10000, 1, 1000),), ([1000] * 10000,)],
)


def _distinct_distance_points(n: int) -> list[list[int]]:
    seen, out = set(), []
    while len(out) < n:
        x, y = rng.randint(-10**4, 10**4), rng.randint(-10**4, 10**4)
        d = x * x + y * y
        if d not in seen:
            seen.add(d)
            out.append([x, y])
    return out


problem(
    number=102, topic="Heaps", slug="nearest-points", title="K Nearest Points", difficulty=M,
    tags=["heap", "sorting", "geometry"], complexity="O(n log k) with a heap",
    statement="Return the `k` points closest to the origin (Euclidean distance). All points have different distances, so the answer is unique; return the points in any order.",
    constraints="- `1 <= k <= points.length <= 10^4`\n- `-10^4 <= x, y <= 10^4`",
    hints=["Compare squared distances (no square roots). Keep a max-heap of the k best so far."],
    editorial="Use squared distance x² + y². A size-k max-heap keyed by distance drops the farthest candidate whenever it grows beyond k, giving O(n log k); sorting all points is the O(n log n) alternative.",
    spec=spec("nearestPoints", [("points", "int[][]"), ("k", "int")], "int[][]"), compare="unordered",
    reference="""
import heapq
class Solution:
    def nearestPoints(self, points, k):
        return heapq.nsmallest(k, points, key=lambda p: p[0] * p[0] + p[1] * p[1])
""",
    samples=[(([[1, 3], [-2, 2]], 1), "Distances² are 10 and 8."), (([[3, 3], [5, -1], [-2, 4]], 2), None)],
    hidden=[([[0, 1]], 1), (_distinct_distance_points(10000), 1), (_distinct_distance_points(10000), 5000)],
)

problem(
    number=103, topic="Heaps", slug="running-medians", title="Running Medians", difficulty=H,
    tags=["heap", "design", "two-heaps"], complexity="O(n log n) time",
    statement=(
        "Values arrive one at a time. After each value, report the median of all values received so far (the middle value, or the "
        "average of the two middle values when the count is even). Return the list of medians; answers within 1e-5 are accepted."
    ),
    constraints="- `1 <= nums.length <= 5 * 10^4`\n- `-10^5 <= nums[i] <= 10^5`",
    hints=["Keep the smaller half in a max-heap and the larger half in a min-heap, with sizes differing by at most one."],
    editorial="Two heaps: `low` (max-heap) holds the smaller half, `high` (min-heap) the larger half. Insert into low, move low's top to high, and if high becomes larger move its top back. The median is low's top (odd count) or the mean of both tops. Each step is O(log n).",
    spec=spec("runningMedians", [("nums", "int[]")], "double[]"), compare="float",
    reference="""
import heapq
class Solution:
    def runningMedians(self, nums):
        low, high, out = [], [], []
        for x in nums:
            heapq.heappush(low, -x)
            heapq.heappush(high, -heapq.heappop(low))
            if len(high) > len(low):
                heapq.heappush(low, -heapq.heappop(high))
            out.append(float(-low[0]) if len(low) > len(high) else (-low[0] + high[0]) / 2.0)
        return out
""",
    samples=[(([5, 15, 1, 3],), "Medians: 5, 10, 5, 4."), (([2, 2],), None)],
    hidden=[([7],), (list(range(50000)),), (rand_ints(50000, -10**5, 10**5),)],
)
