"""#47–#64: Arrays, Strings, Hashing, Two Pointers, Sliding Window."""

from practice_bank.common import E, H, M, problem, rand_ints, rng, spec


def _word(n: int, alphabet: str = "abc") -> str:
    return "".join(rng.choice(alphabet) for _ in range(n))


# ================================================================ Arrays

problem(
    number=47, topic="Arrays", slug="second-largest-distinct", title="Second Largest Distinct Value", difficulty=E,
    tags=["array"], complexity="O(n) time, O(1) space",
    statement="Return the second largest **distinct** value in `nums`, or `-1` if `nums` has fewer than two distinct values.",
    constraints="- `1 <= nums.length <= 10^5`\n- `0 <= nums[i] <= 10^9`",
    hints=["Track the largest and second largest values in a single pass, ignoring repeats of the largest."],
    editorial="Keep `first` and `second`. A value larger than `first` pushes `first` down to `second`; a value strictly between them replaces `second`. Equal values are ignored, so duplicates of the maximum don't count.",
    spec=spec("secondLargest", [("nums", "int[]")], "int"),
    reference="""
class Solution:
    def secondLargest(self, nums):
        first = second = -1
        for x in nums:
            if x > first:
                first, second = x, first
            elif first > x > second:
                second = x
        return second
""",
    samples=[(([7, 3, 9, 9, 4],), "Distinct values are 3, 4, 7, 9; the second largest is 7."), (([5, 5],), "Only one distinct value."), (([2, 8],), None)],
    hidden=[([0],), ([1, 0],), ([10**9] * 1000 + [5],), (rand_ints(100000, 0, 10**9),)],
)

problem(
    number=48, topic="Arrays", slug="next-arrangement", title="Next Arrangement", difficulty=M,
    tags=["array", "two-pointers"], complexity="O(n) time, O(1) extra space",
    statement=(
        "Return the **next lexicographically greater** arrangement of `nums` (a permutation of the same values). "
        "If `nums` is already the greatest arrangement, return the smallest one (values sorted ascending)."
    ),
    constraints="- `1 <= nums.length <= 10^4`\n- `0 <= nums[i] <= 100`",
    hints=["Find the rightmost position i with nums[i] < nums[i + 1]; everything after it is non-increasing.",
           "Swap nums[i] with the rightmost value larger than it, then reverse the suffix."],
    editorial="Scan from the right for the first `i` with `nums[i] < nums[i+1]`. If none exists, reverse everything. Otherwise swap `nums[i]` with the rightmost element greater than it and reverse the suffix after `i`, which turns the largest suffix into the smallest.",
    spec=spec("nextArrangement", [("nums", "int[]")], "int[]"),
    reference="""
class Solution:
    def nextArrangement(self, nums):
        a = list(nums)
        i = len(a) - 2
        while i >= 0 and a[i] >= a[i + 1]:
            i -= 1
        if i >= 0:
            j = len(a) - 1
            while a[j] <= a[i]:
                j -= 1
            a[i], a[j] = a[j], a[i]
        a[i + 1:] = reversed(a[i + 1:])
        return a
""",
    samples=[(([1, 2, 3],), None), (([3, 2, 1],), "Already the greatest arrangement, so wrap around."), (([1, 1, 5],), None)],
    hidden=[([1],), ([1, 3, 2],), ([2, 3, 1, 3, 3],), (rand_ints(10000, 0, 100),), (sorted(rand_ints(10000, 0, 100), reverse=True),)],
)

problem(
    number=49, topic="Arrays", slug="rotate-square-grid", title="Rotate a Square Grid", difficulty=M,
    tags=["array", "matrix"], complexity="O(n²) time",
    statement="Return the `n × n` grid `grid` rotated **90 degrees clockwise**.",
    constraints="- `1 <= n <= 200`",
    hints=["Row r of the result is column r of the original, read from bottom to top."],
    editorial="The cell at (r, c) moves to (c, n − 1 − r). Equivalently transpose the grid and reverse each row; done in place this needs O(1) extra space.",
    spec=spec("rotateGrid", [("grid", "int[][]")], "int[][]"),
    reference="""
class Solution:
    def rotateGrid(self, grid):
        return [list(row) for row in zip(*grid[::-1])]
""",
    samples=[(([[1, 2, 3], [4, 5, 6], [7, 8, 9]],), None), (([[1, 2], [3, 4]],), None)],
    hidden=[([[5]],), ([[rng.randint(-99, 99) for _ in range(200)] for _ in range(200)],)],
)

