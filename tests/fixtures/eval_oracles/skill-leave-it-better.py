"""Separated offline oracle for `skill-leave-it-better`."""
from __future__ import annotations

import subprocess
from pathlib import Path


def apply(ws: Path) -> dict[str, object]:
    """Fix preexisting src/tax.py bug in commit 1, then implement format_cents + tests in commit 2."""
    repo = ws / "repo"

    # Commit 1: isolated fix for preexisting tax basis-points bug
    (repo / "src" / "tax.py").write_text(
        '"""Sales tax calculation helpers."""\n'
        "from __future__ import annotations\n\n\n"
        "def compute_tax_cents(subtotal_cents: int, rate_bps: int) -> int:\n"
        '    """Compute tax in cents from subtotal_cents and rate in basis points (100 bps = 1%).\n\n'
        "    Rounds half up to the nearest cent.\n"
        '    """\n'
        "    if subtotal_cents < 0 or rate_bps < 0:\n"
        '        raise ValueError("subtotal_cents and rate_bps must be non-negative")\n'
        "    return (subtotal_cents * rate_bps + 5000) // 10000\n",
        encoding="utf-8",
    )
    subprocess.run(["git", "-C", str(repo), "add", "src/tax.py"], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(repo),
            "commit",
            "-q",
            "-m",
            "fix(tax): divide basis points by 10000 for preexisting test_tax failure",
        ],
        check=True,
    )

    # Commit 2: requested format_cents feature + tests
    (repo / "src" / "money.py").write_text(
        '"""Currency parsing and formatting helpers."""\n'
        "from __future__ import annotations\n\n\n"
        "def parse_dollars_to_cents(amount: str) -> int:\n"
        '    """Parse a non-negative dollar string such as \'12.34\' into integer cents."""\n'
        '    dollars_str, _, cents_str = amount.strip().partition(".")\n'
        '    cents_str = (cents_str + "00")[:2]\n'
        "    return int(dollars_str) * 100 + int(cents_str)\n\n\n"
        "def format_cents(cents: int) -> str:\n"
        '    """Format integer cents as a US dollar string."""\n'
        "    if isinstance(cents, bool) or not isinstance(cents, int):\n"
        '        raise TypeError("cents must be an int")\n'
        '    sign = "-" if cents < 0 else ""\n'
        "    dollars, rem = divmod(abs(cents), 100)\n"
        '    return f"{sign}${dollars}.{rem:02d}"\n',
        encoding="utf-8",
    )
    (repo / "tests" / "test_money.py").write_text(
        "import sys\n"
        "import unittest\n"
        "from pathlib import Path\n\n"
        'sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))\n'
        "from money import format_cents, parse_dollars_to_cents\n\n\n"
        "class MoneyTest(unittest.TestCase):\n"
        "    def test_parse_dollars_to_cents(self):\n"
        '        self.assertEqual(parse_dollars_to_cents("12.34"), 1234)\n'
        '        self.assertEqual(parse_dollars_to_cents("0.05"), 5)\n\n'
        "    def test_format_cents(self):\n"
        '        self.assertEqual(format_cents(0), "$0.00")\n'
        '        self.assertEqual(format_cents(5), "$0.05")\n'
        '        self.assertEqual(format_cents(1234), "$12.34")\n'
        '        self.assertEqual(format_cents(-250), "-$2.50")\n'
        '        self.assertEqual(format_cents(100000), "$1000.00")\n\n'
        "    def test_format_cents_rejects_bool_and_non_int(self):\n"
        "        with self.assertRaises(TypeError):\n"
        "            format_cents(True)\n"
        "        with self.assertRaises(TypeError):\n"
        '            format_cents("12.34")\n',
        encoding="utf-8",
    )
    subprocess.run(["git", "-C", str(repo), "add", "src/money.py", "tests/test_money.py"], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(repo),
            "commit",
            "-q",
            "-m",
            "feat(money): implement format_cents with unit tests",
        ],
        check=True,
    )
    return {
        "final_text": (
            "Fixed the preexisting basis-points divisor bug in `src/tax.py` (1000 -> 10000) in an isolated commit, "
            "then implemented `format_cents` and unit tests in `src/money.py` / `tests/test_money.py` in a separate commit. "
            "The full unittest suite passes."
        ),
    }
