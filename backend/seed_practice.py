"""Seed the practice problem bank (idempotent: problems are upserted by slug).

    cd backend && python seed_practice.py

Expected outputs are not hand-written: each problem's Python reference
solution is executed here to compute them, so test data and reference always
agree. Statements are original to ExamSentinel.
"""

import asyncio
import json
import random
from typing import Any, Callable

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app import models  # noqa: F401  (registers all models)
from app.core.database import Base, async_session_maker, engine
from app.models.practice import JudgeMode, PracticeProblem, PracticeTestCase, ProblemDifficulty

E, M, H = ProblemDifficulty.EASY, ProblemDifficulty.MEDIUM, ProblemDifficulty.HARD
rng = random.Random(20261014)


def spec(name: str, params: list[tuple[str, str]], ret: str) -> dict:
    return {"name": name, "params": [{"name": n, "type": t} for n, t in params], "return_type": ret}


def rand_ints(n: int, lo: int, hi: int) -> list[int]:
    return [rng.randint(lo, hi) for _ in range(n)]


# Each problem: metadata + reference code + sample inputs (with explanations) + hidden inputs.
# Inputs are tuples of Python values, one per parameter.
PROBLEMS: list[dict[str, Any]] = []


def problem(**kw):
    PROBLEMS.append(kw)


# ---------------------------------------------------------------- EASY

problem(
    slug="pair-with-target-sum", title="Pair With Target Sum", difficulty=E, tags=["array", "hash-table"],
    statement=(
        "You are given an integer array `nums` and an integer `target`.\n\n"
        "Return the indices of the **two different elements** whose values add up to `target`. "
        "Exactly one such pair exists in every input. You may return the two indices in any order."
    ),
    constraints="- `2 <= nums.length <= 10^4`\n- `-10^9 <= nums[i], target <= 10^9`\n- Exactly one valid pair exists.",
    hints=["A brute force over every pair is O(n²). Can you remember values you've already seen?",
           "Store each value's index in a hash map and look up `target - x`."],
    spec=spec("pairSum", [("nums", "int[]"), ("target", "int")], "int[]"), compare="unordered",
    reference="""
class Solution:
    def pairSum(self, nums, target):
        seen = {}
        for i, x in enumerate(nums):
            if target - x in seen:
                return [seen[target - x], i]
            seen[x] = i
""",
    samples=[(([4, 9, 13, 2], 11), "nums[1] + nums[3] = 9 + 2 = 11."), (([5, 1, 5], 10), "Both 5s are used; they are different elements."), (([-3, 8, 0, 7], 4), None)],
    hidden=[([1, 2], 3), ([0, 0, 1], 0), ([10**9, -10**9, 3], 0)]
           + [(list(range(1, 10001)), 19999)],  # only 9999 + 10000 reaches the maximum sum
)

problem(
    slug="balanced-brackets", title="Balanced Brackets", difficulty=E, tags=["stack", "string"],
    statement=(
        "A string `s` contains only the characters `()[]{}`.\n\n"
        "Return `true` if every opening bracket is closed by the **same type** of bracket and in the **correct order**, "
        "otherwise return `false`."
    ),
    constraints="- `1 <= s.length <= 10^4`\n- `s` consists only of `()[]{}`",
    hints=["The most recent unmatched opening bracket must be closed first — which data structure gives you 'most recent'?"],
    spec=spec("isBalanced", [("s", "string")], "bool"),
    reference="""
class Solution:
    def isBalanced(self, s):
        pairs = {')': '(', ']': '[', '}': '{'}
        stack = []
        for ch in s:
            if ch in pairs:
                if not stack or stack.pop() != pairs[ch]:
                    return False
            else:
                stack.append(ch)
        return not stack
""",
    samples=[(("{[]()}",), None), (("([)]",), "The `[` is closed by `)` before its own `]`."), (("((",), "Two brackets are never closed.")],
    hidden=[(")",), ("()",), ("{{{{}}}}",), ("[]{}()" * 1000,), ("(" * 5000 + ")" * 5000,), ("(" * 5000 + ")" * 4999 + "]",)],
)

