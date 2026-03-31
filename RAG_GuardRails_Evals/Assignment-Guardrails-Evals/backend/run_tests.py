#!/usr/bin/env python3
"""
run_tests.py - Simple test runner (no pytest required)
Runs all unit tests for RBAC, guardrails, and routing.
"""
import sys
import traceback
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

PASS = "\033[92m✓ PASS\033[0m"
FAIL = "\033[91m✗ FAIL\033[0m"
SKIP = "\033[93m~ SKIP\033[0m"


def run_test(test_fn):
    """Run a single test function, return (passed, error_msg)."""
    try:
        test_fn()
        return True, None
    except AssertionError as e:
        return False, f"AssertionError: {e}"
    except Exception as e:
        return False, f"{type(e).__name__}: {e}\n{traceback.format_exc()}"


def run_class(cls):
    """Run all test_ methods in a class."""
    results = []
    instance = cls()
    for name in dir(cls):
        if name.startswith("test_"):
            fn = getattr(instance, name)
            passed, err = run_test(fn)
            results.append((name, passed, err))
    return results


def print_results(class_name, results):
    passed = sum(1 for _, p, _ in results if p)
    print(f"\n  [{class_name}]")
    for name, p, err in results:
        status = PASS if p else FAIL
        print(f"    {status} {name}")
        if err:
            print(f"         {err[:200]}")
    print(f"    → {passed}/{len(results)} passed")
    return passed, len(results)


def main():
    total_passed = 0
    total_tests = 0
    all_suites = []

    # ── Guardrail Tests ─────────────────────────────────────────────
    print("\n" + "="*60)
    print("GUARDRAIL TESTS")
    print("="*60)
    try:
        from tests.test_guardrails import TestInputGuardrails, TestOutputGuardrails
        for cls in [TestInputGuardrails, TestOutputGuardrails]:
            results = run_class(cls)
            p, t = print_results(cls.__name__, results)
            total_passed += p; total_tests += t
    except Exception as e:
        print(f"  ERROR importing guardrail tests: {e}")

    # ── Routing Tests ─────────────────────────────────────────────────
    print("\n" + "="*60)
    print("ROUTING TESTS")
    print("="*60)
    try:
        from tests.test_routing import TestSemanticRouter
        results = run_class(TestSemanticRouter)
        p, t = print_results(TestSemanticRouter.__name__, results)
        total_passed += p; total_tests += t
    except Exception as e:
        print(f"  ERROR importing routing tests: {e}")

    # ── RBAC Tests ───────────────────────────────────────────────────
    print("\n" + "="*60)
    print("RBAC TESTS")
    print("="*60)
    try:
        from tests.test_rbac import TestRBACBoundaries
        results = run_class(TestRBACBoundaries)
        p, t = print_results(TestRBACBoundaries.__name__, results)
        total_passed += p; total_tests += t
    except Exception as e:
        print(f"  ERROR importing RBAC tests: {e}")

    # ── Summary ──────────────────────────────────────────────────────
    print("\n" + "="*60)
    print(f"TOTAL: {total_passed}/{total_tests} tests passed")
    print("="*60)

    # Exit non-zero if any failures
    if total_passed < total_tests:
        sys.exit(1)


if __name__ == "__main__":
    main()

