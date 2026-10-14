"""#104–#116: Greedy, Dynamic Programming, Graphs, Bit Manipulation."""

from practice_bank.common import E, H, M, problem, rand_ints, rng, spec

# ---------------------------------------------------------------- graph generators

def _random_edges(n: int, m: int, connected: bool = False) -> list[list[int]]:
    edges, seen = [], set()
    if connected:
        for v in range(1, n):
            u = rng.randrange(v)
            edges.append([u, v])
            seen.add((u, v))
    while len(edges) < m:
        u, v = rng.randrange(n), rng.randrange(n)
        if u != v and (min(u, v), max(u, v)) not in seen:
            seen.add((min(u, v), max(u, v)))
            edges.append([u, v])
    rng.shuffle(edges)
    return edges


def _weighted(edges: list[list[int]], lo: int, hi: int) -> list[list[int]]:
    return [[u, v, rng.randint(lo, hi)] for u, v in edges]


def _random_dag(n: int, m: int) -> list[list[int]]:
    order = list(range(n))
    rng.shuffle(order)
    edges, seen = [], set()
    while len(edges) < m:
        i, j = sorted(rng.sample(range(n), 2))
        if (i, j) not in seen:
            seen.add((i, j))
            edges.append([order[i], order[j]])
    rng.shuffle(edges)
    return edges


def _bipartite_edges(n: int, m: int) -> list[list[int]]:
    side = [rng.randint(0, 1) for _ in range(n)]
    left = [v for v in range(n) if side[v] == 0] or [0]
    right = [v for v in range(n) if side[v] == 1] or [n - 1]
    edges, seen = [], set()
    while len(edges) < m:
        u, v = rng.choice(left), rng.choice(right)
        if u != v and (min(u, v), max(u, v)) not in seen:
            seen.add((min(u, v), max(u, v)))
            edges.append([u, v])
    return edges


# ================================================================ Greedy

problem(
    number=104, topic="Greedy", slug="reach-the-end", title="Reach the Last Square", difficulty=M,
    tags=["greedy", "array"], complexity="O(n) time, O(1) space",
    statement="You start on square 0. From square `i` you may jump forward **up to** `jumps[i]` squares. Return `true` if you can reach the last square.",
    constraints="- `1 <= jumps.length <= 10^5`\n- `0 <= jumps[i] <= 10^5`",
    hints=["Track the farthest square reachable so far; if you ever stand beyond it, you are stuck."],
    editorial="Scan left to right keeping `reach`, the farthest index reachable. If i > reach the walk is stuck; otherwise reach = max(reach, i + jumps[i]). The answer is whether reach ≥ n − 1. Greedy works because any square up to `reach` is reachable.",
    spec=spec("canReachEnd", [("jumps", "int[]")], "bool"),
    reference="""
class Solution:
    def canReachEnd(self, jumps):
        reach = 0
        for i, j in enumerate(jumps):
            if i > reach:
                return False
            reach = max(reach, i + j)
        return True
""",
    samples=[(([2, 3, 1, 1, 4],), "0 → 1 → 4."), (([3, 2, 1, 0, 4],), "Every path lands on the 0 at index 3.")],
    hidden=[([0],), ([0, 1],), ([1] * 100000,), ([1] * 50000 + [0] + [1] * 49999,), (rand_ints(100000, 0, 3),)],
)

