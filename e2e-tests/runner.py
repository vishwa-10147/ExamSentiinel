#!/usr/bin/env python3
"""
ExamSentinel Unified E2E Test Runner.
Executes opaque-box test suites across Tiers 1 through 4 with structured CLI reporting.

Usage:
    python e2e-tests/runner.py [--tier 1|2|all] [--verbose] [--json-report report.json]
"""
import sys
import os
import unittest
import argparse
import time
import json
import datetime
from typing import List, Dict, Any

# Ensure e2e-tests directory is in sys.path
TESTS_DIR = os.path.abspath(os.path.dirname(__file__))
if TESTS_DIR not in sys.path:
    sys.path.insert(0, TESTS_DIR)


class Color:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    BOLD = "\033[1m"
    RESET = "\033[0m"


def format_header(title: str) -> str:
    line = "=" * 70
    return f"\n{Color.BOLD}{Color.BLUE}{line}\n  {title}\n{line}{Color.RESET}\n"


class CustomTestResult(unittest.TestResult):
    def __init__(self, stream=sys.stdout, descriptions=True, verbosity=1):
        super().__init__(stream, descriptions, verbosity)
        self.stream = stream
        self.verbosity = verbosity
        self.test_records: List[Dict[str, Any]] = []
        self._start_time = 0.0

    def startTest(self, test):
        super().startTest(test)
        self._start_time = time.time()
        if self.verbosity > 1:
            self.stream.write(f"  RUNNING: {test.id()} ... ")
            self.stream.flush()

    def addSuccess(self, test):
        super().addSuccess(test)
        duration = time.time() - self._start_time
        self.test_records.append({
            "test_id": test.id(),
            "status": "PASS",
            "duration": round(duration, 4),
            "message": None
        })
        if self.verbosity > 1:
            self.stream.write(f"{Color.GREEN}PASS{Color.RESET} ({duration:.3f}s)\n")
        elif self.verbosity == 1:
            self.stream.write(f"{Color.GREEN}.{Color.RESET}")
            self.stream.flush()

    def addFailure(self, test, err):
        super().addFailure(test, err)
        duration = time.time() - self._start_time
        err_msg = self._exc_info_to_string(err, test)
        self.test_records.append({
            "test_id": test.id(),
            "status": "FAIL",
            "duration": round(duration, 4),
            "message": err_msg
        })
        if self.verbosity > 1:
            self.stream.write(f"{Color.RED}FAIL{Color.RESET}\n")
        elif self.verbosity == 1:
            self.stream.write(f"{Color.RED}F{Color.RESET}")
            self.stream.flush()

    def addError(self, test, err):
        super().addError(test, err)
        duration = time.time() - self._start_time
        err_msg = self._exc_info_to_string(err, test)
        self.test_records.append({
            "test_id": test.id(),
            "status": "ERROR",
            "duration": round(duration, 4),
            "message": err_msg
        })
        if self.verbosity > 1:
            self.stream.write(f"{Color.YELLOW}ERROR{Color.RESET}\n")
        elif self.verbosity == 1:
            self.stream.write(f"{Color.YELLOW}E{Color.RESET}")
            self.stream.flush()

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        self.test_records.append({
            "test_id": test.id(),
            "status": "SKIP",
            "duration": 0.0,
            "message": reason
        })
        if self.verbosity > 1:
            self.stream.write(f"{Color.YELLOW}SKIP ({reason}){Color.RESET}\n")
        elif self.verbosity == 1:
            self.stream.write(f"{Color.YELLOW}s{Color.RESET}")
            self.stream.flush()


