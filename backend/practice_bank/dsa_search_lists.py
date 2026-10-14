"""#65–#81: Binary Search, Sorting & Searching, Linked Lists."""

from practice_bank.common import E, H, M, problem, rand_ints, rng, spec


def _rotated_distinct(n: int) -> list[int]:
    values = sorted(rng.sample(range(-10**6, 10**6), n))
    k = rng.randint(0, n - 1)
    return values[k:] + values[:k]


def _cycle_spec(name: str, ret: str) -> dict:
    s = spec(name, [("head", "ListNode"), ("pos", "int")], ret)
    s["params"][1]["internal"] = True
    s["cycle"] = {"list": "head", "pos": "pos"}
    return s


# ================================================================ Binary Search

problem(
    number=65, topic="Binary Search", slug="insert-position", title="Insert Position", difficulty=E,
    tags=["array", "binary-search"], complexity="O(log n) time",
    statement="`nums` is sorted in strictly increasing order. Return the index of `target` if present; otherwise return the index where it would be inserted to keep the order.",
    constraints="- `1 <= nums.length <= 10^5`\n- `-10^9 <= nums[i], target <= 10^9`",
    hints=["You are looking for the first index whose value is ≥ target."],
    editorial="Binary search for the lower bound: the first position with `nums[i] >= target`. If every value is smaller, that position is n.",
    spec=spec("insertPosition", [("nums", "int[]"), ("target", "int")], "int"),
    reference="""
import bisect
class Solution:
    def insertPosition(self, nums, target):
        return bisect.bisect_left(nums, target)
""",
    samples=[(([1, 3, 5, 6], 5), None), (([1, 3, 5, 6], 2), "2 would go between 1 and 3."), (([1, 3, 5, 6], 7), None)],
    hidden=[([4], 4), ([4], 1), ([4], 9), (list(range(0, 200000, 2)), 77777), (list(range(0, 200000, 2)), -5)],
)

problem(
    number=66, topic="Binary Search", slug="first-and-last-index", title="First and Last Index", difficulty=M,
    tags=["array", "binary-search"], complexity="O(log n) time",
    statement="`nums` is sorted in non-decreasing order. Return `[first, last]`, the first and last index of `target`, or `[-1, -1]` if it is absent.",
    constraints="- `0 <= nums.length <= 10^5`\n- `-10^9 <= nums[i], target <= 10^9`",
    hints=["Run two binary searches: the first index ≥ target and the first index > target."],
    editorial="first = lower_bound(target); if it is out of range or not equal to target return [-1, -1]. last = upper_bound(target) − 1. Two O(log n) searches.",
    spec=spec("firstAndLast", [("nums", "int[]"), ("target", "int")], "int[]"),
    reference="""
import bisect
class Solution:
    def firstAndLast(self, nums, target):
        lo = bisect.bisect_left(nums, target)
        if lo == len(nums) or nums[lo] != target:
            return [-1, -1]
        return [lo, bisect.bisect_right(nums, target) - 1]
""",
    samples=[(([5, 7, 7, 8, 8, 10], 8), None), (([5, 7, 7, 8, 8, 10], 6), None), (([], 0), None)],
    hidden=[([2], 2), ([2, 2, 2], 2), (sorted(rand_ints(100000, 0, 500)), 250), (sorted(rand_ints(100000, 0, 500)), 501)],
)

problem(
    number=67, topic="Binary Search", slug="minimum-of-rotated", title="Minimum of a Rotated List", difficulty=M,
    tags=["array", "binary-search"], complexity="O(log n) time",
    statement="A strictly increasing list of distinct values was rotated an unknown number of times (e.g. `[1,2,3,4,5]` → `[3,4,5,1,2]`). Return its minimum in O(log n).",
    constraints="- `1 <= nums.length <= 10^5`\n- distinct values",
    hints=["Compare the middle element with the last element to tell which half holds the drop."],
    editorial="If nums[mid] > nums[hi], the rotation point (minimum) is right of mid; otherwise it is at mid or to its left. Narrow until lo == hi.",
    spec=spec("rotatedMin", [("nums", "int[]")], "int"),
    reference="""
class Solution:
    def rotatedMin(self, nums):
        lo, hi = 0, len(nums) - 1
        while lo < hi:
            mid = (lo + hi) // 2
            if nums[mid] > nums[hi]:
                lo = mid + 1
            else:
                hi = mid
        return nums[lo]
""",
    samples=[(([3, 4, 5, 1, 2],), None), (([11, 13, 15, 17],), "Not rotated at all.")],
    hidden=[([7],), ([2, 1],), (_rotated_distinct(100000),), (_rotated_distinct(99999),)],
)