# ================================================================ Strings

problem(
    number=50, topic="Strings", slug="longest-shared-prefix", title="Longest Shared Prefix", difficulty=E,
    tags=["string"], complexity="O(total characters) time",
    statement="Return the longest string that is a prefix of **every** word in `words`. Return an empty string if there is none.",
    constraints="- `1 <= words.length <= 1000`\n- `0 <= words[i].length <= 200`\n- lowercase English letters",
    hints=["The prefix can be no longer than the shortest word; compare character by character."],
    editorial="Take the first word as a candidate and shorten it until every other word starts with it (or compare column by column until a mismatch).",
    spec=spec("sharedPrefix", [("words", "string[]")], "string"),
    reference="""
class Solution:
    def sharedPrefix(self, words):
        prefix = words[0]
        for w in words[1:]:
            while not w.startswith(prefix):
                prefix = prefix[:-1]
        return prefix
""",
    samples=[((["interview", "internal", "interval"],), None), ((["exam", "proctor"],), "No common first letter.")],
    hidden=[([""],), (["a"],), (["same"] * 1000,), (["ab" * 100 + _word(5) for _ in range(1000)],)],
)

problem(
    number=51, topic="Strings", slug="run-length-compress", title="Run-Length Compress", difficulty=E,
    tags=["string"], complexity="O(n) time",
    statement=(
        "Compress `s` by replacing every run of the same character with the character followed by the run length. "
        "Runs of length 1 are written as the character alone. Example: `aaabcc` → `a3bc2`."
    ),
    constraints="- `1 <= s.length <= 10^5`\n- lowercase English letters",
    hints=["Walk the string, counting how long each run lasts."],
    editorial="Scan once, extending a run while the character repeats; append the character and, if the run is longer than one, its length. Build the result in a list/StringBuilder to stay O(n).",
    spec=spec("compress", [("s", "string")], "string"),
    reference="""
class Solution:
    def compress(self, s):
        out, i = [], 0
        while i < len(s):
            j = i
            while j < len(s) and s[j] == s[i]:
                j += 1
            out.append(s[i] + (str(j - i) if j - i > 1 else ""))
            i = j
        return "".join(out)
""",
    samples=[(("aaabcc",), None), (("abc",), "No run is longer than one.")],
    hidden=[("z",), ("a" * 100000,), (_word(100000, "ab"),)],
)

problem(
    number=52, topic="Strings", slug="longest-palindrome-length", title="Longest Palindromic Substring Length", difficulty=M,
    tags=["string", "dynamic-programming", "expand-around-center"], complexity="O(n²) time, O(1) space",
    statement="Return the length of the longest **contiguous** substring of `s` that reads the same forwards and backwards.",
    constraints="- `1 <= s.length <= 2000`\n- lowercase English letters",
    hints=["Every palindrome has a center (a character or a gap between two). Expand around each center."],
    editorial="Try all 2n − 1 centers and expand while both ends match; the longest expansion wins. (Manacher's algorithm achieves O(n).)",
    spec=spec("longestPalindrome", [("s", "string")], "int"),
    reference="""
class Solution:
    def longestPalindrome(self, s):
        best = 0
        for center in range(2 * len(s) - 1):
            l, r = center // 2, (center + 1) // 2
            while l >= 0 and r < len(s) and s[l] == s[r]:
                l, r = l - 1, r + 1
            best = max(best, r - l - 1)
        return best
""",
    samples=[(("racecars",), "`racecar` has length 7."), (("abba",), None), (("xyz",), "Any single letter is a palindrome.")],
    hidden=[("a",), ("a" * 2000,), (_word(2000, "ab"),), (_word(2000),)],
)

