"""The DSA question bank: size, topic coverage, required fields, stable IDs and seeding.

These tests run without a code-execution engine. Expected outputs are computed by
running each reference through the judge's Python harness (as the seeder does), so
reference/test-data agreement is checked here too; tests/test_sandbox_engine.py
re-checks every reference on the real engine.
"""

import collections
import json

import pytest
from sqlalchemy import func, select

from app.models.practice import JudgeMode, PracticeProblem, PracticeTestCase
from app.services.practice_judge import SUPPORTED_LANGUAGES, build_harness, describe_function_io, starter_code, validate_function_spec
from practice_bank import EXTRA_TOPICS, PROBLEMS, TOPICS

DSA = [p for p in PROBLEMS if p["topic"] in TOPICS]

# Minimum number of problems per topic.
TOPIC_MINIMUMS = {
    "Arrays": 10, "Strings": 8, "Hashing": 6, "Two Pointers": 5, "Sliding Window": 5, "Binary Search": 6,
    "Sorting & Searching": 6, "Linked Lists": 6, "Stacks & Queues": 6, "Recursion & Backtracking": 6,
    "Trees & BST": 8, "Heaps": 4, "Greedy": 4, "Dynamic Programming": 6, "Graphs": 6, "Bit Manipulation": 3,
}

# Public IDs are permanent. A few anchors from each batch catch accidental renumbering.
STABLE_IDS = {
    1: "pair-with-target-sum", 46: "longest-balanced-run", 47: "second-largest-distinct", 74: "reverse-linked-list",
    82: "queue-from-two-stacks", 100: "max-path-sum", 111: "task-ordering", 116: "lone-value", 201: "sql-high-earners",
}


def test_bank_has_at_least_100_dsa_problems():
    assert len(DSA) >= 100
    assert len(PROBLEMS) == len(DSA) + sum(1 for p in PROBLEMS if p["topic"] in EXTRA_TOPICS)


def test_numbers_and_slugs_are_unique_and_stable():
    numbers = [p["number"] for p in PROBLEMS]
    slugs = [p["slug"] for p in PROBLEMS]
    assert len(set(numbers)) == len(numbers), [n for n, c in collections.Counter(numbers).items() if c > 1]
    assert len(set(slugs)) == len(slugs), [s for s, c in collections.Counter(slugs).items() if c > 1]
    by_number = {p["number"]: p["slug"] for p in PROBLEMS}
    for number, slug in STABLE_IDS.items():
        assert by_number.get(number) == slug, f"#{number} must stay {slug}"
    assert sorted(p["number"] for p in DSA) == list(range(1, len(DSA) + 1)), "DSA IDs are contiguous from 1"


def test_every_topic_meets_its_minimum():
    counts = collections.Counter(p["topic"] for p in DSA)
    assert set(counts) == set(TOPICS)
    short = {t: (counts[t], m) for t, m in TOPIC_MINIMUMS.items() if counts[t] < m}
    assert not short, f"topics below minimum (have, need): {short}"


def test_every_difficulty_is_represented_in_most_topics():
    by_topic = collections.defaultdict(set)
    for p in DSA:
        by_topic[p["topic"]].add(p["difficulty"].value)
    assert sum(1 for levels in by_topic.values() if len(levels) >= 2) >= 12


@pytest.mark.parametrize("p", PROBLEMS, ids=lambda p: f"{p['number']}-{p['slug']}")
def test_problem_has_required_fields(p):
    for key in ("number", "slug", "title", "difficulty", "topic", "tags", "statement", "constraints", "complexity", "editorial", "reference"):
        assert p.get(key), f"{p['slug']} is missing {key}"
    assert len(p["statement"]) >= 40
    assert p.get("hints") or p["topic"] == "SQL", f"{p['slug']} has no hints"
    mode = p.get("judge_mode", JudgeMode.FUNCTION)
    if mode == JudgeMode.FUNCTION:
        validate_function_spec(p["spec"])
        assert 2 <= len(p["samples"]) <= 3, "2-3 visible samples"
        assert len(p["hidden"]) >= 2, "at least two hidden tests"
    elif mode == JudgeMode.STDIO:
        assert p.get("input_format") and p.get("output_format")
        assert 2 <= len(p["stdio_samples"]) <= 3 and len(p["stdio_hidden"]) >= 2
        assert set(p["starter_code"]) >= {"python", "javascript", "java", "cpp", "c"}
    else:
        assert p.get("sql_schema") and len(p["sql_samples"]) >= 1 and len(p["sql_hidden"]) >= 2
    if p.get("compare") == "checker":
        assert "def check(" in p["checker"]
    else:
        assert not p.get("checker"), "a checker is only used with compare='checker'"