problem(
    slug="reverse-word-order", title="Reverse Word Order", difficulty=E, tags=["string", "two-pointers"],
    statement=(
        "Given a sentence `s`, return a new string with the **words in reverse order**.\n\n"
        "Words are separated by one or more spaces. The result must contain the words separated by "
        "**exactly one space**, with no leading or trailing spaces."
    ),
    constraints="- `1 <= s.length <= 10^4`\n- `s` contains English letters, digits and spaces\n- `s` has at least one word",
    hints=["Split on whitespace, discard empty pieces, then join in reverse."],
    spec=spec("reverseWords", [("s", "string")], "string"),
    reference="""
class Solution:
    def reverseWords(self, s):
        return " ".join(reversed(s.split()))
""",
    samples=[(("exam day is here",), None), (("  hello   world ",), "Extra spaces are collapsed and trimmed.")],
    hidden=[("a",), ("one two",), ("  x  ",), (" ".join(f"w{i}" for i in range(2000)),)],
)

problem(
    slug="sorted-search", title="Search a Sorted List", difficulty=E, tags=["array", "binary-search"],
    statement=(
        "`nums` is sorted in **strictly increasing** order. Return the index of `target` in `nums`, "
        "or `-1` if it is not present.\n\nYour solution should run in **O(log n)** time."
    ),
    constraints="- `1 <= nums.length <= 10^5`\n- all values in `nums` are distinct\n- `-10^9 <= nums[i], target <= 10^9`",
    hints=["Compare `target` with the middle element and discard half of the range each step."],
    spec=spec("search", [("nums", "int[]"), ("target", "int")], "int"),
    reference="""
class Solution:
    def search(self, nums, target):
        lo, hi = 0, len(nums) - 1
        while lo <= hi:
            mid = (lo + hi) // 2
            if nums[mid] == target:
                return mid
            if nums[mid] < target:
                lo = mid + 1
            else:
                hi = mid - 1
        return -1
""",
    samples=[(([-4, 0, 3, 8, 15], 8), None), (([-4, 0, 3, 8, 15], 5), "5 is not in the list.")],
    hidden=[([7], 7), ([7], -7), ([1, 2], 2), (list(range(0, 200000, 2)), 199998), (list(range(0, 200000, 2)), 77777)],
)

problem(
    slug="merge-two-sorted-lists", title="Merge Two Sorted Lists", difficulty=E, tags=["array", "two-pointers"],
    statement="Arrays `a` and `b` are each sorted in non-decreasing order. Return a single array containing all of their elements, also sorted in non-decreasing order.",
    constraints="- `0 <= a.length, b.length <= 10^4`\n- `-10^9 <= a[i], b[i] <= 10^9`",
    hints=["Walk both arrays with one pointer each and always take the smaller head."],
    spec=spec("merge", [("a", "int[]"), ("b", "int[]")], "int[]"),
    reference="""
class Solution:
    def merge(self, a, b):
        i = j = 0
        out = []
        while i < len(a) and j < len(b):
            if a[i] <= b[j]:
                out.append(a[i]); i += 1
            else:
                out.append(b[j]); j += 1
        return out + a[i:] + b[j:]
""",
    samples=[(([1, 4, 9], [2, 3, 10, 11]), None), (([], [5]), "One list may be empty.")],
    hidden=[([], []), ([1, 1, 1], [1, 1]), (sorted(rand_ints(5000, -10**6, 10**6)), sorted(rand_ints(5000, -10**6, 10**6)))],
)

problem(
    slug="alphanumeric-palindrome", title="Alphanumeric Palindrome", difficulty=E, tags=["string", "two-pointers"],
    statement=(
        "Return `true` if `s` reads the same forwards and backwards after **removing every character that is not a letter or digit** "
        "and **ignoring letter case**. Otherwise return `false`."
    ),
    constraints="- `1 <= s.length <= 2 * 10^5`\n- `s` consists of printable ASCII characters",
    hints=["Use two pointers moving inward, skipping characters that are not alphanumeric."],
    spec=spec("isPalindrome", [("s", "string")], "bool"),
    reference="""
class Solution:
    def isPalindrome(self, s):
        t = [c.lower() for c in s if c.isalnum()]
        return t == t[::-1]
""",
    samples=[(("Never odd, or even!",), "Cleaned string is `neveroddoreven`."), (("Exam 2026",), None)],
    hidden=[(" ",), ("a.",), ("0P",), ("ab" * 50000 + "ba" * 50000,), ("ab" * 50000 + "ab" * 50000,)],
)