problem(
    number=68, topic="Binary Search", slug="split-into-k-parts", title="Split Into K Parts", difficulty=H,
    tags=["array", "binary-search", "greedy"], complexity="O(n log(sum)) time",
    statement=(
        "Split `nums` into exactly `k` non-empty **contiguous** parts. Return the smallest possible value of the **largest part sum**."
    ),
    constraints="- `1 <= nums.length <= 10^4`\n- `0 <= nums[i] <= 10^6`\n- `1 <= k <= min(50, nums.length)`",
    hints=["Binary-search the answer: for a cap X, greedily count how many parts are needed so no part exceeds X."],
    editorial="The answer lies between max(nums) and sum(nums). For a candidate cap, a greedy left-to-right scan gives the minimum number of parts; it is feasible if ≤ k. Feasibility is monotone in the cap, so binary-search the smallest feasible cap.",
    spec=spec("minLargestPart", [("nums", "int[]"), ("k", "int")], "long"),
    reference="""
class Solution:
    def minLargestPart(self, nums, k):
        def parts(cap):
            count, cur = 1, 0
            for x in nums:
                if cur + x > cap:
                    count, cur = count + 1, x
                else:
                    cur += x
            return count
        lo, hi = max(nums), sum(nums)
        while lo < hi:
            mid = (lo + hi) // 2
            if parts(mid) <= k:
                hi = mid
            else:
                lo = mid + 1
        return lo
""",
    samples=[(([7, 2, 5, 10, 8], 2), "[7,2,5] and [10,8]: the largest sum is 18."), (([1, 2, 3, 4, 5], 2), None)],
    hidden=[([5], 1), ([1, 4, 4], 3), (rand_ints(10000, 0, 10**6), 37), ([10**6] * 10000, 50)],
)

# ================================================================ Sorting & Searching

problem(
    number=69, topic="Sorting & Searching", slug="three-color-sort", title="Three-Color Sort", difficulty=E,
    tags=["array", "sorting", "two-pointers"], complexity="O(n) time, O(1) space (one pass)",
    statement="`colors` contains only the values 0, 1 and 2. Return it sorted. Try to do it in one pass without a general-purpose sort.",
    constraints="- `1 <= colors.length <= 10^5`",
    hints=["Dutch national flag: keep regions for 0s at the front and 2s at the back."],
    editorial="Three pointers: `low` (next slot for 0), `mid` (current), `high` (next slot for 2). Swap 0s to low, 2s to high, skip 1s. Each element is moved at most once.",
    spec=spec("sortColors", [("colors", "int[]")], "int[]"),
    reference="""
class Solution:
    def sortColors(self, colors):
        a = list(colors)
        low, mid, high = 0, 0, len(a) - 1
        while mid <= high:
            if a[mid] == 0:
                a[low], a[mid] = a[mid], a[low]
                low, mid = low + 1, mid + 1
            elif a[mid] == 2:
                a[mid], a[high] = a[high], a[mid]
                high -= 1
            else:
                mid += 1
        return a
""",
    samples=[(([2, 0, 2, 1, 1, 0],), None), (([2, 0, 1],), None)],
    hidden=[([1],), ([2, 2, 0],), ([rng.randint(0, 2) for _ in range(100000)],)],
)

