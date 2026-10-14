# DSA question bank

ExamSentinel ships **116 data-structures-and-algorithms problems** (#1–#116) across 16
topics, plus **11 SQL problems** (#201–#211). Every statement is original to ExamSentinel.
Every problem has a reference solution that is executed to produce its test data, and every
reference passes its own tests on the real execution engine
(`backend/tests/test_sandbox_engine.py::test_reference_solution_passes_on_the_engine`).

## Where the bank lives

```
backend/practice_bank/
├── common.py           # TOPICS, problem() registry, shared seeded RNG, spec() helper
├── core.py             # original problems (numbers come from metadata.py)
├── algorithms.py       #   "
├── sql.py              # SQL problems (#201–#211)
├── dsa_basics.py       # #47–#64   Arrays, Strings, Hashing, Two Pointers, Sliding Window
├── dsa_search_lists.py # #65–#81   Binary Search, Sorting & Searching, Linked Lists
├── dsa_structures.py   # #82–#103  Stacks & Queues, Recursion & Backtracking, Trees & BST, Heaps
├── dsa_advanced.py     # #104–#116 Greedy, Dynamic Programming, Graphs, Bit Manipulation
├── metadata.py         # number/topic/complexity/editorial for core, algorithms and sql
└── __init__.py         # imports modules in a FIXED order, then applies metadata
```

Hidden inputs are generated from one seeded RNG (`common.rng`), so **module import order and
the order of problems inside a module must not change** — that would change the hidden
data of every later problem. Append new problems at the end of the last module (or a new
module imported last).

## What every problem has

| Field | Notes |
|---|---|
| `number` | permanent public ID — never renumber or reuse |
| `slug`, `title` | slug is the URL and the seeder's upsert key |
| `topic`, `tags`, `difficulty` | one primary topic from `common.TOPICS`; free-form tags |
| `statement`, `constraints` | Markdown |
| `input_format`, `output_format` | generated from the function signature when omitted (FUNCTION mode) |
| `samples` | 2–3 visible cases, optionally with explanations |
| `hidden` | ≥ 2 hidden cases, usually including edge cases and a maximum-size case |
| `reference` | Python (SQL for SQL problems); executed to compute every expected output |
| `starter_code` | generated per language from the function spec (FUNCTION); explicit for STDIO |
| `complexity`, `editorial`, `hints` | editorial is shown only after the student solves it |
| `compare` | `exact`, `unordered`, `float` or `checker` (with a `checker` function) |

`backend/tests/test_practice_bank.py` enforces all of this (≥ 100 DSA problems, topic
minimums, unique IDs/slugs, stable anchor IDs, required fields, sample/hidden counts,
harness generation in every language, checker behaviour, seeding idempotency).

## Seeding

```bash
cd backend
python seed_practice.py
```

The seeder upserts by slug, so it is **idempotent and never changes IDs**: re-running
updates statements and test data in place and keeps each problem's database id and
`number`. Expected outputs are computed by running the reference through the same Python
harness the judge uses. Seeding all 127 problems takes about 30 s.

## Problem formats

**FUNCTION** — implement a method on `class Solution`; tests are JSON values, one per
parameter. Linked lists are JSON arrays (`[1,2,3]`), binary trees are level-order arrays
with `null` for missing children (`[3,9,20,null,null,15,7]`). For cycle problems an
`internal` `pos` parameter wires the tail to node `pos` before calling the method.

**STDIO** — a full program reads stdin and writes stdout (#10, #82, #83).

**SQL** — a single SELECT over tables created from the shown schema; each test inserts its
own rows.

**Checker** — when many answers are valid (#111 *Order the Tasks* accepts any topological
order), a Python `check(args, output, expected)` decides. Checkers come only from this
repository; the admin API cannot create or modify them.

## Adding a problem

1. Append a `problem(...)` call to the last module (or create `dsa_<name>.py` and import it
   last in `__init__.py`). Use the next free `number`.
2. Write an original statement, constraints, 2–3 samples (with explanations), hidden cases
   covering edge cases and the maximum size, a clear Python reference, complexity, hints and
   an editorial.
3. Keep total test data under ~6 MB per problem (one request carries all cases).
4. Run `python -m pytest tests/test_practice_bank.py` and, with Piston running,
   `python -m pytest tests/test_sandbox_engine.py -k <slug>`.
5. Run `python seed_practice.py`.

Problems can also be authored in the UI (**Admin → Practice Problems**), with a
**Validate** button that runs the reference against every test on the engine.

### Can problems be imported from websites or other repositories?

Only with a compatible license. LeetCode/HackerRank/Codeforces statements and tests are
copyrighted and their terms forbid copying them. Openly licensed sources exist
(e.g. Exercism's problem specifications under MIT, many textbook exercises under CC
licenses); they need attribution and must be adapted to the bank's format and re-validated.

## Difficulty

Difficulty is set by the author (Easy / Medium / Hard). Once a problem has 20+ submissions,
the admin problem list shows a **suggested difficulty** from the real acceptance rate
(≥ 60 % Easy, ≥ 35 % Medium, otherwise Hard). Students can filter by difficulty and topic and
sort by ID, difficulty, acceptance or title.

## Coverage

| Topic | Problems | Easy | Medium | Hard |
|---|---|---|---|---|
| Arrays | 12 | 6 | 6 | 0 |
| Strings | 10 | 7 | 2 | 1 |
| Hashing | 8 | 5 | 3 | 0 |
| Two Pointers | 6 | 3 | 2 | 1 |
| Sliding Window | 6 | 1 | 3 | 2 |
| Binary Search | 7 | 2 | 3 | 2 |
| Sorting & Searching | 7 | 2 | 4 | 1 |
| Linked Lists | 8 | 4 | 3 | 1 |
| Stacks & Queues | 8 | 2 | 4 | 2 |
| Recursion & Backtracking | 8 | 1 | 5 | 2 |
| Trees & BST | 8 | 3 | 4 | 1 |
| Heaps | 4 | 1 | 2 | 1 |
| Greedy | 4 | 1 | 3 | 0 |
| Dynamic Programming | 8 | 1 | 6 | 1 |
| Graphs | 8 | 0 | 7 | 1 |
| Bit Manipulation | 4 | 4 | 0 | 0 |
| SQL | 11 | 4 | 5 | 2 |
| **DSA total** | **116** | 43 | 57 | 16 |

## Problem index

| # | Title | Slug | Topic | Difficulty | Judge |
|---|---|---|---|---|---|
| 1 | Pair With Target Sum | `pair-with-target-sum` | Hashing | Easy | FUNCTION · unordered |
| 2 | Balanced Brackets | `balanced-brackets` | Stacks & Queues | Easy | FUNCTION |
| 3 | Reverse Word Order | `reverse-word-order` | Strings | Easy | FUNCTION |
| 4 | Search a Sorted List | `sorted-search` | Binary Search | Easy | FUNCTION |
| 5 | Merge Two Sorted Lists | `merge-two-sorted-lists` | Two Pointers | Easy | FUNCTION |
| 6 | Alphanumeric Palindrome | `alphanumeric-palindrome` | Strings | Easy | FUNCTION |
| 7 | Stair Climber | `stair-climber` | Dynamic Programming | Easy | FUNCTION |
| 8 | Single Trade Profit | `single-trade-profit` | Arrays | Easy | FUNCTION |
| 9 | Fizz Buzz Words | `fizz-buzz-words` | Arrays | Easy | FUNCTION |
| 10 | Sum of Numbers (stdin) | `sum-of-numbers-stdin` | Arrays | Easy | STDIO |
| 11 | Best Contiguous Sum | `best-contiguous-sum` | Arrays | Medium | FUNCTION |
| 12 | Longest Run Without Repeats | `longest-unique-run` | Sliding Window | Medium | FUNCTION |
| 13 | Products Except Self | `products-except-self` | Arrays | Medium | FUNCTION |
| 14 | Count the Islands | `count-islands` | Graphs | Medium | FUNCTION |
| 15 | Fewest Coins | `fewest-coins` | Dynamic Programming | Medium | FUNCTION |
| 16 | K Most Frequent Values | `k-most-frequent` | Heaps | Medium | FUNCTION · unordered |
| 17 | Merge Overlapping Ranges | `merge-overlapping-ranges` | Sorting & Searching | Medium | FUNCTION |
| 18 | Longest Rising Subsequence | `longest-rising-subsequence` | Dynamic Programming | Medium | FUNCTION |
| 19 | Anagram Groups | `anagram-groups` | Hashing | Medium | FUNCTION |
| 20 | Rainwater Capacity | `rainwater-capacity` | Two Pointers | Hard | FUNCTION |
| 21 | Minimum Edit Steps | `minimum-edit-steps` | Dynamic Programming | Hard | FUNCTION |
| 22 | Median of Two Sorted Arrays | `median-of-two-sorted` | Binary Search | Hard | FUNCTION · float |
| 23 | Has a Repeated Value | `has-repeated-value` | Hashing | Easy | FUNCTION |
| 24 | Missing Ticket Number | `missing-ticket-number` | Bit Manipulation | Easy | FUNCTION |
| 25 | Zeros to the Back | `zeros-to-the-back` | Two Pointers | Easy | FUNCTION |
| 26 | Majority Value | `majority-value` | Arrays | Easy | FUNCTION |
| 27 | Same Letters | `same-letters` | Strings | Easy | FUNCTION |
| 28 | First Unique Letter | `first-unique-letter` | Strings | Easy | FUNCTION |
| 29 | Power of Two? | `power-of-two-check` | Bit Manipulation | Easy | FUNCTION |
| 30 | Roman Numeral Value | `roman-numeral-value` | Strings | Easy | FUNCTION |
| 31 | Running Totals | `running-totals` | Arrays | Easy | FUNCTION |
| 32 | Common Values | `common-values` | Hashing | Easy | FUNCTION |
| 33 | Rotate Right | `rotate-right` | Arrays | Medium | FUNCTION |
| 34 | Zero-Sum Triplets | `zero-sum-triplets` | Two Pointers | Medium | FUNCTION |
| 35 | Search a Rotated List | `search-rotated-list` | Binary Search | Medium | FUNCTION |
| 36 | Spiral Walk | `spiral-walk` | Arrays | Medium | FUNCTION |
| 37 | Days Until Warmer | `days-until-warmer` | Stacks & Queues | Medium | FUNCTION |
| 38 | Rooms Needed | `rooms-needed` | Sorting & Searching | Medium | FUNCTION |
| 39 | Word Segmentation | `word-segmentation` | Dynamic Programming | Medium | FUNCTION |
| 40 | Non-Adjacent Max Sum | `non-adjacent-max-sum` | Dynamic Programming | Medium | FUNCTION |
| 41 | Grid Path Count | `grid-path-count` | Dynamic Programming | Medium | FUNCTION |
| 42 | Can Finish All Courses? | `prerequisite-order` | Graphs | Medium | FUNCTION |
| 43 | Largest Banner | `largest-banner` | Stacks & Queues | Hard | FUNCTION |
| 44 | Window Maximums | `window-maximums` | Sliding Window | Hard | FUNCTION |
| 45 | Peaceful Queens | `peaceful-queens` | Recursion & Backtracking | Hard | FUNCTION |
| 46 | Longest Balanced Run | `longest-balanced-run` | Stacks & Queues | Hard | FUNCTION |
| 47 | Second Largest Distinct Value | `second-largest-distinct` | Arrays | Easy | FUNCTION |
| 48 | Next Arrangement | `next-arrangement` | Arrays | Medium | FUNCTION |
| 49 | Rotate a Square Grid | `rotate-square-grid` | Arrays | Medium | FUNCTION |
| 50 | Longest Shared Prefix | `longest-shared-prefix` | Strings | Easy | FUNCTION |
| 51 | Run-Length Compress | `run-length-compress` | Strings | Easy | FUNCTION |
| 52 | Longest Palindromic Substring Length | `longest-palindrome-length` | Strings | Medium | FUNCTION |
| 53 | Parse an Integer | `parse-integer` | Strings | Medium | FUNCTION |
| 54 | Fewest Letters to Make a Palindrome | `shortest-palindrome-prefix` | Strings | Hard | FUNCTION |
| 55 | Same-Shape Strings | `same-shape-strings` | Hashing | Easy | FUNCTION |
| 56 | Subarrays With a Given Sum | `subarrays-with-sum` | Hashing | Medium | FUNCTION |
| 57 | Longest Consecutive Run | `longest-consecutive-run` | Hashing | Medium | FUNCTION |
| 58 | Follows the Pattern | `follows-pattern` | Hashing | Easy | FUNCTION |
| 59 | Squares of a Sorted List | `sorted-squares` | Two Pointers | Easy | FUNCTION |
| 60 | Widest Water Container | `widest-water-container` | Two Pointers | Medium | FUNCTION |
| 61 | Best Window Sum | `best-window-sum` | Sliding Window | Easy | FUNCTION |
| 62 | Longest Ones After Flips | `ones-after-flips` | Sliding Window | Medium | FUNCTION |
| 63 | Anagram Positions | `anagram-positions` | Sliding Window | Medium | FUNCTION |
| 64 | Smallest Covering Window | `smallest-covering-window` | Sliding Window | Hard | FUNCTION |
| 65 | Insert Position | `insert-position` | Binary Search | Easy | FUNCTION |
| 66 | First and Last Index | `first-and-last-index` | Binary Search | Medium | FUNCTION |
| 67 | Minimum of a Rotated List | `minimum-of-rotated` | Binary Search | Medium | FUNCTION |
| 68 | Split Into K Parts | `split-into-k-parts` | Binary Search | Hard | FUNCTION |
| 69 | Three-Color Sort | `three-color-sort` | Sorting & Searching | Easy | FUNCTION |
| 70 | K-th Smallest Value | `kth-smallest-value` | Sorting & Searching | Medium | FUNCTION |
| 71 | Largest Concatenation | `largest-concatenation` | Sorting & Searching | Medium | FUNCTION |
| 72 | Count Inversions | `count-inversions` | Sorting & Searching | Hard | FUNCTION |
| 73 | Sort by a Custom Order | `custom-order-sort` | Sorting & Searching | Easy | FUNCTION |
| 74 | Reverse a Linked List | `reverse-linked-list` | Linked Lists | Easy | FUNCTION |
| 75 | Detect a Cycle | `detect-list-cycle` | Linked Lists | Easy | FUNCTION |
| 76 | Merge Two Sorted Linked Lists | `merge-sorted-linked-lists` | Linked Lists | Easy | FUNCTION |
| 77 | Middle Node | `middle-node` | Linked Lists | Easy | FUNCTION |
| 78 | Remove the K-th Node From the End | `remove-kth-from-end` | Linked Lists | Medium | FUNCTION |
| 79 | Add Two Digit Lists | `add-digit-lists` | Linked Lists | Medium | FUNCTION |
| 80 | Length of the Cycle | `cycle-length` | Linked Lists | Medium | FUNCTION |
| 81 | Reverse in Groups of K | `reverse-in-groups` | Linked Lists | Hard | FUNCTION |
| 82 | Queue From Two Stacks | `queue-from-two-stacks` | Stacks & Queues | Medium | STDIO |
| 83 | Stack With Minimum | `min-stack` | Stacks & Queues | Medium | STDIO |
| 84 | Evaluate a Postfix Expression | `evaluate-postfix` | Stacks & Queues | Medium | FUNCTION |
| 85 | Remove Adjacent Equal Pairs | `remove-adjacent-pairs` | Stacks & Queues | Easy | FUNCTION |
| 86 | All Subsets | `all-subsets` | Recursion & Backtracking | Medium | FUNCTION · unordered |
| 87 | All Orderings | `all-orderings` | Recursion & Backtracking | Medium | FUNCTION · unordered |
| 88 | Combinations That Sum to a Target | `sum-combinations` | Recursion & Backtracking | Medium | FUNCTION · unordered |
| 89 | All Balanced Parentheses Strings | `balanced-parentheses-strings` | Recursion & Backtracking | Medium | FUNCTION · unordered |
| 90 | Word in a Letter Grid | `word-in-grid` | Recursion & Backtracking | Medium | FUNCTION |
| 91 | Fast Modular Power | `fast-power-mod` | Recursion & Backtracking | Easy | FUNCTION |
| 92 | Queens Boards | `queens-boards` | Recursion & Backtracking | Hard | FUNCTION · unordered |
| 93 | Depth of a Binary Tree | `tree-depth` | Trees & BST | Easy | FUNCTION |
| 94 | In-Order Traversal | `inorder-traversal` | Trees & BST | Easy | FUNCTION |
| 95 | Mirror a Binary Tree | `mirror-tree` | Trees & BST | Easy | FUNCTION |
| 96 | Level-Order Traversal | `level-order` | Trees & BST | Medium | FUNCTION |
| 97 | Valid Binary Search Tree | `valid-search-tree` | Trees & BST | Medium | FUNCTION |
| 98 | Lowest Common Ancestor | `lowest-common-ancestor` | Trees & BST | Medium | FUNCTION |
| 99 | K-th Smallest in a BST | `kth-smallest-in-bst` | Trees & BST | Medium | FUNCTION |
| 100 | Maximum Path Sum | `max-path-sum` | Trees & BST | Hard | FUNCTION |
| 101 | Smash the Stones | `smash-stones` | Heaps | Easy | FUNCTION |
| 102 | K Nearest Points | `nearest-points` | Heaps | Medium | FUNCTION · unordered |
| 103 | Running Medians | `running-medians` | Heaps | Hard | FUNCTION · float |
| 104 | Reach the Last Square | `reach-the-end` | Greedy | Medium | FUNCTION |
| 105 | Fuel Loop Starting Point | `fuel-loop` | Greedy | Medium | FUNCTION |
| 106 | Hand Out Snacks | `hand-out-snacks` | Greedy | Easy | FUNCTION |
| 107 | Fewest Removals for No Overlap | `fewest-removals-no-overlap` | Greedy | Medium | FUNCTION |
| 108 | Pack the Bag (0/1 Knapsack) | `pack-the-bag` | Dynamic Programming | Medium | FUNCTION |
| 109 | Fewest Hops Between Two Nodes | `fewest-hops` | Graphs | Medium | FUNCTION |
| 110 | Cheapest Routes From a Source | `cheapest-routes` | Graphs | Medium | FUNCTION |
| 111 | Order the Tasks | `task-ordering` | Graphs | Medium | FUNCTION · checker |
| 112 | Split Into Two Teams | `two-team-split` | Graphs | Medium | FUNCTION |
| 113 | Count Connected Groups | `count-groups` | Graphs | Medium | FUNCTION |
| 114 | Cheapest Network (MST) | `cheapest-network` | Graphs | Hard | FUNCTION |
| 115 | Count the One Bits | `count-one-bits` | Bit Manipulation | Easy | FUNCTION |
| 116 | The Lone Value | `lone-value` | Bit Manipulation | Easy | FUNCTION |
| 201 | High Earners (SQL) | `sql-high-earners` | SQL | Easy | SQL |
| 202 | Customers Without Orders (SQL) | `sql-customers-without-orders` | SQL | Easy | SQL · unordered |
| 203 | Department Headcount (SQL) | `sql-department-headcount` | SQL | Easy | SQL |
| 204 | Total Spent per Customer (SQL) | `sql-total-spent` | SQL | Easy | SQL |
| 205 | Second Highest Salary (SQL) | `sql-second-highest-salary` | SQL | Medium | SQL |
| 206 | Top Earner per Department (SQL) | `sql-department-top-earners` | SQL | Medium | SQL · unordered |
| 207 | Earns More Than Their Manager (SQL) | `sql-earns-more-than-manager` | SQL | Medium | SQL · unordered |
| 208 | Monthly Revenue (SQL) | `sql-monthly-revenue` | SQL | Medium | SQL |
| 209 | Shared Email Addresses (SQL) | `sql-shared-emails` | SQL | Medium | SQL · unordered |
| 210 | Top Three Salaries per Department (SQL) | `sql-top-three-salaries` | SQL | Hard | SQL |
| 211 | Three-Day Login Streaks (SQL) | `sql-login-streaks` | SQL | Hard | SQL · unordered |