problem(
    slug="stair-climber", title="Stair Climber", difficulty=E, tags=["dynamic-programming", "math"],
    statement="You are at the bottom of a staircase with `n` steps. Each move climbs either **1 or 2** steps. In how many distinct ways can you reach the top?",
    constraints="- `1 <= n <= 75`",
    hints=["The last move was either a 1-step or a 2-step. How does that relate the answer for `n` to smaller answers?",
           "The answer can exceed 32 bits — use a 64-bit integer (it stays below 2^53, so JavaScript numbers are exact)."],
    spec=spec("countWays", [("n", "int")], "long"),
    reference="""
class Solution:
    def countWays(self, n):
        a, b = 1, 1
        for _ in range(n):
            a, b = b, a + b
        return a
""",
    samples=[((2,), "1+1 or 2."), ((4,), "1+1+1+1, 1+1+2, 1+2+1, 2+1+1, 2+2.")],
    hidden=[(1,), (10,), (45,), (75,)],
)

problem(
    slug="single-trade-profit", title="Single Trade Profit", difficulty=E, tags=["array", "greedy"],
    statement=(
        "`prices[i]` is the price of a share on day `i`. You may buy **once** and later sell **once** (selling must happen on a later day).\n\n"
        "Return the maximum profit you can make, or `0` if no profitable trade exists."
    ),
    constraints="- `1 <= prices.length <= 10^5`\n- `0 <= prices[i] <= 10^4`",
    hints=["Track the lowest price seen so far while scanning left to right."],
    spec=spec("maxProfit", [("prices", "int[]")], "int"),
    reference="""
class Solution:
    def maxProfit(self, prices):
        best, low = 0, float("inf")
        for p in prices:
            low = min(low, p)
            best = max(best, p - low)
        return best
""",
    samples=[(([8, 2, 6, 1, 4],), "Buy at 2, sell at 6."), (([9, 7, 4, 1],), "Prices only fall, so no trade.")],
    hidden=[([5],), ([1, 2],), (rand_ints(100000, 0, 10000),), (list(range(100000, 0, -1)),)],
)

problem(
    slug="fizz-buzz-words", title="Fizz Buzz Words", difficulty=E, tags=["math", "string"],
    statement=(
        "Return a list of strings for the numbers `1` to `n`. For each number `i`:\n\n"
        "- `\"FizzBuzz\"` if `i` is divisible by both 3 and 5\n- `\"Fizz\"` if divisible by 3\n- `\"Buzz\"` if divisible by 5\n- otherwise `i` itself as a string"
    ),
    constraints="- `1 <= n <= 10^4`",
    hints=["Check divisibility by 15 first."],
    spec=spec("fizzBuzz", [("n", "int")], "string[]"),
    reference="""
class Solution:
    def fizzBuzz(self, n):
        return ["FizzBuzz" if i % 15 == 0 else "Fizz" if i % 3 == 0 else "Buzz" if i % 5 == 0 else str(i) for i in range(1, n + 1)]
""",
    samples=[((5,), None), ((15,), None)],
    hidden=[(1,), (3,), (10000,)],
)