problem(
    number=105, topic="Greedy", slug="fuel-loop", title="Fuel Loop Starting Point", difficulty=M,
    tags=["greedy", "array"], complexity="O(n) time, O(1) space",
    statement=(
        "Stations `0..n-1` lie on a circular road. Station `i` gives `fuel[i]` units of fuel and driving from it to the next station costs "
        "`cost[i]`. Starting with an empty tank, return the **smallest** station index from which you can drive all the way around, or −1 if none works."
    ),
    constraints="- `1 <= n <= 10^5`\n- `0 <= fuel[i], cost[i] <= 10^4`",
    hints=["If the total fuel is less than the total cost, no start works.", "If the tank goes negative after station i, no station up to i can be the start."],
    editorial="If sum(fuel) < sum(cost) return −1. Otherwise scan once with a running tank; whenever it drops below zero, restart from the next station with an empty tank. The last restart point is a valid start, and it is the smallest one: every earlier index was ruled out by a negative running tank.",
    spec=spec("startStation", [("fuel", "int[]"), ("cost", "int[]")], "int"),
    reference="""
class Solution:
    def startStation(self, fuel, cost):
        if sum(fuel) < sum(cost):
            return -1
        start = tank = 0
        for i in range(len(fuel)):
            tank += fuel[i] - cost[i]
            if tank < 0:
                start, tank = i + 1, 0
        return start
""",
    samples=[(([1, 2, 3, 4, 5], [3, 4, 5, 1, 2]), "Start at 3 with 4 fuel."), (([2, 3, 4], [3, 4, 3]), "Total fuel 9 < total cost 10.")],
    hidden=[([5], [5]), ([0, 0, 0], [0, 0, 0]), (rand_ints(100000, 0, 10000), rand_ints(100000, 0, 10000)),
            (rand_ints(100000, 3, 10000), rand_ints(100000, 0, 5000))],
)

problem(
    number=106, topic="Greedy", slug="hand-out-snacks", title="Hand Out Snacks", difficulty=E,
    tags=["greedy", "sorting", "two-pointers"], complexity="O(n log n + m log m) time",
    statement=(
        "Child `i` is content with a snack of size at least `need[i]`. Each snack `sizes[j]` can go to one child. "
        "Return the largest number of content children."
    ),
    constraints="- `1 <= need.length, sizes.length <= 3 * 10^4`\n- `1 <= need[i], sizes[j] <= 2^31 - 1`",
    hints=["Sort both lists and give each child the smallest snack that satisfies them."],
    editorial="Sort both arrays. Walk the snacks from smallest; a snack goes to the least-demanding remaining child if it is big enough, otherwise it is useless for everyone and is skipped. Satisfying the easiest children with the smallest adequate snacks never hurts later choices.",
    spec=spec("contentChildren", [("need", "int[]"), ("sizes", "int[]")], "int"),
    reference="""
class Solution:
    def contentChildren(self, need, sizes):
        need, sizes = sorted(need), sorted(sizes)
        child = 0
        for s in sizes:
            if child < len(need) and s >= need[child]:
                child += 1
        return child
""",
    samples=[(([1, 2, 3], [1, 1]), "Only the child needing 1 can be satisfied."), (([1, 2], [1, 2, 3]), None)],
    hidden=[([5], [4]), ([2**31 - 1], [2**31 - 1]), (rand_ints(30000, 1, 10**9), rand_ints(30000, 1, 10**9)),
            (rand_ints(30000, 1, 100), rand_ints(1000, 50, 200))],
)

problem(
    number=107, topic="Greedy", slug="fewest-removals-no-overlap", title="Fewest Removals for No Overlap", difficulty=M,
    tags=["greedy", "intervals", "sorting"], complexity="O(n log n) time",
    statement="Return the smallest number of intervals `[start, end)` to remove so that the remaining intervals do not overlap. Intervals that only touch (one ends where the next starts) do not overlap.",
    constraints="- `1 <= intervals.length <= 10^5`\n- `-5 * 10^4 <= start < end <= 5 * 10^4`",
    hints=["Keep as many intervals as possible: always keep the one that ends earliest."],
    editorial="Sort by end. Greedily keep an interval when it starts at or after the end of the last kept one; otherwise remove it. Choosing the earliest-ending interval leaves the most room for the rest (classic interval scheduling), so kept is maximal and removals = n − kept.",
    spec=spec("minRemovals", [("intervals", "int[][]")], "int"),
    reference="""
class Solution:
    def minRemovals(self, intervals):
        kept, last_end = 0, -10**18
        for s, e in sorted(intervals, key=lambda iv: iv[1]):
            if s >= last_end:
                kept += 1
                last_end = e
        return len(intervals) - kept
""",
    samples=[(([[1, 2], [2, 3], [3, 4], [1, 3]],), "Removing [1,3] leaves touching intervals."), (([[1, 2], [1, 2], [1, 2]],), None)],
    hidden=[([[0, 1]],), ([[i, i + 1] for i in range(-50000, 49999, 2)],),
            ([sorted(rng.sample(range(-50000, 50001), 2)) for _ in range(100000)],)],
)