problem(
    number=70, topic="Sorting & Searching", slug="kth-smallest-value", title="K-th Smallest Value", difficulty=M,
    tags=["array", "quickselect", "sorting"], complexity="O(n) average with quickselect",
    statement="Return the `k`-th smallest value in `nums` (1-indexed, counting duplicates).",
    constraints="- `1 <= k <= nums.length <= 10^5`\n- `-10^9 <= nums[i] <= 10^9`",
    hints=["Sorting works in O(n log n); quickselect only recurses into one side."],
    editorial="Quickselect: partition around a random pivot into <, = and > groups and continue only in the group that contains position k. Average O(n); sorting is the simpler O(n log n) alternative.",
    spec=spec("kthSmallest", [("nums", "int[]"), ("k", "int")], "int"),
    reference="""
class Solution:
    def kthSmallest(self, nums, k):
        return sorted(nums)[k - 1]
""",
    samples=[(([7, 10, 4, 3, 20, 15], 3), "Sorted: 3, 4, 7, …"), (([5, 5, 1], 2), None)],
    hidden=[([9], 1), (rand_ints(100000, -10**9, 10**9), 50000), ([3] * 100000, 99999)],
)

problem(
    number=71, topic="Sorting & Searching", slug="largest-concatenation", title="Largest Concatenation", difficulty=M,
    tags=["sorting", "greedy", "string"], complexity="O(n log n) comparisons",
    statement="Arrange the non-negative integers in `nums` so that writing them one after another forms the **largest** number. Return it as a string (no leading zeros unless the number is 0).",
    constraints="- `1 <= nums.length <= 1000`\n- `0 <= nums[i] <= 10^9`",
    hints=["Put a before b when the string a + b is larger than b + a."],
    editorial="Sort the numbers as strings with the comparator `a + b > b + a` (this order is transitive). Join them; if the first is '0', every value is zero and the answer is '0'.",
    spec=spec("largestNumber", [("nums", "int[]")], "string"),
    reference="""
from functools import cmp_to_key
class Solution:
    def largestNumber(self, nums):
        parts = sorted(map(str, nums), key=cmp_to_key(lambda a, b: (b + a > a + b) - (b + a < a + b)))
        result = "".join(parts)
        return "0" if result[0] == "0" else result
""",
    samples=[(([10, 2],), "'210' beats '102'."), (([3, 30, 34, 5, 9],), None), (([0, 0],), None)],
    hidden=[([1],), ([121, 12],), (rand_ints(1000, 0, 10**9),), (rand_ints(1000, 0, 99),)],
)

problem(
    number=72, topic="Sorting & Searching", slug="count-inversions", title="Count Inversions", difficulty=H,
    tags=["array", "merge-sort", "divide-and-conquer"], complexity="O(n log n) time",
    statement="Return the number of pairs (i, j) with `i < j` and `nums[i] > nums[j]`.",
    constraints="- `1 <= nums.length <= 10^5`\n- `-10^9 <= nums[i] <= 10^9` (the count fits in 64 bits)",
    hints=["During merge sort, when an element from the right half is placed before remaining left elements, each of them forms an inversion with it."],
    editorial="Merge sort counts inversions while merging: taking an element from the right half while k elements remain in the left half adds k inversions. Total O(n log n); the O(n²) double loop is too slow for 10^5.",
    spec=spec("countInversions", [("nums", "int[]")], "long"),
    reference="""
class Solution:
    def countInversions(self, nums):
        def sort(a):
            if len(a) <= 1:
                return a, 0
            mid = len(a) // 2
            left, x = sort(a[:mid])
            right, y = sort(a[mid:])
            merged, i, j, inv = [], 0, 0, x + y
            while i < len(left) and j < len(right):
                if left[i] <= right[j]:
                    merged.append(left[i]); i += 1
                else:
                    merged.append(right[j]); j += 1
                    inv += len(left) - i
            merged += left[i:] + right[j:]
            return merged, inv
        return sort(list(nums))[1]
""",
    samples=[(([2, 4, 1, 3, 5],), "(2,1), (4,1), (4,3)."), (([1, 2, 3],), None), (([3, 2, 1],), None)],
    hidden=[([1],), (list(range(100000, 0, -1)),), (rand_ints(100000, -10**9, 10**9),), ([7] * 50000,)],
)

