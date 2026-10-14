"""Shared helpers for the practice problem bank.

Problems register themselves by calling ``problem(...)``. Hidden test data is
generated from one seeded RNG, so modules must be imported in a fixed order
(see ``practice_bank/__init__.py``) to keep test data stable across seeds.
"""

import random
from typing import Any

from app.models.practice import JudgeMode, ProblemDifficulty  # noqa: F401  (re-exported)

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
