"""Separated offline oracle for `skill-fix-it`."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

_FIXED_TAX_SRC = '''"""Sales tax calculation helpers."""
from __future__ import annotations


def calculate_tax_cents(subtotal_cents: int, rate_bps: int) -> int:
    """Compute sales tax in integer cents from basis points (100 bps = 1%).

    Half-cent remainders (e.g. 0.5 cents, 72.5 cents) MUST round half up to the next cent.
    """
    if subtotal_cents < 0 or rate_bps < 0:
        raise ValueError("subtotal_cents and rate_bps must be non-negative")
    return (subtotal_cents * rate_bps + 5000) // 10000
'''

_UPDATED_TEST_TAX = '''import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from tax import calculate_tax_cents


class TaxTest(unittest.TestCase):
    def test_whole_cent_tax(self):
        self.assertEqual(calculate_tax_cents(10000, 800), 800)
        self.assertEqual(calculate_tax_cents(0, 725), 0)

    def test_rounds_down_below_half(self):
        self.assertEqual(calculate_tax_cents(100, 725), 7)

    def test_rounds_half_up_on_half_cent_boundaries(self):
        self.assertEqual(calculate_tax_cents(100, 50), 1)
        self.assertEqual(calculate_tax_cents(1000, 725), 73)
        self.assertEqual(calculate_tax_cents(200, 125), 3)

    def test_rejects_negative_inputs(self):
        with self.assertRaises(ValueError):
            calculate_tax_cents(-1, 500)
        with self.assertRaises(ValueError):
            calculate_tax_cents(100, -1)
'''


def apply(ws: Path) -> dict[str, object]:
    """Add red-first regression test and minimally fix repo/src/tax.py without touching auth or billing."""
    repo = ws / "repo"
    (repo / "tests" / "test_tax.py").write_text(_UPDATED_TEST_TAX, encoding="utf-8")

    red_proc = subprocess.run(
        [sys.executable, "-B", "-m", "unittest", "discover", "-s", "tests"],
        cwd=repo,
        capture_output=True,
        text=True,
    )
    assert red_proc.returncode != 0, "expected new half-up test to fail before fix"

    (repo / "src" / "tax.py").write_text(_FIXED_TAX_SRC, encoding="utf-8")
    subprocess.run(
        [sys.executable, "-B", "-m", "unittest", "discover", "-s", "tests"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )
    return {
        "final_text": (
            "Added red-first regression tests in `./repo/tests/test_tax.py` (confirmed failing on half-cent "
            "boundaries), then replaced float `round(...)` in `./repo/src/tax.py` with exact integer half-up "
            "arithmetic `(subtotal_cents * rate_bps + 5000) // 10000`. Left `./repo/src/auth.py` and "
            "`./repo/src/billing.py` untouched. All unit tests pass."
        ),
    }