@pytest.mark.parametrize("p", [p for p in PROBLEMS if p.get("spec")], ids=lambda p: p["slug"])
def test_function_problems_generate_starters_and_harnesses_in_every_language(p):
    input_format, output_format = describe_function_io(p["spec"], p.get("compare", "exact"))
    assert p["spec"]["name"] in input_format and output_format
    for language in SUPPORTED_LANGUAGES:
        code = starter_code(p["spec"], language)
        assert p["spec"]["name"] in code
        assert p["spec"]["name"] in build_harness(code, p["spec"], language)


def test_checker_accepts_any_valid_answer_and_rejects_invalid_ones():
    from app.services.practice_judge import run_checker
    from types import SimpleNamespace

    topo = next(p for p in PROBLEMS if p["slug"] == "task-ordering")
    problem = SimpleNamespace(checker=topo["checker"], slug=topo["slug"])
    case = "4\n[[1,0],[2,0],[3,1],[3,2]]"
    assert run_checker(problem, case, [3, 1, 2, 0], None)
    assert run_checker(problem, case, [3, 2, 1, 0], None)  # a different valid order
    assert not run_checker(problem, case, [0, 1, 2, 3], None)  # violates dependencies
    assert not run_checker(problem, case, [3, 1, 2], None)  # missing a task
    assert not run_checker(problem, case, "3120", None)  # wrong type is a wrong answer, not a crash


# ---------------------------------------------------------------------------
# Seeding (expected outputs come from executing the references)
# ---------------------------------------------------------------------------

async def test_seed_is_idempotent_and_never_changes_ids(monkeypatch):
    import seed_practice
    from tests.conftest import test_async_session_maker, test_engine

    sample = [p for p in PROBLEMS if p["number"] in (1, 74, 82, 98, 111, 201)]
    monkeypatch.setattr(seed_practice, "PROBLEMS", sample)
    monkeypatch.setattr(seed_practice, "async_session_maker", test_async_session_maker)
    monkeypatch.setattr(seed_practice, "engine", test_engine)

    await seed_practice.seed()
    async with test_async_session_maker() as db:
        first = {p.slug: (p.id, p.number) for p in (await db.execute(select(PracticeProblem))).scalars()}
        cases_first = (await db.execute(select(func.count(PracticeTestCase.id)))).scalar_one()

    await seed_practice.seed()
    async with test_async_session_maker() as db:
        rows = (await db.execute(select(PracticeProblem))).scalars().all()
        second = {p.slug: (p.id, p.number) for p in rows}
        cases_second = (await db.execute(select(func.count(PracticeTestCase.id)))).scalar_one()
        topo = next(p for p in rows if p.slug == "task-ordering")
        lists = next(p for p in rows if p.slug == "reverse-linked-list")

    assert first == second and len(first) == len(sample)
    assert cases_first == cases_second
    assert topo.compare_mode == "checker" and "def check(" in topo.checker
    assert lists.topic == "Linked Lists" and lists.editorial and lists.complexity
    assert "linked list" in lists.input_format.lower()


def test_function_reference_outputs_are_computed_not_hand_written():
    from seed_practice import build_cases

    p = next(p for p in PROBLEMS if p["slug"] == "reverse-linked-list")
    cases = build_cases(p)
    sample = next(c for c in cases if c.is_sample)
    assert json.loads(sample.expected_output) == list(reversed(json.loads(sample.input_data.splitlines()[0])))