problem(
    number=73, topic="Sorting & Searching", slug="custom-order-sort", title="Sort by a Custom Order", difficulty=E,
    tags=["array", "sorting", "hash-table"], complexity="O(n log n) time",
    statement=(
        "Sort `items` so that values appearing in `order` come first, in the same relative order as in `order` (repeats kept "
        "together), followed by all remaining values in ascending order. `order` has distinct values."
    ),
    constraints="- `1 <= items.length <= 10^4`\n- `0 <= order.length <= 1000`\n- `0 <= values <= 1000`",
    hints=["Sort by the key (position in order, or len(order) + value for unlisted values)."],
    editorial="Map each value in `order` to its rank. Sort items by `(rank, 0)` for listed values and `(len(order), value)` otherwise. Counting sort also works because values are ≤ 1000.",
    spec=spec("customSort", [("items", "int[]"), ("order", "int[]")], "int[]"),
    reference="""
class Solution:
    def customSort(self, items, order):
        rank = {v: i for i, v in enumerate(order)}
        return sorted(items, key=lambda v: (rank.get(v, len(order)), v))
""",
    samples=[(([2, 3, 1, 3, 2, 4, 6, 7, 9, 2, 19], [2, 1, 4, 3, 9, 6]), None), (([5, 1, 5], []), "No custom order: plain ascending.")],
    hidden=[([1], [1]), (rand_ints(10000, 0, 1000), rng.sample(range(1001), 1000)), (rand_ints(10000, 0, 1000), rng.sample(range(1001), 37))],
)

# ================================================================ Linked Lists

problem(
    number=74, topic="Linked Lists", slug="reverse-linked-list", title="Reverse a Linked List", difficulty=E,
    tags=["linked-list", "recursion"], complexity="O(n) time, O(1) space",
    statement="Reverse the singly linked list starting at `head` and return the new head.",
    constraints="- `0 <= number of nodes <= 10^5`\n- `-5000 <= node.val <= 5000`",
    hints=["Walk the list, pointing each node's next at the node before it."],
    editorial="Iteratively keep `prev` (initially null) and for each node save `next`, point `node.next` to `prev`, then advance. The last node becomes the head. The recursive version uses O(n) stack.",
    spec=spec("reverseList", [("head", "ListNode")], "ListNode"),
    reference="""
class Solution:
    def reverseList(self, head):
        prev = None
        while head:
            head.next, prev, head = prev, head, head.next
        return prev
""",
    samples=[(([1, 2, 3, 4, 5],), None), (([],), "An empty list stays empty.")],
    hidden=[([7],), ([1, 2],), (rand_ints(100000, -5000, 5000),)],
)

problem(
    number=75, topic="Linked Lists", slug="detect-list-cycle", title="Detect a Cycle", difficulty=E,
    tags=["linked-list", "two-pointers", "floyd"], complexity="O(n) time, O(1) space",
    statement=(
        "Return `true` if the linked list starting at `head` contains a cycle (following `next` pointers eventually revisits a node).\n\n"
        "In the examples, `pos` is the index of the node the tail links back to (`-1` means no cycle); `pos` is **not** passed to your method."
    ),
    constraints="- `0 <= number of nodes <= 10^4`\n- `-1 <= pos < number of nodes`",
    hints=["Move one pointer by one step and another by two. If there is a cycle they must meet."],
    editorial="Floyd's tortoise and hare: the fast pointer gains one node per step, so inside a cycle it eventually lands on the slow pointer. Without a cycle the fast pointer reaches null. O(1) extra memory, unlike storing visited nodes in a set.",
    spec=_cycle_spec("hasCycle", "bool"),
    reference="""
class Solution:
    def hasCycle(self, head):
        slow = fast = head
        while fast and fast.next:
            slow, fast = slow.next, fast.next.next
            if slow is fast:
                return True
        return False
""",
    samples=[(([3, 2, 0, -4], 1), "The tail links back to the node with value 2."), (([1, 2], 0), None), (([1], -1), "No cycle.")],
    hidden=[([], -1), ([1, 2, 3], -1), (list(range(10000)), 9999), (list(range(10000)), 0), (list(range(10000)), -1)],
)