def discover_suite(tier: str) -> unittest.TestSuite:
    """Discovers test suites based on requested tier."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    tier1_dir = os.path.join(TESTS_DIR, "tier1_feature_coverage")
    tier2_dir = os.path.join(TESTS_DIR, "tier2_boundary_corner")

    if tier in ("1", "all"):
        if os.path.isdir(tier1_dir):
            suite.addTests(loader.discover(start_dir=tier1_dir, pattern="test_*.py", top_level_dir=TESTS_DIR))

    if tier in ("2", "all"):
        if os.path.isdir(tier2_dir):
            suite.addTests(loader.discover(start_dir=tier2_dir, pattern="test_*.py", top_level_dir=TESTS_DIR))

    return suite


def run_e2e_tests(tier: str = "all", verbosity: int = 1, json_report: str = None) -> int:
    """Executes the test suite and returns exit code."""
    print(format_header("ExamSentinel Opaque-Box E2E Test Suite"))
    print(f"  Configuration:")
    print(f"  - Target Tier: {tier.upper()}")
    print(f"  - Test Directory: {TESTS_DIR}")
    print(f"  - Timestamp: {datetime.datetime.utcnow().isoformat()}Z\n")

    suite = discover_suite(tier)
    test_count = suite.countTestCases()
    if test_count == 0:
        print(f"{Color.YELLOW}Warning: No test cases discovered for tier {tier}.{Color.RESET}")
        return 0

    print(f"Discovered {test_count} test cases. Running tests...\n")
    start_time = time.time()
    result = CustomTestResult(verbosity=verbosity)
    suite.run(result)
    total_time = time.time() - start_time

    # Print summary
    print("\n" + format_header("Test Execution Summary"))
    passed = len([t for t in result.test_records if t["status"] == "PASS"])
    failed = len(result.failures)
    errors = len(result.errors)
    skipped = len(result.skipped)

    print(f"  Total Tests Run: {result.testsRun}")
    print(f"  {Color.GREEN}Passed:          {passed}{Color.RESET}")
    if failed > 0:
        print(f"  {Color.RED}Failed:          {failed}{Color.RESET}")
    else:
        print(f"  Failed:          0")
    if errors > 0:
        print(f"  {Color.YELLOW}Errors:          {errors}{Color.RESET}")
    else:
        print(f"  Errors:          0")
    print(f"  Skipped:         {skipped}")
    print(f"  Elapsed Time:    {total_time:.3f} seconds\n")

    # Print detailed failures if any
    if failed > 0 or errors > 0:
        print(f"{Color.BOLD}{Color.RED}Failures & Errors Details:{Color.RESET}\n")
        for failure in result.failures:
            test, traceback_str = failure
            print(f"{Color.RED}[FAIL]{Color.RESET} {test.id()}:\n{traceback_str}\n")
        for error in result.errors:
            test, traceback_str = error
            print(f"{Color.YELLOW}[ERROR]{Color.RESET} {test.id()}:\n{traceback_str}\n")

    # Generate JSON report if requested
    if json_report:
        report_data = {
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "tier": tier,
            "total_tests": result.testsRun,
            "passed": passed,
            "failed": failed,
            "errors": errors,
            "skipped": skipped,
            "duration_seconds": round(total_time, 4),
            "tests": result.test_records
        }
        with open(json_report, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2)
        print(f"JSON execution report saved to: {os.path.abspath(json_report)}")

    if failed == 0 and errors == 0:
        print(f"\n{Color.BOLD}{Color.GREEN}SUCCESS: All {passed} tests passed successfully!{Color.RESET}\n")
        return 0
    else:
        print(f"\n{Color.BOLD}{Color.RED}FAILURE: {failed + errors} test(s) failed or encountered errors.{Color.RESET}\n")
        return 1


def main():
    parser = argparse.ArgumentParser(description="ExamSentinel E2E Test Runner")
    parser.add_argument("--tier", choices=["1", "2", "3", "4", "all"], default="all", help="Test tier to execute")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output displaying individual test names")
    parser.add_argument("--json-report", help="Save test execution results to JSON file")

    args = parser.parse_args()
    verbosity = 2 if args.verbose else 1
    exit_code = run_e2e_tests(tier=args.tier, verbosity=verbosity, json_report=args.json_report)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