# ================================================================ Dynamic Programming

problem(
    number=108, topic="Dynamic Programming", slug="pack-the-bag", title="Pack the Bag (0/1 Knapsack)", difficulty=M,
    tags=["dynamic-programming", "knapsack"], complexity="O(n · capacity) time, O(capacity) space",
    statement="Item `i` weighs `weights[i]` and is worth `values[i]`. Each item can be taken at most once. Return the largest total value with total weight at most `capacity`.",
    constraints="- `1 <= n <= 200`\n- `1 <= weights[i] <= capacity <= 10^4`\n- `0 <= values[i] <= 10^5`",
    hints=["best[c] = best value with capacity c using the items seen so far."],
    editorial="One-dimensional DP over capacity: for each item, update best[c] = max(best[c], best[c − w] + v) for c from capacity **down** to w. Iterating downwards ensures each item is used at most once.",
    spec=spec("bestValue", [("weights", "int[]"), ("values", "int[]"), ("capacity", "int")], "int"),
    reference="""
class Solution:
    def bestValue(self, weights, values, capacity):
        best = [0] * (capacity + 1)
        for w, v in zip(weights, values):
            for c in range(capacity, w - 1, -1):
                if best[c - w] + v > best[c]:
                    best[c] = best[c - w] + v
        return best[capacity]
""",
    samples=[(([1, 3, 4, 5], [1, 4, 5, 7], 7), "Weights 3 + 4 give 4 + 5 = 9."), (([5], [10], 4), "The only item is too heavy.")],
    hidden=[([1], [0], 1), (rand_ints(200, 1, 10000), rand_ints(200, 0, 100000), 10000),
            (rand_ints(200, 1, 100), rand_ints(200, 0, 100000), 5000)],
    time_limit_ms=3000,
)

# ================================================================ Graphs

problem(
    number=109, topic="Graphs", slug="fewest-hops", title="Fewest Hops Between Two Nodes", difficulty=M,
    tags=["graph", "bfs"], complexity="O(n + edges) time",
    statement="An undirected graph has nodes `0..n-1` and the given `edges`. Return the smallest number of edges on a path from `source` to `target`, or −1 if `target` cannot be reached.",
    constraints="- `1 <= n <= 5 * 10^4`\n- `0 <= edges.length <= 10^5`\n- no self-loops or duplicate edges",
    hints=["Breadth-first search visits nodes in order of distance."],
    editorial="Build an adjacency list and run BFS from source; the first time a node is dequeued its distance is final. Return the distance recorded for target (−1 if never reached).",
    spec=spec("fewestHops", [("n", "int"), ("edges", "int[][]"), ("source", "int"), ("target", "int")], "int"),
    reference="""
from collections import deque
class Solution:
    def fewestHops(self, n, edges, source, target):
        adj = [[] for _ in range(n)]
        for u, v in edges:
            adj[u].append(v)
            adj[v].append(u)
        dist = [-1] * n
        dist[source] = 0
        queue = deque([source])
        while queue:
            u = queue.popleft()
            for v in adj[u]:
                if dist[v] < 0:
                    dist[v] = dist[u] + 1
                    queue.append(v)
        return dist[target]
""",
    samples=[((6, [[0, 1], [1, 2], [0, 3], [3, 4], [4, 2], [2, 5]], 0, 5), "0 → 1 → 2 → 5."), ((3, [[0, 1]], 0, 2), None), ((1, [], 0, 0), None)],
    hidden=[(50000, [[i, i + 1] for i in range(49999)], 0, 49999), (50000, _random_edges(50000, 75000), 5, 37777),
            (30000, _random_edges(30000, 100000, connected=True), 0, 29999)],
)