problem(
    number=76, topic="Linked Lists", slug="merge-sorted-linked-lists", title="Merge Two Sorted Linked Lists", difficulty=E,
    tags=["linked-list", "recursion"], complexity="O(n + m) time, O(1) extra space",
    statement="`a` and `b` are linked lists sorted in non-decreasing order. Merge them into one sorted list by relinking their nodes and return its head.",
    constraints="- `0 <= nodes in each list <= 5 * 10^4`\n- `-10^5 <= node.val <= 10^5`",
    hints=["Use a dummy head and always attach the smaller current node."],
    editorial="A dummy node simplifies the head case. Repeatedly attach the smaller of the two current nodes, advance in that list, and finally attach whichever list still has nodes.",
    spec=spec("mergeLists", [("a", "ListNode"), ("b", "ListNode")], "ListNode"),
    reference="""
class Solution:
    def mergeLists(self, a, b):
        dummy = tail = ListNode()
        while a and b:
            if a.val <= b.val:
                tail.next, a = a, a.next
            else:
                tail.next, b = b, b.next
            tail = tail.next
        tail.next = a or b
        return dummy.next
""",
    samples=[(([1, 2, 4], [1, 3, 4]), None), (([], [0]), None)],
    hidden=[([], []), ([5], [1, 2, 3]), (sorted(rand_ints(50000, -10**5, 10**5)), sorted(rand_ints(50000, -10**5, 10**5)))],
)

problem(
    number=77, topic="Linked Lists", slug="middle-node", title="Middle Node", difficulty=E,
    tags=["linked-list", "two-pointers"], complexity="O(n) time, O(1) space",
    statement="Return the middle node of the list (the list from that node onward). With an even number of nodes, return the **second** of the two middle nodes.",
    constraints="- `1 <= number of nodes <= 10^5`",
    hints=["When a fast pointer moving two steps reaches the end, a slow one moving one step is in the middle."],
    editorial="Advance `slow` by one and `fast` by two while `fast` and `fast.next` exist; `slow` then sits on the (second) middle node.",
    spec=spec("middleNode", [("head", "ListNode")], "ListNode"),
    reference="""
class Solution:
    def middleNode(self, head):
        slow = fast = head
        while fast and fast.next:
            slow, fast = slow.next, fast.next.next
        return slow
""",
    samples=[(([1, 2, 3, 4, 5],), "Node 3 onward."), (([1, 2, 3, 4, 5, 6],), "Two middles (3 and 4): return 4.")],
    hidden=[([1],), ([1, 2],), (list(range(100000)),), (list(range(99999)),)],
)

problem(
    number=78, topic="Linked Lists", slug="remove-kth-from-end", title="Remove the K-th Node From the End", difficulty=M,
    tags=["linked-list", "two-pointers"], complexity="O(n) time, one pass",
    statement="Remove the `k`-th node from the **end** of the list (k = 1 is the last node) and return the head.",
    constraints="- `1 <= number of nodes <= 10^5`\n- `1 <= k <= number of nodes`",
    hints=["Move a lead pointer k steps ahead, then move both until the lead reaches the end."],
    editorial="With a dummy before the head, advance `fast` k steps, then move `fast` and `slow` together until `fast.next` is null; `slow.next` is the node to remove. The dummy handles removing the head itself.",
    spec=spec("removeFromEnd", [("head", "ListNode"), ("k", "int")], "ListNode"),
    reference="""
class Solution:
    def removeFromEnd(self, head, k):
        dummy = ListNode(0, head)
        fast = slow = dummy
        for _ in range(k):
            fast = fast.next
        while fast.next:
            fast, slow = fast.next, slow.next
        slow.next = slow.next.next
        return dummy.next
""",
    samples=[(([1, 2, 3, 4, 5], 2), "Removes 4."), (([1], 1), None), (([1, 2], 2), "Removes the head.")],
    hidden=[([1, 2], 1), (list(range(100000)), 1), (list(range(100000)), 100000), (list(range(100000)), 54321)],
)