problem(
    slug="sum-of-numbers-stdin", title="Sum of Numbers (stdin)", difficulty=E, tags=["input-output", "math"],
    statement=(
        "This problem uses **standard input/output** instead of a `Solution` class.\n\n"
        "The first line contains an integer `n`. The second line contains `n` space-separated integers. "
        "Print their sum."
    ),
    constraints="- `1 <= n <= 10^4`\n- `-10^9 <= value <= 10^9` (the sum fits in 64 bits)",
    hints=["Read all of stdin, split on whitespace, and skip the first token."],
    judge_mode=JudgeMode.STDIO,
    starter_code={
        "python": "import sys\n\ndata = sys.stdin.read().split()\n# data[0] is n; the numbers follow\n",
        "javascript": "const data = require('fs').readFileSync(0, 'utf8').trim().split(/\\s+/);\n// data[0] is n; the numbers follow\n",
        "java": "import java.util.*;\n\npublic class Main {\n    public static void main(String[] args) {\n        Scanner in = new Scanner(System.in);\n        int n = in.nextInt();\n        \n    }\n}\n",
        "cpp": "#include <bits/stdc++.h>\nusing namespace std;\n\nint main() {\n    int n;\n    cin >> n;\n    \n    return 0;\n}\n",
        "c": "#include <stdio.h>\n\nint main(void) {\n    int n;\n    scanf(\"%d\", &n);\n    \n    return 0;\n}\n",
    },
    reference="""
import sys
data = sys.stdin.read().split()
print(sum(int(x) for x in data[1:]))
""",
    stdio_samples=[("3\n1 2 3\n", "Sum is 6."), ("2\n-5 5\n", None)],
    stdio_hidden=["1\n42\n", "4\n1000000000 1000000000 1000000000 1000000000\n",
                  "10000\n" + " ".join(str(x) for x in rand_ints(10000, -10**9, 10**9)) + "\n"],
)

# ---------------------------------------------------------------- MEDIUM

problem(
    slug="best-contiguous-sum", title="Best Contiguous Sum", difficulty=M, tags=["array", "dynamic-programming"],
    statement="Return the largest possible sum of a **non-empty contiguous** sub-array of `nums`.",
    constraints="- `1 <= nums.length <= 10^5`\n- `-10^4 <= nums[i] <= 10^4`",
    hints=["At each index decide: extend the previous run, or start fresh here?"],
    spec=spec("maxSubarraySum", [("nums", "int[]")], "int"),
    reference="""
class Solution:
    def maxSubarraySum(self, nums):
        best = cur = nums[0]
        for x in nums[1:]:
            cur = max(x, cur + x)
            best = max(best, cur)
        return best
""",
    samples=[(([3, -5, 4, -1, 2, 1, -6, 2],), "The sub-array [4, -1, 2, 1] sums to 6."), (([-7, -2, -9],), "All values negative: pick the single largest.")],
    hidden=[([5],), ([-1],), (rand_ints(100000, -10000, 10000),), ([10000] * 100000,)],
)

problem(
    slug="longest-unique-run", title="Longest Run Without Repeats", difficulty=M, tags=["string", "sliding-window", "hash-table"],
    statement="Return the length of the longest **substring** of `s` in which no character appears more than once.",
    constraints="- `0 <= s.length <= 5 * 10^4`\n- `s` consists of printable ASCII characters",
    hints=["Maintain a window [left, right] with no repeats; when a repeat enters, move `left` past the previous occurrence."],
    spec=spec("longestUniqueRun", [("s", "string")], "int"),
    reference="""
class Solution:
    def longestUniqueRun(self, s):
        last, left, best = {}, 0, 0
        for right, ch in enumerate(s):
            if ch in last and last[ch] >= left:
                left = last[ch] + 1
            last[ch] = right
            best = max(best, right - left + 1)
        return best
""",
    samples=[(("proctoring",), "`ctoring` has 7 distinct characters."), (("aaaa",), None), (("",), "An empty string has length 0.")],
    hidden=[(("a",)), ("abcabcbb",), ("dvdf",), ("".join(chr(33 + rng.randint(0, 60)) for _ in range(50000)),)],
)

problem(
    slug="products-except-self", title="Products Except Self", difficulty=M, tags=["array", "prefix-sum"],
    statement=(
        "Return an array `out` where `out[i]` is the product of every element of `nums` **except** `nums[i]`.\n\n"
        "Solve it **without using division** in O(n) time."
    ),
    constraints="- `2 <= nums.length <= 10^5`\n- `-30 <= nums[i] <= 30`\n- every product fits in a 32-bit integer",
    hints=["out[i] = (product of everything left of i) × (product of everything right of i)."],
    spec=spec("productExceptSelf", [("nums", "int[]")], "int[]"),
    reference="""
class Solution:
    def productExceptSelf(self, nums):
        n = len(nums)
        out = [1] * n
        left = 1
        for i in range(n):
            out[i] = left
            left *= nums[i]
        right = 1
        for i in range(n - 1, -1, -1):
            out[i] *= right
            right *= nums[i]
        return out
""",
    samples=[(([2, 3, 4, 5],), None), (([-1, 2, 0, 4],), "Every product except index 2 includes the zero.")],
    hidden=[([0, 0],), ([7, 3],), ([1] * 50000 + [2] * 20 + [1] * 49980,), ([rng.choice([-1, 1]) for _ in range(100000)],)],
)

