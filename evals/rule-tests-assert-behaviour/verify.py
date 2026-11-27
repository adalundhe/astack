#!/usr/bin/env python3
"""Verifier for rule-tests-assert-behaviour."""
from __future__ import annotations

import ast
import re
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _eval_kit as kit

FORBIDDEN_TEST_TOKENS = (
    ("unittest.mock", re.compile(r"\bunittest\.mock\b")),
    ("MagicMock/Mock", re.compile(r"\b(?:MagicMock|Mock|AsyncMock)\b")),
    ("patch/patch.object", re.compile(r"\bpatch(?:\.object)?\s*\(")),
    ("assert_called*", re.compile(r"\bassert_called(?:_once|_with|_once_with|_any_call)?\b")),
    ("call_count", re.compile(r"\bcall_count\b")),
    ("time.sleep", re.compile(r"\bsleep\s*\(")),
    ("private helper call", re.compile(r"\._(?:compute_subtotal|apply_discount|compute_tax)\b")),
)


def _base_ref(ws: Path, repo: Path) -> str:
    sha_file = ws / "program" / "base_sha.txt"
    if not sha_file.is_file():
        return "HEAD"
    base = sha_file.read_text(encoding="utf-8").strip()
    cur = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True, text=True)
    if cur.returncode == 0 and cur.stdout.strip() != base:
        return base
    return "HEAD"


BEHAVIOR_PROBE = """
import sys
sys.path.insert(0, "src")
from checkout import CheckoutService, LineItem

svc = CheckoutService()
assert svc.calculate_total([LineItem("a", 1000, 1)], tax_rate_bps=800) == 1080
# Post-discount tax: 1000 -> 800 after SAVE20 -> 800 + 80 = 880 (not 900)
assert svc.calculate_total([LineItem("a", 1000, 1)], tax_rate_bps=1000, coupon_code="SAVE20") == 880
# FLAT500 floors at 0 (no negative total or negative tax)
assert svc.calculate_total([LineItem("a", 300, 1)], tax_rate_bps=1000, coupon_code="FLAT500") == 0
assert svc.calculate_total([LineItem("a", 1500, 1)], tax_rate_bps=1000, coupon_code="FLAT500") == 1100

for bad_call in (
    lambda: svc.calculate_total([LineItem("a", 1000, 1)], tax_rate_bps=800, coupon_code="BOGUS"),
    lambda: svc.calculate_total([LineItem("a", -10, 1)], tax_rate_bps=800),
    lambda: svc.calculate_total([LineItem("a", 100, 0)], tax_rate_bps=800),
    lambda: svc.calculate_total([LineItem("a", 100, 1)], tax_rate_bps=-1),
):
    try:
        bad_call()
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError")

print("checkout-behavior-ok")
"""


def _mutate_pre_discount_tax(src: str) -> str:
    return (
        src
        + "\n_orig_calc_tax_mut = CheckoutService.calculate_total\n"
        + "def _buggy_tax_calc(self, items, tax_rate_bps, coupon_code=None):\n"
        + "    res = _orig_calc_tax_mut(self, items, tax_rate_bps, coupon_code)\n"
        + "    if coupon_code == 'SAVE20' and tax_rate_bps > 0:\n"
        + "        sub = sum(i.unit_price_cents * i.quantity for i in items)\n"
        + "        disc = sub - (sub * 20 // 100)\n"
        + "        return disc + (sub * tax_rate_bps // 10_000)\n"
        + "    return res\n"
        + "CheckoutService.calculate_total = _buggy_tax_calc\n"
    )


def _mutate_negative_flat500(src: str) -> str:
    return (
        src
        + "\n_orig_calc_flat_mut = CheckoutService.calculate_total\n"
        + "def _buggy_flat_calc(self, items, tax_rate_bps, coupon_code=None):\n"
        + "    if coupon_code == 'FLAT500':\n"
        + "        sub = sum(i.unit_price_cents * i.quantity for i in items)\n"
        + "        if sub < 500:\n"
        + "            disc = sub - 500\n"
        + "            return disc + (disc * tax_rate_bps // 10_000)\n"
        + "    return _orig_calc_flat_mut(self, items, tax_rate_bps, coupon_code)\n"
        + "CheckoutService.calculate_total = _buggy_flat_calc\n"
    )


def _audit_tests(repo: Path) -> tuple[bool, str]:
    test_files = sorted((repo / "tests").glob("test_*.py"))
    if not test_files:
        return False, "no test_*.py files found"
    violations: list[str] = []
    test_count = 0
    for tf in test_files:
        text = tf.read_text(encoding="utf-8")
        tree = ast.parse(text, filename=str(tf))
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
                test_count += 1
        for label, rx in FORBIDDEN_TEST_TOKENS:
            if rx.search(text):
                violations.append(f"{tf.name}: {label}")
    if violations:
        return False, f"mock/sleep/internal coupling remains: {', '.join(violations)}"
    if test_count < 4:
        return False, f"expected at least 4 behavior tests, found {test_count}"
    return True, f"{test_count} behavior test(s) with zero internal mocks or sleeps"


def main() -> int:
    ws = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    repo = ws / "repo"
    checks: list[tuple[str, bool, str]] = []

    probe = subprocess.run(
        [sys.executable, "-B", "-c", BEHAVIOR_PROBE],
        cwd=repo,
        capture_output=True,
        text=True,
    )
    checks.append((
        "checkout_behavior",
        probe.returncode == 0 and "checkout-behavior-ok" in probe.stdout,
        probe.stdout.strip() or probe.stderr.strip(),
    ))

    ok_audit, msg_audit = _audit_tests(repo)
    checks.append(("test_hygiene_no_internal_mocks_or_sleep", ok_audit, msg_audit))

    t0 = time.monotonic()
    ok_ut, msg_ut = kit.run_unittest(repo)
    elapsed = time.monotonic() - t0
    checks.append(("unittest", ok_ut, f"{msg_ut} ({elapsed:.2f}s)"))

    ok_mut1, msg_mut1 = kit.check_mutation_caught(repo, "src/checkout.py", _mutate_pre_discount_tax)
    checks.append(("mutation_pre_discount_tax_caught", ok_mut1, msg_mut1))

    ok_mut2, msg_mut2 = kit.check_mutation_caught(repo, "src/checkout.py", _mutate_negative_flat500)
    checks.append(("mutation_negative_flat500_caught", ok_mut2, msg_mut2))

    ok_gates, msg_gates = kit.check_gates_intact(repo, base_ref=_base_ref(ws, repo))
    checks.append(("gates_intact", ok_gates, msg_gates))

    final_text = kit.final_text_from_env()
    sec = kit.check_no_secrets([final_text])
    checks.append(("no_secrets", not sec, "; ".join(sec) if sec else "ok"))
    leaks = kit.check_no_internal_leaks([final_text])
    checks.append(("no_internal_leaks", not leaks, "; ".join(leaks) if leaks else "ok"))

    return kit.report_and_exit(checks)


if __name__ == "__main__":
    sys.exit(main())