problem(
    number=79, topic="Linked Lists", slug="add-digit-lists", title="Add Two Digit Lists", difficulty=M,
    tags=["linked-list", "math"], complexity="O(max(n, m)) time",
    statement=(
        "Two non-negative integers are stored as linked lists of digits in **reverse order** (the ones digit first). "
        "Return their sum in the same form. Neither number has leading zeros except the number 0 itself."
    ),
    constraints="- `1 <= nodes in each list <= 10^4`\n- `0 <= node.val <= 9`",
    hints=["Add digit by digit with a carry, exactly like on paper."],
    editorial="Walk both lists together, summing the digits plus carry; append `sum % 10` and carry `sum // 10`. Continue while either list or the carry remains.",
    spec=spec("addLists", [("a", "ListNode"), ("b", "ListNode")], "ListNode"),
    reference="""
class Solution:
    def addLists(self, a, b):
        dummy = tail = ListNode()
        carry = 0
        while a or b or carry:
            total = carry + (a.val if a else 0) + (b.val if b else 0)
            carry, digit = divmod(total, 10)
            tail.next = ListNode(digit)
            tail = tail.next
            a = a.next if a else None
            b = b.next if b else None
        return dummy.next
""",
    samples=[(([2, 4, 3], [5, 6, 4]), "342 + 465 = 807."), (([9, 9, 9, 9], [9, 9]), "9999 + 99 = 10098."), (([0], [0]), None)],
    hidden=[([5], [5]), ([9] * 10000, [1]), ([rng.randint(0, 9) for _ in range(9999)] + [rng.randint(1, 9)], [rng.randint(0, 9) for _ in range(9999)] + [7])],
)

problem(
    number=80, topic="Linked Lists", slug="cycle-length", title="Length of the Cycle", difficulty=M,
    tags=["linked-list", "two-pointers", "floyd"], complexity="O(n) time, O(1) space",
    statement=(
        "Return the number of nodes in the cycle of the linked list starting at `head`, or `0` if there is no cycle.\n\n"
        "In the examples, `pos` is the index the tail links back to (`-1` = no cycle); it is not passed to your method."
    ),
    constraints="- `0 <= number of nodes <= 10^4`",
    hints=["Once slow and fast meet inside the cycle, walk around it once from the meeting point."],
    editorial="Use Floyd's algorithm to find a meeting point inside the cycle, then move one pointer around until it returns to that node, counting steps. O(1) memory.",
    spec=_cycle_spec("cycleLength", "int"),
    reference="""
class Solution:
    def cycleLength(self, head):
        slow = fast = head
        while fast and fast.next:
            slow, fast = slow.next, fast.next.next
            if slow is fast:
                length, node = 1, slow.next
                while node is not slow:
                    node, length = node.next, length + 1
                return length
        return 0
""",
    samples=[(([3, 2, 0, -4], 1), "Cycle: 2 → 0 → -4 → 2."), (([1, 2], -1), None), (([7], 0), "A node pointing to itself.")],
    hidden=[([], -1), (list(range(10000)), 0), (list(range(10000)), 9999), (list(range(10000)), 4321)],
)

problem(
    number=81, topic="Linked Lists", slug="reverse-in-groups", title="Reverse in Groups of K", difficulty=H,
    tags=["linked-list", "recursion"], complexity="O(n) time, O(1) extra space",
    statement=(
        "Reverse the nodes of the list `k` at a time and return the new head. If the number of remaining nodes at the end is "
        "less than `k`, leave them in their original order. Only relink nodes; don't change their values."
    ),
    constraints="- `1 <= k <= number of nodes <= 10^5`",
    hints=["Check that k nodes remain before reversing a group, then reconnect the reversed group to the previous part."],
    editorial="Keep a pointer to the node before the current group. If k nodes remain, reverse exactly those k (standard in-place reversal), connect the previous part to the new group head and the old group head (now its tail) to the rest, then continue from that tail.",
    spec=spec("reverseGroups", [("head", "ListNode"), ("k", "int")], "ListNode"),
    reference="""
class Solution:
    def reverseGroups(self, head, k):
        dummy = ListNode(0, head)
        before = dummy
        while True:
            check = before
            for _ in range(k):
                check = check.next
                if check is None:
                    return dummy.next
            group_head = before.next
            prev, cur = None, group_head
            for _ in range(k):
                cur.next, prev, cur = prev, cur, cur.next
            before.next = prev
            group_head.next = cur
            before = group_head
""",
    samples=[(([1, 2, 3, 4, 5], 2), "Last node stays: 2,1,4,3,5."), (([1, 2, 3, 4, 5], 3), None), (([1, 2], 1), None)],
    hidden=[([1], 1), (list(range(100000)), 100000), (list(range(100000)), 7), (list(range(99999)), 2)],
)