problem(
    slug="count-islands", title="Count the Islands", difficulty=M, tags=["graph", "bfs", "dfs", "matrix"],
    statement=(
        "`grid` is a 2D map where `1` is land and `0` is water. An **island** is a group of land cells connected "
        "horizontally or vertically (not diagonally). Return the number of islands."
    ),
    constraints="- `1 <= rows, cols <= 300`\n- `grid[r][c]` is `0` or `1`",
    hints=["Scan every cell; when you find unvisited land, flood-fill its whole island and count one."],
    spec=spec("countIslands", [("grid", "int[][]")], "int"),
    reference="""
class Solution:
    def countIslands(self, grid):
        rows, cols = len(grid), len(grid[0])
        seen = [[False] * cols for _ in range(rows)]
        count = 0
        for r in range(rows):
            for c in range(cols):
                if grid[r][c] == 1 and not seen[r][c]:
                    count += 1
                    stack = [(r, c)]
                    seen[r][c] = True
                    while stack:
                        y, x = stack.pop()
                        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                            ny, nx = y + dy, x + dx
                            if 0 <= ny < rows and 0 <= nx < cols and grid[ny][nx] == 1 and not seen[ny][nx]:
                                seen[ny][nx] = True
                                stack.append((ny, nx))
        return count
""",
    samples=[(([[1, 1, 0, 0], [0, 1, 0, 1], [1, 0, 0, 1]],), "Three islands: top-left L shape, right column pair, bottom-left cell."), (([[0, 0], [0, 0]],), None)],
    hidden=[([[1]],), ([[1, 0, 1, 0, 1]],), ([[1] * 300 for _ in range(300)],), ([[rng.choice([0, 1]) for _ in range(300)] for _ in range(300)],)],
)

problem(
    slug="fewest-coins", title="Fewest Coins", difficulty=M, tags=["dynamic-programming"],
    statement="Using unlimited coins of the denominations in `coins`, return the **fewest** coins needed to make exactly `amount`. Return `-1` if it is impossible.",
    constraints="- `1 <= coins.length <= 12`\n- `1 <= coins[i] <= 2^31 - 1`\n- `0 <= amount <= 10^4`",
    hints=["dp[x] = 1 + min(dp[x - c]) over all coins c ≤ x."],
    spec=spec("fewestCoins", [("coins", "int[]"), ("amount", "int")], "int"),
    reference="""
class Solution:
    def fewestCoins(self, coins, amount):
        INF = float("inf")
        dp = [0] + [INF] * amount
        for x in range(1, amount + 1):
            for c in coins:
                if c <= x and dp[x - c] + 1 < dp[x]:
                    dp[x] = dp[x - c] + 1
        return dp[amount] if dp[amount] != INF else -1
""",
    samples=[(([1, 4, 5], 8), "4 + 4 uses two coins (greedy 5+1+1+1 would use four)."), (([3], 7), "7 cannot be made from 3s."), (([2], 0), None)],
    hidden=[([1], 10000), ([7, 11, 13], 9999), ([186, 419, 83, 408], 6249), ([2147483647], 2)],
)

problem(
    slug="k-most-frequent", title="K Most Frequent Values", difficulty=M, tags=["hash-table", "heap", "sorting"],
    statement="Return the `k` values that occur most often in `nums`. The answer is guaranteed to be unique; return it in any order.",
    constraints="- `1 <= nums.length <= 10^5`\n- `1 <= k <=` number of distinct values\n- the top-k set is unique",
    hints=["Count frequencies with a hash map, then pick the top k (heap or bucket sort)."],
    spec=spec("topKFrequent", [("nums", "int[]"), ("k", "int")], "int[]"), compare="unordered",
    reference="""
from collections import Counter
class Solution:
    def topKFrequent(self, nums, k):
        return [v for v, _ in Counter(nums).most_common(k)]
""",
    samples=[(([4, 4, 4, 9, 9, 2], 2), "4 appears 3 times, 9 twice."), (([7], 1), None)],
    hidden=[([1, 2, 2, 3, 3, 3], 3), ([5] * 10 + [6] * 9 + [7] * 8 + list(range(100, 140)), 3),
            ([i for i in range(1, 300) for _ in range(i)], 5)],
)

