"""Additional algorithm problems (arrays, strings, DP, graphs). Statements are original."""

from practice_bank.common import E, H, M, problem, rand_ints, rng, spec


def _majority_case(n: int) -> list[int]:
    winner = rng.randint(-100, 100)
    nums = [winner] * (n // 2 + 1) + rand_ints(n - (n // 2 + 1), -100, 100)
    rng.shuffle(nums)
    return nums


def _rotated(n: int) -> list[int]:
    nums = sorted(rng.sample(range(-10**6, 10**6), n))
    k = rng.randint(0, n - 1)
    return nums[k:] + nums[:k]


def _missing(n: int) -> list[int]:
    nums = list(range(n + 1))
    nums.remove(rng.randint(0, n))
    rng.shuffle(nums)
    return nums


# ---------------------------------------------------------------- EASY

problem(
    slug="has-repeated-value", title="Has a Repeated Value", difficulty=E, tags=["array", "hash-table"],
    statement="Return `true` if any value appears **at least twice** in `nums`, and `false` if every value is distinct.",
    constraints="- `1 <= nums.length <= 10^5`\n- `-10^9 <= nums[i] <= 10^9`",
    hints=["A set lets you check \"have I seen this before?\" in O(1)."],
    spec=spec("hasRepeat", [("nums", "int[]")], "bool"),
    reference="""
class Solution:
    def hasRepeat(self, nums):
        return len(set(nums)) != len(nums)
""",
    samples=[(([3, 8, 1, 8],), "8 appears twice."), (([5, 6, 7],), None)],
    hidden=[([1],), ([2, 2],), (list(range(100000)),), (list(range(99999)) + [42],)],
)

problem(
    slug="missing-ticket-number", title="Missing Ticket Number", difficulty=E, tags=["array", "math", "bit-manipulation"],
    statement=(
        "Tickets numbered `0` to `n` were printed, and exactly one went missing. `nums` holds the `n` tickets that remain, "
        "in any order. Return the missing number."
    ),
    constraints="- `1 <= n <= 10^5`\n- all values in `nums` are distinct and in `[0, n]`",
    hints=["The sum 0 + 1 + … + n is n(n+1)/2."],
    spec=spec("missingNumber", [("nums", "int[]")], "int"),
    reference="""
class Solution:
    def missingNumber(self, nums):
        n = len(nums)
        return n * (n + 1) // 2 - sum(nums)
""",
    samples=[(([3, 0, 1],), "n = 3, so tickets 0..3 exist; 2 is missing."), (([0],), "n = 1; ticket 1 is missing.")],
    hidden=[([1],), (_missing(10),), (_missing(100000),)],
)

problem(
    slug="zeros-to-the-back", title="Zeros to the Back", difficulty=E, tags=["array", "two-pointers"],
    statement="Return `nums` with every `0` moved to the end, keeping the **relative order** of the non-zero values.",
    constraints="- `1 <= nums.length <= 10^5`\n- `-10^9 <= nums[i] <= 10^9`",
    hints=["Write each non-zero value to the next free slot, then fill the rest with zeros."],
    spec=spec("moveZeros", [("nums", "int[]")], "int[]"),
    reference="""
class Solution:
    def moveZeros(self, nums):
        kept = [x for x in nums if x != 0]
        return kept + [0] * (len(nums) - len(kept))
""",
    samples=[(([0, 4, 0, 3, 9],), None), (([0, 0],), None)],
    hidden=[([7],), ([1, 2, 3],), ([rng.choice([0, 0, rng.randint(-9, 9)]) for _ in range(100000)],)],
)

problem(
    slug="majority-value", title="Majority Value", difficulty=E, tags=["array", "voting"],
    statement="One value in `nums` appears **more than half** of the time. Return it.",
    constraints="- `1 <= nums.length <= 5 * 10^4`\n- a majority value always exists",
    hints=["Try Boyer–Moore voting: a counter that goes up for the current candidate and down for others."],
    spec=spec("majority", [("nums", "int[]")], "int"),
    reference="""
class Solution:
    def majority(self, nums):
        candidate, count = None, 0
        for x in nums:
            if count == 0:
                candidate = x
            count += 1 if x == candidate else -1
        return candidate
""",
    samples=[(([2, 7, 2, 2, 5],), "2 appears 3 times out of 5."), (([9],), None)],
    hidden=[([4, 4],), (_majority_case(51),), (_majority_case(50000),)],
)

problem(
    slug="same-letters", title="Same Letters", difficulty=E, tags=["string", "hash-table", "sorting"],
    statement="Return `true` if `b` can be formed by rearranging **all** the letters of `a` (each letter used exactly as often), otherwise `false`.",
    constraints="- `1 <= a.length, b.length <= 5 * 10^4`\n- lowercase English letters",
    hints=["Count letters in both strings and compare the counts."],
    spec=spec("sameLetters", [("a", "string"), ("b", "string")], "bool"),
    reference="""
from collections import Counter
class Solution:
    def sameLetters(self, a, b):
        return Counter(a) == Counter(b)
""",
    samples=[(("listen", "silent"), None), (("exam", "maxe"), None), (("aab", "abb"), "Counts differ.")],
    hidden=[("a", "a"), ("a", "b"), ("ab", "abc"), ("".join(rng.choice("abc") for _ in range(50000)), "c" * 50000)],
)

problem(
    slug="first-unique-letter", title="First Unique Letter", difficulty=E, tags=["string", "hash-table"],
    statement="Return the index of the first character of `s` that appears **only once** in `s`, or `-1` if there is none.",
    constraints="- `1 <= s.length <= 10^5`\n- lowercase English letters",
    hints=["Count every letter first, then scan again for the first count of 1."],
    spec=spec("firstUnique", [("s", "string")], "int"),
    reference="""
from collections import Counter
class Solution:
    def firstUnique(self, s):
        counts = Counter(s)
        for i, ch in enumerate(s):
            if counts[ch] == 1:
                return i
        return -1
""",
    samples=[(("sentinel",), "`s` is the first letter that never repeats."), (("aabb",), None)],
    hidden=[("z",), ("aabbc",), ("ab" * 50000,), ("ab" * 49999 + "c" + "ab",)],
)

problem(
    slug="power-of-two-check", title="Power of Two?", difficulty=E, tags=["math", "bit-manipulation"],
    statement="Return `true` if `n` equals `2^k` for some integer `k >= 0`, otherwise `false`.",
    constraints="- `-2^31 <= n <= 2^31 - 1`",
    hints=["A positive power of two has exactly one bit set: `n & (n - 1) == 0`."],
    spec=spec("isPowerOfTwo", [("n", "int")], "bool"),
    reference="""
class Solution:
    def isPowerOfTwo(self, n):
        return n > 0 and n & (n - 1) == 0
""",
    samples=[((16,), None), ((12,), None), ((1,), "2^0 = 1.")],
    hidden=[(0,), (-8,), (2**30,), (2**31 - 1,), (-(2**31),)],
)

problem(
    slug="roman-numeral-value", title="Roman Numeral Value", difficulty=E, tags=["string", "math"],
    statement=(
        "Convert a valid Roman numeral to an integer. Symbols: `I`=1, `V`=5, `X`=10, `L`=50, `C`=100, `D`=500, `M`=1000. "
        "A smaller symbol placed **before** a larger one is subtracted (`IV` = 4, `XC` = 90)."
    ),
    constraints="- `1 <= s.length <= 15`\n- `s` is a valid numeral for a value in `[1, 3999]`",
    hints=["Scan left to right; subtract a value when the next symbol is larger."],
    spec=spec("romanValue", [("s", "string")], "int"),
    reference="""
class Solution:
    def romanValue(self, s):
        v = {'I': 1, 'V': 5, 'X': 10, 'L': 50, 'C': 100, 'D': 500, 'M': 1000}
        total = 0
        for i, ch in enumerate(s):
            if i + 1 < len(s) and v[ch] < v[s[i + 1]]:
                total -= v[ch]
            else:
                total += v[ch]
        return total
""",
    samples=[(("XIV",), "10 + (5 - 1) = 14."), (("MMXXVI",), None)],
    hidden=[("I",), ("IX",), ("XL",), ("CM",), ("MMMCMXCIX",), ("DCCCXC",)],
)

problem(
    slug="running-totals", title="Running Totals", difficulty=E, tags=["array", "prefix-sum"],
    statement="Return an array where element `i` is the sum of `nums[0..i]`.",
    constraints="- `1 <= nums.length <= 10^5`\n- `-10^9 <= nums[i] <= 10^9` (totals fit in 64 bits)",
    hints=["Keep one running sum while you scan."],
    spec=spec("runningTotals", [("nums", "int[]")], "long[]"),
    reference="""
class Solution:
    def runningTotals(self, nums):
        out, total = [], 0
        for x in nums:
            total += x
            out.append(total)
        return out
""",
    samples=[(([1, 2, 3, 4],), None), (([5, -5, 5],), None)],
    hidden=[([0],), ([10**9] * 1000,), (rand_ints(100000, -10**9, 10**9),)],
)

problem(
    slug="common-values", title="Common Values", difficulty=E, tags=["array", "hash-table", "sorting"],
    statement="Return the **distinct** values that appear in both `a` and `b`, sorted in increasing order.",
    constraints="- `1 <= a.length, b.length <= 10^5`\n- `-10^9 <= a[i], b[i] <= 10^9`",
    hints=["Intersect two sets, then sort."],
    spec=spec("commonValues", [("a", "int[]"), ("b", "int[]")], "int[]"),
    reference="""
class Solution:
    def commonValues(self, a, b):
        return sorted(set(a) & set(b))
""",
    samples=[(([4, 9, 5, 9], [9, 4, 9, 8, 4]), None), (([1, 2], [3]), "No common values.")],
    hidden=[([1], [1]), (rand_ints(100000, 0, 50000), rand_ints(100000, 25000, 75000))],
)

# ---------------------------------------------------------------- MEDIUM

problem(
    slug="rotate-right", title="Rotate Right", difficulty=M, tags=["array", "math"],
    statement="Return `nums` rotated to the right by `k` steps (the last `k` elements move to the front, wrapping around).",
    constraints="- `1 <= nums.length <= 10^5`\n- `0 <= k <= 10^9`",
    hints=["Only `k mod n` matters."],
    spec=spec("rotateRight", [("nums", "int[]"), ("k", "int")], "int[]"),
    reference="""
class Solution:
    def rotateRight(self, nums, k):
        k %= len(nums)
        return nums[-k:] + nums[:-k] if k else nums
""",
    samples=[(([1, 2, 3, 4, 5], 2), "[4, 5] moves to the front."), (([7, 8], 3), "3 mod 2 = 1.")],
    hidden=[([1], 0), ([1, 2, 3], 3), (list(range(100000)), 10**9)],
)

problem(
    slug="zero-sum-triplets", title="Zero-Sum Triplets", difficulty=M, tags=["array", "two-pointers", "sorting"],
    statement=(
        "Return every **distinct** triplet of values `[a, b, c]` taken from three different positions of `nums` with `a + b + c = 0`.\n\n"
        "Write each triplet in increasing order and return the list of triplets sorted lexicographically."
    ),
    constraints="- `3 <= nums.length <= 1500`\n- `-10^5 <= nums[i] <= 10^5`",
    hints=["Sort, fix the first value, then use two pointers for the other two. Skip repeated values."],
    spec=spec("zeroTriplets", [("nums", "int[]")], "int[][]"),
    reference="""
class Solution:
    def zeroTriplets(self, nums):
        nums = sorted(nums)
        out = []
        for i in range(len(nums) - 2):
            if i and nums[i] == nums[i - 1]:
                continue
            lo, hi = i + 1, len(nums) - 1
            while lo < hi:
                s = nums[i] + nums[lo] + nums[hi]
                if s < 0:
                    lo += 1
                elif s > 0:
                    hi -= 1
                else:
                    out.append([nums[i], nums[lo], nums[hi]])
                    lo += 1
                    while lo < hi and nums[lo] == nums[lo - 1]:
                        lo += 1
                    hi -= 1
        return out
""",
    samples=[(([-1, 0, 1, 2, -1, -4],), None), (([1, 2, 3],), "No triplet sums to zero.")],
    hidden=[([0, 0, 0, 0],), ([-2, 0, 1, 1, 2],), (rand_ints(1500, -50, 50),)],
)

problem(
    slug="search-rotated-list", title="Search a Rotated List", difficulty=M, tags=["array", "binary-search"],
    statement=(
        "A strictly increasing list was rotated at an unknown point (e.g. `[1,3,5,7]` → `[5,7,1,3]`). "
        "Return the index of `target` in `nums`, or `-1`. Aim for **O(log n)**."
    ),
    constraints="- `1 <= nums.length <= 10^5`\n- all values distinct",
    hints=["In every binary-search step, one half is sorted — check whether target lies inside it."],
    spec=spec("searchRotated", [("nums", "int[]"), ("target", "int")], "int"),
    reference="""
class Solution:
    def searchRotated(self, nums, target):
        lo, hi = 0, len(nums) - 1
        while lo <= hi:
            mid = (lo + hi) // 2
            if nums[mid] == target:
                return mid
            if nums[lo] <= nums[mid]:
                if nums[lo] <= target < nums[mid]:
                    hi = mid - 1
                else:
                    lo = mid + 1
            else:
                if nums[mid] < target <= nums[hi]:
                    lo = mid + 1
                else:
                    hi = mid - 1
        return -1
""",
    samples=[(([5, 7, 9, 1, 3], 1), None), (([5, 7, 9, 1, 3], 4), None)],
    hidden=[([1], 1), ([2, 1], 1), (_rotated(100000), 0)] + [((lambda r: (r, r[rng.randint(0, len(r) - 1)]))(_rotated(100000)))],
)

problem(
    slug="spiral-walk", title="Spiral Walk", difficulty=M, tags=["matrix", "simulation"],
    statement="Return all values of the `rows × cols` grid `grid` in **clockwise spiral order**, starting at the top-left corner.",
    constraints="- `1 <= rows, cols <= 100`",
    hints=["Keep four boundaries (top, bottom, left, right) and shrink them after each side."],
    spec=spec("spiral", [("grid", "int[][]")], "int[]"),
    reference="""
class Solution:
    def spiral(self, grid):
        out = []
        top, bottom, left, right = 0, len(grid) - 1, 0, len(grid[0]) - 1
        while top <= bottom and left <= right:
            out += [grid[top][c] for c in range(left, right + 1)]
            out += [grid[r][right] for r in range(top + 1, bottom + 1)]
            if top < bottom:
                out += [grid[bottom][c] for c in range(right - 1, left - 1, -1)]
            if left < right:
                out += [grid[r][left] for r in range(bottom - 1, top, -1)]
            top, bottom, left, right = top + 1, bottom - 1, left + 1, right - 1
        return out
""",
    samples=[(([[1, 2, 3], [4, 5, 6], [7, 8, 9]],), None), (([[1, 2, 3, 4]],), "A single row.")],
    hidden=[([[5]],), ([[1], [2], [3]],), ([[rng.randint(0, 99) for _ in range(37)] for _ in range(53)],)],
)

problem(
    slug="days-until-warmer", title="Days Until Warmer", difficulty=M, tags=["array", "stack", "monotonic-stack"],
    statement="`temps[i]` is the temperature on day `i`. For each day return how many days you must wait for a **strictly warmer** day, or `0` if none comes.",
    constraints="- `1 <= temps.length <= 10^5`\n- `-50 <= temps[i] <= 60`",
    hints=["Keep a stack of days still waiting for a warmer temperature."],
    spec=spec("daysUntilWarmer", [("temps", "int[]")], "int[]"),
    reference="""
class Solution:
    def daysUntilWarmer(self, temps):
        out, stack = [0] * len(temps), []
        for i, t in enumerate(temps):
            while stack and temps[stack[-1]] < t:
                j = stack.pop()
                out[j] = i - j
            stack.append(i)
        return out
""",
    samples=[(([21, 19, 24, 22, 25, 18],), None), (([30, 30, 30],), "Equal is not warmer.")],
    hidden=[([5],), (list(range(100000, 0, -1)),), (rand_ints(100000, -50, 60),)],
)

problem(
    slug="rooms-needed", title="Rooms Needed", difficulty=M, tags=["sorting", "heap", "sweep-line"],
    statement=(
        "Each exam slot is `[start, end)` (it ends just before `end`). Return the minimum number of rooms needed so that "
        "no two overlapping slots share a room. A slot ending at `t` and one starting at `t` can use the same room."
    ),
    constraints="- `1 <= slots.length <= 10^4`\n- `0 <= start < end <= 10^6`",
    hints=["Sort starts and ends separately and sweep through time."],
    spec=spec("roomsNeeded", [("slots", "int[][]")], "int"),
    reference="""
class Solution:
    def roomsNeeded(self, slots):
        starts = sorted(s for s, _ in slots)
        ends = sorted(e for _, e in slots)
        rooms = best = j = 0
        for s in starts:
            while ends[j] <= s:
                j += 1
                rooms -= 1
            rooms += 1
            best = max(best, rooms)
        return best
""",
    samples=[(([[0, 30], [5, 10], [15, 20]],), "[0,30) overlaps both others, which don't overlap each other."), (([[1, 3], [3, 5]],), "Back-to-back slots share a room.")],
    hidden=[([[0, 1]],), ([[0, 10]] * 50,), ([(lambda s: [s, s + rng.randint(1, 5000)])(rng.randint(0, 990000)) for _ in range(10000)],)],
)

problem(
    slug="word-segmentation", title="Word Segmentation", difficulty=M, tags=["dynamic-programming", "string", "hash-table"],
    statement="Return `true` if `s` can be split into a sequence of one or more words from `words` (words may be reused), otherwise `false`.",
    constraints="- `1 <= s.length <= 300`\n- `1 <= words.length <= 1000`, each `1..20` lowercase letters",
    hints=["can[i] = some word w ends at i and can[i - len(w)]."],
    spec=spec("canSegment", [("s", "string"), ("words", "string[]")], "bool"),
    reference="""
class Solution:
    def canSegment(self, s, words):
        vocab = set(words)
        can = [True] + [False] * len(s)
        for i in range(1, len(s) + 1):
            can[i] = any(can[j] and s[j:i] in vocab for j in range(max(0, i - 20), i))
        return can[-1]
""",
    samples=[(("examsentinel", ["exam", "sent", "inel", "sentinel"]), "exam + sentinel."), (("aaab", ["a", "aa"]), None)],
    hidden=[("a", ["a"]), ("a" * 299 + "b", ["a", "aa", "aaa"]), ("ab" * 150, ["ab", "ba", "a"])],
)

problem(
    slug="non-adjacent-max-sum", title="Non-Adjacent Max Sum", difficulty=M, tags=["dynamic-programming", "array"],
    statement="Choose values from `nums` so that **no two chosen values are next to each other**. Return the largest possible sum (choosing nothing gives 0).",
    constraints="- `1 <= nums.length <= 10^5`\n- `0 <= nums[i] <= 10^4`",
    hints=["best(i) = max(best(i-1), best(i-2) + nums[i])."],
    spec=spec("maxNonAdjacent", [("nums", "int[]")], "long"),
    reference="""
class Solution:
    def maxNonAdjacent(self, nums):
        take = skip = 0
        for x in nums:
            take, skip = skip + x, max(take, skip)
        return max(take, skip)
""",
    samples=[(([2, 7, 9, 3, 1],), "2 + 9 + 1 = 12."), (([5, 1, 1, 5],), "5 + 5 = 10.")],
    hidden=[([0],), ([4, 1],), (rand_ints(100000, 0, 10000),)],
)

problem(
    slug="grid-path-count", title="Grid Path Count", difficulty=M, tags=["dynamic-programming", "math", "combinatorics"],
    statement="A robot starts at the top-left cell of a `rows × cols` grid and may only move **right** or **down**. How many different paths reach the bottom-right cell?",
    constraints="- `1 <= rows, cols <= 25` (the answer fits in 64 bits and below 2^53)",
    hints=["Every path has (rows−1) downs and (cols−1) rights — choose where the downs go."],
    spec=spec("countPaths", [("rows", "int"), ("cols", "int")], "long"),
    reference="""
from math import comb
class Solution:
    def countPaths(self, rows, cols):
        return comb(rows + cols - 2, rows - 1)
""",
    samples=[((3, 3), "6 paths."), ((1, 7), "Only one straight path.")],
    hidden=[(1, 1), (2, 2), (10, 10), (25, 25)],
)

problem(
    slug="prerequisite-order", title="Can Finish All Courses?", difficulty=M, tags=["graph", "topological-sort", "dfs"],
    statement=(
        "There are `n` courses labelled `0..n-1`. Each pair `[a, b]` in `prereqs` means course `b` must be finished before course `a`. "
        "Return `true` if it is possible to finish every course."
    ),
    constraints="- `1 <= n <= 2000`\n- `0 <= prereqs.length <= 5000`",
    hints=["It's possible exactly when the prerequisite graph has no cycle (Kahn's algorithm)."],
    spec=spec("canFinish", [("n", "int"), ("prereqs", "int[][]")], "bool"),
    reference="""
from collections import deque
class Solution:
    def canFinish(self, n, prereqs):
        indeg = [0] * n
        nxt = [[] for _ in range(n)]
        for a, b in prereqs:
            nxt[b].append(a)
            indeg[a] += 1
        q = deque(i for i in range(n) if indeg[i] == 0)
        done = 0
        while q:
            c = q.popleft()
            done += 1
            for d in nxt[c]:
                indeg[d] -= 1
                if indeg[d] == 0:
                    q.append(d)
        return done == n
""",
    samples=[((2, [[1, 0]]), "Take 0, then 1."), ((2, [[1, 0], [0, 1]]), "0 and 1 need each other.")],
    hidden=[(1, []), (3, [[1, 0], [2, 1], [0, 2]]),
            (2000, [[i, i - 1] for i in range(1, 2000)]),
            (2000, [[i, i - 1] for i in range(1, 2000)] + [[0, 1999]])],
)

# ---------------------------------------------------------------- HARD

problem(
    slug="largest-banner", title="Largest Banner", difficulty=H, tags=["array", "stack", "monotonic-stack"],
    statement="`heights[i]` is the height of a bar of width 1 in a bar chart. Return the area of the **largest rectangle** that fits entirely inside the bars.",
    constraints="- `1 <= heights.length <= 10^5`\n- `0 <= heights[i] <= 10^4`",
    hints=["For each bar, find how far it can extend left and right while bars are at least as tall — a monotonic stack does both in O(n)."],
    spec=spec("largestRectangle", [("heights", "int[]")], "long"),
    reference="""
class Solution:
    def largestRectangle(self, heights):
        stack, best = [], 0
        for i, h in enumerate(heights + [0]):
            start = i
            while stack and stack[-1][1] >= h:
                idx, height = stack.pop()
                best = max(best, height * (i - idx))
                start = idx
            stack.append((start, h))
        return best
""",
    samples=[(([2, 1, 5, 6, 2, 3],), "Bars 5 and 6 give a 5 × 2 rectangle of area 10."), (([4, 4, 4],), None)],
    hidden=[([0],), (list(range(1, 10001)),), ([10000] * 100000,), (rand_ints(100000, 0, 10000),)],
)

problem(
    slug="window-maximums", title="Window Maximums", difficulty=H, tags=["array", "deque", "sliding-window"],
    statement="A window of size `k` slides from the left of `nums` to the right, one step at a time. Return the maximum of each window position.",
    constraints="- `1 <= k <= nums.length <= 10^5`\n- `-10^4 <= nums[i] <= 10^4`",
    hints=["Keep a deque of indices whose values are decreasing; the front is the current maximum."],
    spec=spec("windowMax", [("nums", "int[]"), ("k", "int")], "int[]"),
    reference="""
from collections import deque
class Solution:
    def windowMax(self, nums, k):
        dq, out = deque(), []
        for i, x in enumerate(nums):
            while dq and nums[dq[-1]] <= x:
                dq.pop()
            dq.append(i)
            if dq[0] <= i - k:
                dq.popleft()
            if i >= k - 1:
                out.append(nums[dq[0]])
        return out
""",
    samples=[(([1, 3, -1, -3, 5, 3, 6, 7], 3), None), (([4], 1), None)],
    hidden=[([9, 8, 7], 3), (list(range(100000)), 1000), (rand_ints(100000, -10000, 10000), 5000)],
)

problem(
    slug="peaceful-queens", title="Peaceful Queens", difficulty=H, tags=["backtracking"],
    statement="Count the ways to place `n` chess queens on an `n × n` board so that no two queens share a row, column or diagonal.",
    constraints="- `1 <= n <= 10`",
    hints=["Place one queen per row; track used columns and both diagonal directions in sets."],
    spec=spec("countPlacements", [("n", "int")], "int"),
    reference="""
class Solution:
    def countPlacements(self, n):
        def place(row, cols, d1, d2):
            if row == n:
                return 1
            total = 0
            for c in range(n):
                if c not in cols and row - c not in d1 and row + c not in d2:
                    total += place(row + 1, cols | {c}, d1 | {row - c}, d2 | {row + c})
            return total
        return place(0, frozenset(), frozenset(), frozenset())
""",
    samples=[((4,), "Two placements exist on a 4 × 4 board."), ((1,), None)],
    hidden=[(2,), (3,), (8,), (10,)],
)

problem(
    slug="longest-balanced-run", title="Longest Balanced Run", difficulty=H, tags=["string", "stack", "dynamic-programming"],
    statement="`s` contains only `(` and `)`. Return the length of the longest **contiguous** substring that is a balanced bracket sequence.",
    constraints="- `0 <= s.length <= 3 * 10^4`",
    hints=["Push indices of unmatched brackets onto a stack; the gaps between them are balanced runs."],
    spec=spec("longestBalanced", [("s", "string")], "int"),
    reference="""
class Solution:
    def longestBalanced(self, s):
        stack, best = [-1], 0
        for i, ch in enumerate(s):
            if ch == '(':
                stack.append(i)
            else:
                stack.pop()
                if not stack:
                    stack.append(i)
                else:
                    best = max(best, i - stack[-1])
        return best
""",
    samples=[((")()())",), "`()()` has length 4."), (("(()",), None), (("",), None)],
    hidden=[(")(",), ("()" * 15000,), ("".join(rng.choice("()") for _ in range(30000)),)],
)