problem(
    number=110, topic="Graphs", slug="cheapest-routes", title="Cheapest Routes From a Source", difficulty=M,
    tags=["graph", "dijkstra", "heap", "shortest-path"], complexity="O((n + edges) log n) time",
    statement=(
        "A directed graph has nodes `0..n-1`. Each edge `[u, v, w]` goes from u to v with non-negative cost w. "
        "Return an array whose i-th entry is the cheapest total cost from `source` to node i, or −1 if node i is unreachable."
    ),
    constraints="- `1 <= n <= 5 * 10^4`\n- `0 <= edges.length <= 10^5`\n- `0 <= w <= 10^9` (totals may exceed 32 bits)",
    hints=["Dijkstra's algorithm with a min-heap of (distance, node)."],
    editorial="Dijkstra: pop the closest unsettled node from a min-heap and relax its outgoing edges, skipping stale heap entries. Non-negative weights guarantee a popped distance is final. Use 64-bit integers — a path of many 10^9 edges overflows 32 bits.",
    spec=spec("cheapestRoutes", [("n", "int"), ("edges", "int[][]"), ("source", "int")], "long[]"),
    reference="""
import heapq
class Solution:
    def cheapestRoutes(self, n, edges, source):
        adj = [[] for _ in range(n)]
        for u, v, w in edges:
            adj[u].append((v, w))
        dist = [-1] * n
        heap = [(0, source)]
        while heap:
            d, u = heapq.heappop(heap)
            if dist[u] >= 0:
                continue
            dist[u] = d
            for v, w in adj[u]:
                if dist[v] < 0:
                    heapq.heappush(heap, (d + w, v))
        return dist
""",
    samples=[((4, [[0, 1, 4], [0, 2, 1], [2, 1, 2], [1, 3, 5]], 0), "0 → 2 → 1 costs 3, cheaper than the direct 4."), ((3, [[1, 2, 7]], 0), None)],
    hidden=[(1, [], 0), (50000, [[i, i + 1, 10**9] for i in range(49999)], 0),
            (50000, _weighted(_random_edges(50000, 100000), 0, 10**6), 3),
            (20000, _weighted(_random_edges(20000, 100000, connected=True), 0, 10**9), 0)],
)


TOPO_CHECKER = """
def check(args, output, expected):
    n, edges = args
    if not isinstance(output, list) or sorted(output) != list(range(n)):
        return False
    position = {node: i for i, node in enumerate(output)}
    return all(position[u] < position[v] for u, v in edges)
"""

problem(
    number=111, topic="Graphs", slug="task-ordering", title="Order the Tasks", difficulty=M,
    tags=["graph", "topological-sort", "bfs"], complexity="O(n + edges) time",
    statement=(
        "Tasks are labelled `0..n-1`. Each pair `[u, v]` in `deps` means task u must be done before task v. "
        "The dependencies contain no cycle. Return any ordering of all n tasks that respects every dependency."
    ),
    input_format="`n` (int), then `deps` (2-D int array of `[u, v]` pairs).",
    output_format="An int array: a permutation of `0..n-1`. **Any** valid order is accepted — a checker verifies it.",
    constraints="- `1 <= n <= 5 * 10^4`\n- `0 <= deps.length <= 10^5`\n- the dependency graph is acyclic",
    hints=["Repeatedly output a task with no remaining unmet dependencies (Kahn's algorithm)."],
    editorial="Kahn's algorithm: compute in-degrees, start a queue with every in-degree-0 task, and each time you output a task decrement its successors' in-degrees, enqueueing those that reach 0. A DFS that emits nodes in reverse post-order also works. Many orders are valid, so this problem is judged by a checker rather than by exact comparison.",
    spec=spec("taskOrder", [("n", "int"), ("deps", "int[][]")], "int[]"), compare="checker", checker=TOPO_CHECKER,
    reference="""
from collections import deque
class Solution:
    def taskOrder(self, n, deps):
        adj = [[] for _ in range(n)]
        indeg = [0] * n
        for u, v in deps:
            adj[u].append(v)
            indeg[v] += 1
        queue = deque(i for i in range(n) if indeg[i] == 0)
        order = []
        while queue:
            u = queue.popleft()
            order.append(u)
            for v in adj[u]:
                indeg[v] -= 1
                if indeg[v] == 0:
                    queue.append(v)
        return order
""",
    samples=[((4, [[1, 0], [2, 0], [3, 1], [3, 2]]), "3 first, then 1 and 2 in either order, then 0."), ((2, []), "Both orders are accepted.")],
    hidden=[(1, []), (50000, [[i, i + 1] for i in range(49999)]), (50000, _random_dag(50000, 100000)), (500, _random_dag(500, 50000))],
)