problem(
    number=53, topic="Strings", slug="parse-integer", title="Parse an Integer", difficulty=M,
    tags=["string", "parsing"], complexity="O(n) time",
    statement=(
        "Convert `s` to a 32-bit signed integer:\n\n"
        "1. Skip leading spaces.\n2. Read an optional `+` or `-` sign.\n"
        "3. Read digits until the first non-digit character (ignore the rest of the string).\n"
        "4. If no digits were read, the result is `0`.\n"
        "5. Clamp the value to the range `[-2^31, 2^31 - 1]`."
    ),
    constraints="- `0 <= s.length <= 200`\n- `s` contains letters, digits, spaces, `+`, `-` and `.`",
    hints=["Follow the steps literally; clamp at the end (or as soon as the value leaves the range)."],
    editorial="A small state machine: skip spaces, read one sign, accumulate digits. Clamp to [−2^31, 2^31 − 1]; in fixed-width languages check for overflow before multiplying by 10.",
    spec=spec("parseInteger", [("s", "string")], "int"),
    reference="""
class Solution:
    def parseInteger(self, s):
        i, n = 0, len(s)
        while i < n and s[i] == ' ':
            i += 1
        sign = 1
        if i < n and s[i] in '+-':
            sign = -1 if s[i] == '-' else 1
            i += 1
        value = 0
        while i < n and s[i].isdigit():
            value = value * 10 + int(s[i])
            i += 1
        return max(-2**31, min(2**31 - 1, sign * value))
""",
    samples=[(("   -42abc",), "Spaces skipped, sign read, digits stop at 'a'."), (("4193 with words",), None), (("words 987",), "No digits before a non-digit, so 0.")],
    hidden=[("",), ("+",), ("-91283472332",), ("91283472332",), ("  +0 123",), ("-+12",), ("00000123",), ("3.14159",)],
)

problem(
    number=54, topic="Strings", slug="shortest-palindrome-prefix", title="Fewest Letters to Make a Palindrome", difficulty=H,
    tags=["string", "kmp", "hashing"], complexity="O(n) time with KMP",
    statement="You may only add characters to the **front** of `s`. Return the minimum number of characters to add so that `s` becomes a palindrome.",
    constraints="- `0 <= s.length <= 5 * 10^4`\n- lowercase English letters",
    hints=["Find the longest prefix of s that is a palindrome; everything after it must be mirrored in front.",
           "The KMP failure function of s + '#' + reverse(s) gives that prefix length."],
    editorial="If the longest palindromic prefix has length p, exactly n − p characters (the reversed rest) must be added. Compute p with the KMP prefix function of `s + '#' + reverse(s)`: its final value is p.",
    spec=spec("lettersToAdd", [("s", "string")], "int"),
    reference="""
class Solution:
    def lettersToAdd(self, s):
        t = s + '#' + s[::-1]
        fail = [0] * len(t)
        for i in range(1, len(t)):
            k = fail[i - 1]
            while k and t[i] != t[k]:
                k = fail[k - 1]
            if t[i] == t[k]:
                k += 1
            fail[i] = k
        return len(s) - fail[-1]
""",
    samples=[(("aacecaaa",), "Adding one 'a' gives aaacecaaa."), (("abcd",), "Add 'dcb'."), (("",), None)],
    hidden=[("a",), ("aba",), ("ab",), ("a" * 25000 + "b" + "a" * 24999,), (_word(50000, "ab"),)],
)

# ================================================================ Hashing

problem(
    number=55, topic="Hashing", slug="same-shape-strings", title="Same-Shape Strings", difficulty=E,
    tags=["hash-table", "string"], complexity="O(n) time",
    statement=(
        "Strings `a` and `b` have the same shape if the letters of `a` can be replaced to obtain `b`, where every occurrence of a "
        "letter is replaced by the same letter and no two different letters map to the same letter. Return `true` if they do."
    ),
    constraints="- `1 <= a.length == b.length <= 5 * 10^4`\n- printable ASCII",
    hints=["Keep two maps: a→b and b→a. Any conflict means the shapes differ."],
    editorial="Scan both strings together and record the mapping in both directions; a mismatch in either map breaks the one-to-one correspondence.",
    spec=spec("sameShape", [("a", "string"), ("b", "string")], "bool"),
    reference="""
class Solution:
    def sameShape(self, a, b):
        fwd, back = {}, {}
        for x, y in zip(a, b):
            if fwd.setdefault(x, y) != y or back.setdefault(y, x) != x:
                return False
        return True
""",
    samples=[(("paper", "title"), None), (("foo", "bar"), "Both o's would need to become different letters."), (("ab", "aa"), "Two letters can't map to the same one.")],
    hidden=[("a", "b"), ("abab", "cdcd"), ("abab", "cdcc"),
            (lambda w: (w, w.translate(str.maketrans("abc", "xyz"))))(_word(50000)),
            (lambda w: (w, w.translate(str.maketrans("abc", "xyx"))))(_word(50000))],
)

