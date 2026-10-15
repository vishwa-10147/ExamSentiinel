"""Practice topics in learning order. Every DSA problem belongs to exactly one.

Kept apart from ``practice_bank`` on purpose: importing that package builds the whole problem
bank (about 6 s of CPU), which must never happen inside an API request.
"""

TOPICS = [
    "Arrays", "Strings", "Hashing", "Two Pointers", "Sliding Window", "Binary Search",
    "Sorting & Searching", "Linked Lists", "Stacks & Queues", "Recursion & Backtracking",
    "Trees & BST", "Heaps", "Greedy", "Dynamic Programming", "Graphs", "Bit Manipulation",
]
EXTRA_TOPICS = ["SQL"]  # practice beyond the DSA syllabus