problem(
    number=112, topic="Graphs", slug="two-team-split", title="Split Into Two Teams", difficulty=M,
    tags=["graph", "bfs", "bipartite"], complexity="O(n + edges) time",
    statement="People `0..n-1` must be split into two teams. Each pair in `rivals` must end up on **different** teams. Return `true` if this is possible (that is, if the graph is bipartite).",
    constraints="- `1 <= n <= 5 * 10^4`\n- `0 <= rivals.length <= 10^5`\n- no self-pairs or duplicates",
    hints=["Colour each connected component with BFS, alternating colours; a conflict means an odd cycle."],
    editorial="For every uncoloured node, BFS and colour neighbours with the opposite colour. If an edge ever joins two nodes of the same colour the graph has an odd cycle and cannot be split. Remember the graph may be disconnected.",
    spec=spec("canSplit", [("n", "int"), ("rivals", "int[][]")], "bool"),
    reference="""
from collections import deque
class Solution:
    def canSplit(self, n, rivals):
        adj = [[] for _ in range(n)]
        for u, v in rivals:
            adj[u].append(v)
            adj[v].append(u)
        colour = [-1] * n
        for s in range(n):
            if colour[s] >= 0:
                continue
            colour[s] = 0
            queue = deque([s])
            while queue:
                u = queue.popleft()
                for v in adj[u]:
                    if colour[v] < 0:
                        colour[v] = 1 - colour[u]
                        queue.append(v)
                    elif colour[v] == colour[u]:
                        return False
        return True
""",
    samples=[((4, [[0, 1], [1, 2], [2, 3], [3, 0]]), "Teams {0, 2} and {1, 3}."), ((3, [[0, 1], [1, 2], [2, 0]]), "A triangle cannot be split.")],
    hidden=[(1, []), (50000, _bipartite_edges(50000, 100000)), (50000, _random_edges(50000, 100000)),
            (49999, [[i, (i + 1) % 49999] for i in range(49999)])],
)

problem(
    number=113, topic="Graphs", slug="count-groups", title="Count Connected Groups", difficulty=M,
    tags=["graph", "union-find", "dfs"], complexity="O((n + edges) · α(n)) time",
    statement="An undirected graph has nodes `0..n-1` and the given `edges`. Return the number of connected components.",
    constraints="- `1 <= n <= 5 * 10^4`\n- `0 <= edges.length <= 10^5`",
    hints=["Union-find: start with n groups and merge on every edge that joins two different groups."],
    editorial="Disjoint-set union with path compression (and union by size): every successful union reduces the component count by one. BFS/DFS from each unvisited node gives the same answer.",
    spec=spec("countGroups", [("n", "int"), ("edges", "int[][]")], "int"),
    reference="""
class Solution:
    def countGroups(self, n, edges):
        parent = list(range(n))
        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x
        groups = n
        for u, v in edges:
            ru, rv = find(u), find(v)
            if ru != rv:
                parent[ru] = rv
                groups -= 1
        return groups
""",
    samples=[((5, [[0, 1], [1, 2], [3, 4]]), None), ((4, []), "Four isolated nodes.")],
    hidden=[(1, []), (50000, _random_edges(50000, 60000)), (50000, [[i, i + 1] for i in range(49999)]), (50000, _random_edges(50000, 100000))],
)