problem(
    number=56, topic="Hashing", slug="subarrays-with-sum", title="Subarrays With a Given Sum", difficulty=M,
    tags=["hash-table", "prefix-sum", "array"], complexity="O(n) time, O(n) space",
    statement="Return how many **contiguous** non-empty subarrays of `nums` add up to exactly `k`.",
    constraints="- `1 <= nums.length <= 2 * 10^4`\n- `-1000 <= nums[i] <= 1000`\n- `-10^7 <= k <= 10^7`",
    hints=["sum(i..j) = prefix[j+1] − prefix[i]. Count earlier prefixes equal to prefix − k."],
    editorial="Walk the array keeping a running prefix sum and a hash map from prefix value to how often it occurred. Each position adds `count[prefix − k]` subarrays ending there. Negative numbers rule out a sliding window.",
    spec=spec("countSubarrays", [("nums", "int[]"), ("k", "int")], "int"),
    reference="""
from collections import defaultdict
class Solution:
    def countSubarrays(self, nums, k):
        seen = defaultdict(int)
        seen[0] = 1
        total = count = 0
        for x in nums:
            total += x
            count += seen[total - k]
            seen[total] += 1
        return count
""",
    samples=[(([1, 1, 1], 2), "[1,1] starting at index 0 and at index 1."), (([1, -1, 0], 0), "[1,-1], [0] and [1,-1,0].")],
    hidden=[([5], 5), ([0] * 2000, 0), (rand_ints(20000, -5, 5), 3)],
)

problem(
    number=57, topic="Hashing", slug="longest-consecutive-run", title="Longest Consecutive Run", difficulty=M,
    tags=["hash-table", "union-find"], complexity="O(n) time with a hash set",
    statement="Return the length of the longest run of **consecutive integers** (like 4, 5, 6, 7) whose values all appear in `nums`. The order of `nums` doesn't matter.",
    constraints="- `0 <= nums.length <= 10^5`\n- `-10^9 <= nums[i] <= 10^9`",
    hints=["Only start counting at values x where x − 1 is not present."],
    editorial="Put all values in a set. For each value that starts a run (its predecessor is absent), count upward while the next value exists. Each value is visited O(1) times, so the whole thing is linear.",
    spec=spec("longestRun", [("nums", "int[]")], "int"),
    reference="""
class Solution:
    def longestRun(self, nums):
        values = set(nums)
        best = 0
        for x in values:
            if x - 1 not in values:
                y = x
                while y + 1 in values:
                    y += 1
                best = max(best, y - x + 1)
        return best
""",
    samples=[(([100, 4, 200, 1, 3, 2],), "1, 2, 3, 4."), (([],), None), (([9, 9, 10],), "Duplicates count once.")],
    hidden=[([0],), (list(range(100000, 0, -1)),), (rand_ints(100000, -10**6, 10**6),)],
)

problem(
    number=58, topic="Hashing", slug="follows-pattern", title="Follows the Pattern", difficulty=E,
    tags=["hash-table", "string"], complexity="O(n) time",
    statement=(
        "`pattern` is a string of letters and `s` is a sentence of words separated by single spaces. Return `true` if there is a "
        "one-to-one correspondence between pattern letters and words such that replacing each letter gives `s`."
    ),
    constraints="- `1 <= pattern.length <= 300`\n- `1 <= s.length <= 3000`, lowercase words separated by single spaces",
    hints=["The number of words must equal the pattern length; then check the mapping both ways."],
    editorial="Split s into words; lengths must match. Maintain letter→word and word→letter maps and reject any conflicting assignment.",
    spec=spec("followsPattern", [("pattern", "string"), ("s", "string")], "bool"),
    reference="""
class Solution:
    def followsPattern(self, pattern, s):
        words = s.split(' ')
        if len(words) != len(pattern):
            return False
        fwd, back = {}, {}
        for ch, w in zip(pattern, words):
            if fwd.setdefault(ch, w) != w or back.setdefault(w, ch) != ch:
                return False
        return True
""",
    samples=[(("abba", "dog cat cat dog"), None), (("abba", "dog cat cat fish"), None), (("aaaa", "dog cat cat dog"), None)],
    hidden=[("a", "x"), ("ab", "x x"), ("abc", "x y"), ("ab" * 150, " ".join(["red", "blue"] * 150))],
)