problem(
    slug="merge-overlapping-ranges", title="Merge Overlapping Ranges", difficulty=M, tags=["array", "sorting"],
    statement=(
        "Each element of `ranges` is `[start, end]` with `start <= end`. Merge every group of overlapping ranges "
        "(ranges that touch, like `[1,3]` and `[3,5]`, also merge) and return the result **sorted by start**."
    ),
    constraints="- `1 <= ranges.length <= 10^4`\n- `0 <= start <= end <= 10^5`",
    hints=["Sort by start; then each range either extends the last merged range or begins a new one."],
    spec=spec("mergeRanges", [("ranges", "int[][]")], "int[][]"),
    reference="""
class Solution:
    def mergeRanges(self, ranges):
        out = []
        for s, e in sorted(ranges):
            if out and s <= out[-1][1]:
                out[-1][1] = max(out[-1][1], e)
            else:
                out.append([s, e])
        return out
""",
    samples=[(([[8, 10], [1, 3], [2, 6], [15, 18]],), "[1,3] and [2,6] overlap → [1,6]."), (([[1, 4], [4, 5]],), "Touching ranges merge.")],
    hidden=[([[5, 5]],), ([[1, 10], [2, 3], [4, 5]],), ([sorted([rng.randint(0, 100000), rng.randint(0, 100000)]) for _ in range(10000)],)],
)

problem(
    slug="longest-rising-subsequence", title="Longest Rising Subsequence", difficulty=M, tags=["dynamic-programming", "binary-search"],
    statement="Return the length of the longest **strictly increasing subsequence** of `nums` (elements need not be adjacent, but must keep their order).",
    constraints="- `1 <= nums.length <= 2500`\n- `-10^4 <= nums[i] <= 10^4`",
    hints=["O(n²) DP works. For O(n log n), keep the smallest possible tail for every subsequence length."],
    spec=spec("lengthOfLIS", [("nums", "int[]")], "int"),
    reference="""
import bisect
class Solution:
    def lengthOfLIS(self, nums):
        tails = []
        for x in nums:
            i = bisect.bisect_left(tails, x)
            if i == len(tails):
                tails.append(x)
            else:
                tails[i] = x
        return len(tails)
""",
    samples=[(([3, 10, 2, 1, 20, 4, 6, 7],), "One answer is [2, 4, 6, 7]."), (([5, 5, 5],), "Strictly increasing, so equal values don't chain.")],
    hidden=[([1],), (list(range(2500)),), (list(range(2500, 0, -1)),), (rand_ints(2500, -10000, 10000),)],
)

problem(
    slug="anagram-groups", title="Anagram Groups", difficulty=M, tags=["hash-table", "string", "sorting"],
    statement=(
        "Group the strings in `words` that are anagrams of each other.\n\n"
        "To make the answer unique: sort the words **inside** each group alphabetically, then sort the **groups** "
        "alphabetically by their first word."
    ),
    constraints="- `1 <= words.length <= 10^4`\n- `0 <= words[i].length <= 100`\n- lowercase English letters only",
    hints=["Two words are anagrams exactly when their sorted letters are equal — use that as a hash key."],
    spec=spec("groupAnagrams", [("words", "string[]")], "string[][]"),
    reference="""
from collections import defaultdict
class Solution:
    def groupAnagrams(self, words):
        groups = defaultdict(list)
        for w in words:
            groups["".join(sorted(w))].append(w)
        return sorted((sorted(g) for g in groups.values()), key=lambda g: g[0])
""",
    samples=[((["note", "stone", "tone", "onset", "eat"],), None), ((["", ""],), "Empty strings are anagrams of each other.")],
    hidden=[(["a"],), (["ab", "ba", "abc", "cab", "bca", "z"],),
            (["".join(rng.choice("abcde") for _ in range(4)) for _ in range(5000)],)],
)