problem(
    number=114, topic="Graphs", slug="cheapest-network", title="Cheapest Network (MST)", difficulty=H,
    tags=["graph", "minimum-spanning-tree", "union-find"], complexity="O(edges log edges) time",
    statement=(
        "Cities `0..n-1` can be linked by the candidate cables `[u, v, cost]`. Return the minimum total cost of cables that connect "
        "all cities, or −1 if they cannot all be connected."
    ),
    constraints="- `1 <= n <= 5 * 10^4`\n- `0 <= edges.length <= 10^5`\n- `0 <= cost <= 10^5`",
    hints=["Kruskal: take cables in increasing cost, skipping any that would close a cycle."],
    editorial="Kruskal's algorithm: sort the edges by cost and add each one whose endpoints are in different union-find sets. The result spans everything iff exactly n − 1 edges were taken. Prim's algorithm with a heap is equivalent. Totals fit in 64-bit (and well within 2^31 here).",
    spec=spec("networkCost", [("n", "int"), ("edges", "int[][]")], "long"),
    reference="""
class Solution:
    def networkCost(self, n, edges):
        parent = list(range(n))
        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x
        total, used = 0, 0
        for u, v, w in sorted(edges, key=lambda e: e[2]):
            ru, rv = find(u), find(v)
            if ru != rv:
                parent[ru] = rv
                total += w
                used += 1
        return total if used == n - 1 else -1
""",
    samples=[((4, [[0, 1, 1], [1, 2, 4], [0, 2, 3], [2, 3, 2]]), "1 + 3 + 2 = 6."), ((3, [[0, 1, 5]]), "City 2 cannot be reached."), ((1, []), None)],
    hidden=[(50000, _weighted(_random_edges(50000, 100000, connected=True), 0, 10**5)),
            (50000, _weighted(_random_edges(50000, 75000), 0, 10**5)), (2000, _weighted(_random_edges(2000, 60000, connected=True), 0, 10))],
    time_limit_ms=3000,
)

# ================================================================ Bit Manipulation

problem(
    number=115, topic="Bit Manipulation", slug="count-one-bits", title="Count the One Bits", difficulty=E,
    tags=["bit-manipulation", "dynamic-programming"], complexity="O(n) time",
    statement="Return an array `bits` of length `n + 1` where `bits[i]` is the number of 1s in the binary representation of `i`.",
    constraints="- `0 <= n <= 10^5`",
    hints=["bits[i] = bits[i >> 1] + (i & 1)."],
    editorial="Dropping the lowest bit of i gives i >> 1, which is smaller and already computed, so bits[i] = bits[i >> 1] + (i & 1). Alternatively bits[i] = bits[i & (i − 1)] + 1, since i & (i − 1) clears the lowest set bit.",
    spec=spec("countOneBits", [("n", "int")], "int[]"),
    reference="""
class Solution:
    def countOneBits(self, n):
        bits = [0] * (n + 1)
        for i in range(1, n + 1):
            bits[i] = bits[i >> 1] + (i & 1)
        return bits
""",
    samples=[((2,), "0 → 0, 1 → 1, 10 → 1."), ((5,), None)],
    hidden=[(0,), (1,), (100000,)],
)

problem(
    number=116, topic="Bit Manipulation", slug="lone-value", title="The Lone Value", difficulty=E,
    tags=["bit-manipulation", "xor"], complexity="O(n) time, O(1) space",
    statement="Every value in `nums` appears exactly twice except one, which appears once. Return that value using O(1) extra space.",
    constraints="- `1 <= nums.length <= 3 * 10^4` (odd)\n- `-3 * 10^4 <= nums[i] <= 3 * 10^4`",
    hints=["x XOR x = 0 and x XOR 0 = x."],
    editorial="XOR all values together: pairs cancel out (x ^ x = 0) and XOR is order-independent, so the result is the lone value. O(n) time, O(1) space.",
    spec=spec("loneValue", [("nums", "int[]")], "int"),
    reference="""
class Solution:
    def loneValue(self, nums):
        result = 0
        for x in nums:
            result ^= x
        return result
""",
    samples=[(([2, 2, 1],), None), (([4, 1, 2, 1, 2],), None), (([-7],), None)],
    hidden=[(lambda vals: rng.sample(vals[:-1] * 2 + [vals[-1]], 2 * len(vals) - 1))(rng.sample(range(-30000, 30001), 15000)),
            ([0, 5, 5],)],
)