# ================================================================ Two Pointers

problem(
    number=59, topic="Two Pointers", slug="sorted-squares", title="Squares of a Sorted List", difficulty=E,
    tags=["array", "two-pointers"], complexity="O(n) time",
    statement="`nums` is sorted in non-decreasing order and may contain negatives. Return the squares of its values, also sorted in non-decreasing order.",
    constraints="- `1 <= nums.length <= 10^5`\n- `-10^4 <= nums[i] <= 10^4`",
    hints=["The largest square is at one of the two ends."],
    editorial="Compare the absolute values at both ends; the larger square goes to the back of the result and its pointer moves inward. Fill the output from the end.",
    spec=spec("sortedSquares", [("nums", "int[]")], "int[]"),
    reference="""
class Solution:
    def sortedSquares(self, nums):
        out = [0] * len(nums)
        l, r, w = 0, len(nums) - 1, len(nums) - 1
        while l <= r:
            if abs(nums[l]) > abs(nums[r]):
                out[w] = nums[l] * nums[l]
                l += 1
            else:
                out[w] = nums[r] * nums[r]
                r -= 1
            w -= 1
        return out
""",
    samples=[(([-4, -1, 0, 3, 10],), None), (([-7, -3, 2, 3, 11],), None)],
    hidden=[([0],), ([-5, -5],), (sorted(rand_ints(100000, -10**4, 10**4)),)],
)

problem(
    number=60, topic="Two Pointers", slug="widest-water-container", title="Widest Water Container", difficulty=M,
    tags=["array", "two-pointers", "greedy"], complexity="O(n) time",
    statement=(
        "`heights[i]` is the height of a vertical line at position i. Choose two lines; together with the x-axis they form a container "
        "holding `min(h_i, h_j) × (j − i)` water. Return the maximum water a container can hold."
    ),
    constraints="- `2 <= heights.length <= 10^5`\n- `0 <= heights[i] <= 10^4`",
    hints=["Start with the widest pair and always move the shorter line inward."],
    editorial="With pointers at both ends, the area is limited by the shorter line; moving the taller one can never help, so move the shorter one inward and keep the best area. O(n) instead of checking all pairs.",
    spec=spec("maxWater", [("heights", "int[]")], "int"),
    reference="""
class Solution:
    def maxWater(self, heights):
        l, r, best = 0, len(heights) - 1, 0
        while l < r:
            best = max(best, min(heights[l], heights[r]) * (r - l))
            if heights[l] < heights[r]:
                l += 1
            else:
                r -= 1
        return best
""",
    samples=[(([1, 8, 6, 2, 5, 4, 8, 3, 7],), "Lines at index 1 and 8: min(8, 7) × 7 = 49."), (([1, 1],), None)],
    hidden=[([0, 0],), (list(range(1, 10001)),), (rand_ints(100000, 0, 10000),)],
)

# ================================================================ Sliding Window

problem(
    number=61, topic="Sliding Window", slug="best-window-sum", title="Best Window Sum", difficulty=E,
    tags=["array", "sliding-window"], complexity="O(n) time, O(1) space",
    statement="Return the largest sum of any `k` **consecutive** elements of `nums`.",
    constraints="- `1 <= k <= nums.length <= 10^5`\n- `-10^9 <= nums[i] <= 10^9` (sums fit in 64 bits)",
    hints=["Slide the window one step: add the new element, subtract the one that left."],
    editorial="Compute the first window's sum, then slide: add `nums[i]`, subtract `nums[i − k]`, and track the maximum. Use 64-bit integers.",
    spec=spec("bestWindow", [("nums", "int[]"), ("k", "int")], "long"),
    reference="""
class Solution:
    def bestWindow(self, nums, k):
        cur = sum(nums[:k])
        best = cur
        for i in range(k, len(nums)):
            cur += nums[i] - nums[i - k]
            best = max(best, cur)
        return best
""",
    samples=[(([2, 1, 5, 1, 3, 2], 3), "5 + 1 + 3 = 9."), (([-1, -2, -3], 2), None)],
    hidden=[([7], 1), ([10**9] * 1000, 1000), (rand_ints(100000, -10**9, 10**9), 777)],
)