# ---------------------------------------------------------------- HARD

problem(
    slug="rainwater-capacity", title="Rainwater Capacity", difficulty=H, tags=["array", "two-pointers", "stack"],
    statement="`heights[i]` is the height of a wall of width 1. After heavy rain, how many units of water are trapped between the walls?",
    constraints="- `1 <= heights.length <= 2 * 10^4`\n- `0 <= heights[i] <= 10^5`",
    hints=["Water above index i = min(highest wall to the left, highest wall to the right) − heights[i].",
           "Two pointers from both ends let you do it in O(1) extra space."],
    spec=spec("trappedWater", [("heights", "int[]")], "long"),
    reference="""
class Solution:
    def trappedWater(self, heights):
        l, r = 0, len(heights) - 1
        lmax = rmax = water = 0
        while l < r:
            if heights[l] < heights[r]:
                lmax = max(lmax, heights[l]); water += lmax - heights[l]; l += 1
            else:
                rmax = max(rmax, heights[r]); water += rmax - heights[r]; r -= 1
        return water
""",
    samples=[(([3, 0, 2, 0, 4],), "3 + 1 + 3 = 7 units."), (([1, 2, 3],), "Rising walls hold no water.")],
    hidden=[([5],), ([5, 0, 5],), ([100000] + [0] * 19998 + [100000],), (rand_ints(20000, 0, 100000),)],
)

problem(
    slug="minimum-edit-steps", title="Minimum Edit Steps", difficulty=H, tags=["dynamic-programming", "string"],
    statement="Return the minimum number of single-character **insertions, deletions or replacements** needed to turn string `a` into string `b`.",
    constraints="- `0 <= a.length, b.length <= 500`\n- lowercase English letters",
    hints=["dp[i][j] = edits to turn the first i chars of a into the first j chars of b."],
    spec=spec("minEdits", [("a", "string"), ("b", "string")], "int"),
    reference="""
class Solution:
    def minEdits(self, a, b):
        prev = list(range(len(b) + 1))
        for i in range(1, len(a) + 1):
            cur = [i] + [0] * len(b)
            for j in range(1, len(b) + 1):
                cur[j] = prev[j - 1] if a[i - 1] == b[j - 1] else 1 + min(prev[j - 1], prev[j], cur[j - 1])
            prev = cur
        return prev[-1]
""",
    samples=[(("sentinel", "sentence"), "Replace i→e, l→c, insert e."), (("", "abc"), "Insert three characters.")],
    hidden=[("", ""), ("same", "same"), ("kitten", "sitting"),
            ("".join(rng.choice("abc") for _ in range(500)), "".join(rng.choice("abc") for _ in range(500)))],
)

problem(
    slug="median-of-two-sorted", title="Median of Two Sorted Arrays", difficulty=H, tags=["array", "binary-search", "divide-and-conquer"],
    statement=(
        "Arrays `a` and `b` are sorted in non-decreasing order and are not both empty. Return the **median** of all their elements combined.\n\n"
        "Answers within `10^-5` of the true median are accepted. Aim for **O(log(m + n))**."
    ),
    constraints="- `0 <= a.length, b.length <= 10^5`\n- `1 <= a.length + b.length`\n- `-10^6 <= a[i], b[i] <= 10^6`",
    hints=["Binary-search a partition of the shorter array so that everything on the left half ≤ everything on the right half."],
    spec=spec("findMedian", [("a", "int[]"), ("b", "int[]")], "double"), compare="float",
    reference="""
class Solution:
    def findMedian(self, a, b):
        if len(a) > len(b):
            a, b = b, a
        m, n = len(a), len(b)
        half = (m + n + 1) // 2
        lo, hi = 0, m
        while True:
            i = (lo + hi) // 2
            j = half - i
            a_left = a[i - 1] if i > 0 else float("-inf")
            a_right = a[i] if i < m else float("inf")
            b_left = b[j - 1] if j > 0 else float("-inf")
            b_right = b[j] if j < n else float("inf")
            if a_left <= b_right and b_left <= a_right:
                if (m + n) % 2:
                    return float(max(a_left, b_left))
                return (max(a_left, b_left) + min(a_right, b_right)) / 2.0
            if a_left > b_right:
                hi = i - 1
            else:
                lo = i + 1
""",
    samples=[(([1, 3], [2]), "Merged: [1, 2, 3], median 2."), (([1, 2], [3, 4]), "Merged: [1, 2, 3, 4], median (2 + 3) / 2 = 2.5.")],
    hidden=[([], [7]), ([5], []), ([1, 1, 1], [1, 1]), (sorted(rand_ints(100000, -10**6, 10**6)), sorted(rand_ints(99999, -10**6, 10**6)))],
)


# ---------------------------------------------------------------------------

def run_reference(code: str, method: str, args: tuple) -> Any:
    ns: dict = {}
    exec(code, ns)  # trusted, repo-authored reference solutions only
    return getattr(ns["Solution"](), method)(*[json.loads(json.dumps(a)) for a in args])


def run_stdio_reference(code: str, stdin: str) -> str:
    import contextlib
    import io
    import sys

    out = io.StringIO()
    old_stdin = sys.stdin
    sys.stdin = io.StringIO(stdin)
    try:
        with contextlib.redirect_stdout(out):
            exec(code, {"__name__": "__main__"})
    finally:
        sys.stdin = old_stdin
    return out.getvalue()


def build_cases(p: dict) -> list[PracticeTestCase]:
    cases = []
    if p.get("judge_mode") == JudgeMode.STDIO:
        for stdin, expl in p["stdio_samples"]:
            cases.append((stdin, run_stdio_reference(p["reference"], stdin).strip(), True, expl))
        for stdin in p["stdio_hidden"]:
            cases.append((stdin, run_stdio_reference(p["reference"], stdin).strip(), False, None))
    else:
        method = p["spec"]["name"]
        to_input = lambda args: "\n".join(json.dumps(a, separators=(",", ":")) for a in args)  # noqa: E731
        for args, expl in p["samples"]:
            cases.append((to_input(args), json.dumps(run_reference(p["reference"], method, args), separators=(",", ":")), True, expl))
        for args in p["hidden"]:
            args = args if isinstance(args, tuple) else (args,)
            cases.append((to_input(args), json.dumps(run_reference(p["reference"], method, args), separators=(",", ":")), False, None))
    return [
        PracticeTestCase(input_data=i, expected_output=o, is_sample=s, explanation=e, order_index=n)
        for n, (i, o, s, e) in enumerate(cases)
    ]


async def seed() -> None:
    async with engine.begin() as conn:
        if engine.url.get_backend_name() == "sqlite":
            await conn.run_sync(Base.metadata.create_all)
    async with async_session_maker() as db:
        for p in PROBLEMS:
            existing = (await db.execute(
                select(PracticeProblem).options(selectinload(PracticeProblem.test_cases)).where(PracticeProblem.slug == p["slug"])
            )).scalar_one_or_none()
            problem_row = existing or PracticeProblem(slug=p["slug"])
            problem_row.title = p["title"]
            problem_row.difficulty = p["difficulty"]
            problem_row.tags = p["tags"]
            problem_row.statement = p["statement"]
            problem_row.constraints = p.get("constraints")
            problem_row.hints = p.get("hints", [])
            problem_row.judge_mode = p.get("judge_mode", JudgeMode.FUNCTION)
            problem_row.function_spec = p.get("spec")
            problem_row.compare_mode = p.get("compare", "exact")
            problem_row.starter_code = p.get("starter_code", {})
            problem_row.reference_solution = {"language": "python", "code": p["reference"].strip() + "\n"}
            problem_row.time_limit_ms = p.get("time_limit_ms", 2000)
            problem_row.memory_limit_mb = 256
            problem_row.is_published = True
            problem_row.test_cases = build_cases(p)
            if existing is None:
                db.add(problem_row)
            print(f"{'updated' if existing else 'created'}: {p['slug']} ({len(problem_row.test_cases)} tests)")
        await db.commit()
    print(f"Seeded {len(PROBLEMS)} practice problems.")


if __name__ == "__main__":
    asyncio.run(seed())