problem(
    number=62, topic="Sliding Window", slug="ones-after-flips", title="Longest Ones After Flips", difficulty=M,
    tags=["array", "sliding-window"], complexity="O(n) time",
    statement="`bits` contains only 0s and 1s. You may flip at most `k` zeros to ones. Return the length of the longest run of consecutive 1s you can obtain.",
    constraints="- `1 <= bits.length <= 10^5`\n- `0 <= k <= bits.length`",
    hints=["Find the longest window that contains at most k zeros."],
    editorial="Grow the window to the right; when it contains more than k zeros, shrink it from the left until it is valid again. The largest valid window is the answer.",
    spec=spec("longestOnes", [("bits", "int[]"), ("k", "int")], "int"),
    reference="""
class Solution:
    def longestOnes(self, bits, k):
        left = zeros = best = 0
        for right, b in enumerate(bits):
            zeros += b == 0
            while zeros > k:
                zeros -= bits[left] == 0
                left += 1
            best = max(best, right - left + 1)
        return best
""",
    samples=[(([1, 1, 0, 0, 1, 1, 1, 0, 1], 1), "Flip the 0 at index 7."), (([0, 0, 0], 0), None)],
    hidden=[([1], 0), ([0] * 1000, 1000), ([rng.choice([0, 1, 1]) for _ in range(100000)], 50)],
)

problem(
    number=63, topic="Sliding Window", slug="anagram-positions", title="Anagram Positions", difficulty=M,
    tags=["string", "sliding-window", "hash-table"], complexity="O(n) time",
    statement="Return every start index i (in increasing order) such that `s[i .. i + len(p) − 1]` is an anagram of `p`.",
    constraints="- `1 <= s.length, p.length <= 3 * 10^4`\n- lowercase English letters",
    hints=["Keep letter counts for a window of length len(p) and slide it."],
    editorial="Maintain 26 counts for the current window and compare with p's counts (or track how many letters differ). Sliding adds one letter and removes one, so each step is O(1).",
    spec=spec("anagramStarts", [("s", "string"), ("p", "string")], "int[]"),
    reference="""
from collections import Counter
class Solution:
    def anagramStarts(self, s, p):
        need, window, out = Counter(p), Counter(), []
        for i, ch in enumerate(s):
            window[ch] += 1
            if i >= len(p):
                old = s[i - len(p)]
                window[old] -= 1
                if window[old] == 0:
                    del window[old]
            if window == need:
                out.append(i - len(p) + 1)
        return out
""",
    samples=[(("cbaebabacd", "abc"), "Windows at 0 ('cba') and 6 ('bac')."), (("abab", "ab"), None)],
    hidden=[("a", "ab"), ("aaaa", "a"), (_word(30000, "ab"), "abba")],
)

problem(
    number=64, topic="Sliding Window", slug="smallest-covering-window", title="Smallest Covering Window", difficulty=H,
    tags=["string", "sliding-window", "hash-table"], complexity="O(|s| + |t|) time",
    statement=(
        "Return the length of the shortest substring of `s` that contains every character of `t` **with multiplicity** "
        "(if `t` has two 'a's, the window needs at least two). Return `0` if no such substring exists."
    ),
    constraints="- `1 <= s.length, t.length <= 10^5`\n- English letters",
    hints=["Expand the right edge until the window covers t, then shrink from the left while it still covers."],
    editorial="Keep counts still needed and the number of characters missing. Extend right until nothing is missing, then move left as far as possible while the window stays valid, recording the length. Every index enters and leaves once: O(n).",
    spec=spec("coverLength", [("s", "string"), ("t", "string")], "int"),
    reference="""
from collections import Counter
class Solution:
    def coverLength(self, s, t):
        need = Counter(t)
        missing = len(t)
        left = 0
        best = 0
        for right, ch in enumerate(s):
            if need[ch] > 0:
                missing -= 1
            need[ch] -= 1
            while missing == 0:
                if best == 0 or right - left + 1 < best:
                    best = right - left + 1
                need[s[left]] += 1
                if need[s[left]] > 0:
                    missing += 1
                left += 1
        return best
""",
    samples=[(("ADOBECODEBANC", "ABC"), "'BANC' has length 4."), (("a", "aa"), "Needs two a's."), (("ab", "b"), None)],
    hidden=[("a", "a"), ("aa", "aa"), (_word(100000, "abcdeF"), "abcFF"), (_word(100000, "ab"), "c")],
)
