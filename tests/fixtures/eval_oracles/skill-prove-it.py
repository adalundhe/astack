"""Separated offline oracle for `skill-prove-it`."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

_REPRO_SCRIPT = '''#!/usr/bin/env python3
"""Standalone deterministic repro for escaped CSV quotes in repo/src/csv_stream.py."""
from __future__ import annotations

import sys
from pathlib import Path

WS = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(WS / "repo" / "src"))
from csv_stream import parse_csv_line


def main() -> int:
    cases = [
        ('1,"he said ""hi""",ok', ["1", 'he said "hi"', "ok"]),
        ('""""', ['"']),
        ('"a""b""c",d', ['a"b"c', "d"]),
    ]
    failed = False
    for raw, expected in cases:
        got = parse_csv_line(raw)
        print(f"INPUT={raw!r} GOT={got!r} EXPECTED={expected!r}")
        if got != expected:
            failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
'''

_FIXED_CSV_STREAM = '''"""Lightweight RFC-4180 CSV line parser."""
from __future__ import annotations


def parse_csv_line(line: str) -> list[str]:
    """Parse one CSV record, preserving commas and escaped double quotes inside quoted fields."""
    fields: list[str] = []
    buf: list[str] = []
    in_quotes = False
    i = 0
    n = len(line)
    while i < n:
        ch = line[i]
        if in_quotes:
            if ch == '"':
                if i + 1 < n and line[i + 1] == '"':
                    buf.append('"')
                    i += 2
                    continue
                in_quotes = False
            else:
                buf.append(ch)
        else:
            if ch == '"':
                in_quotes = True
            elif ch == ",":
                fields.append("".join(buf))
                buf = []
            else:
                buf.append(ch)
        i += 1
    fields.append("".join(buf))
    return fields


def parse_csv(text: str) -> list[list[str]]:
    """Parse newline-delimited CSV text into a list of field lists."""
    return [parse_csv_line(row) for row in text.splitlines() if row != ""]
'''

_UPDATED_TEST_CSV = '''import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from csv_stream import parse_csv, parse_csv_line


class CsvStreamTest(unittest.TestCase):
    def test_plain_fields(self):
        self.assertEqual(parse_csv_line("id,name,city"), ["id", "name", "city"])

    def test_quoted_field_with_comma(self):
        self.assertEqual(parse_csv_line('1,"Ada, Lovelace",London'), ["1", "Ada, Lovelace", "London"])

    def test_multi_line_csv(self):
        self.assertEqual(parse_csv("a,b\\n1,2\\n"), [["a", "b"], ["1", "2"]])

    def test_escaped_double_quotes_inside_quoted_field(self):
        self.assertEqual(
            parse_csv_line('1,"he said ""hi""",ok'),
            ["1", 'he said "hi"', "ok"],
        )
        self.assertEqual(parse_csv_line('""""'), ['"'])
        self.assertEqual(parse_csv_line('"a""b""c","x, ""y""",z'), ['a"b"c', 'x, "y"', "z"])
        self.assertEqual(parse_csv_line('a,"",b'), ["a", "", "b"])
'''


def apply(ws: Path) -> dict[str, object]:
    """Save repro, capture raw before/after proofs under astack_home/etl, fix csv_stream.py + tests."""
    astack_home = ws / "program" / "astack_home"
    repro_path = astack_home / "etl" / "repros" / "repro_escaped_quotes.py"
    review_dir = astack_home / "etl" / "reviews" / "2026-11-26T09-00-00Z"
    repro_path.parent.mkdir(parents=True, exist_ok=True)
    review_dir.mkdir(parents=True, exist_ok=True)

    repro_path.write_text(_REPRO_SCRIPT, encoding="utf-8")

    before_proc = subprocess.run(
        [sys.executable, "-B", str(repro_path)],
        cwd=ws,
        capture_output=True,
        text=True,
    )
    assert before_proc.returncode != 0, "expected repro to fail before fix"
    (review_dir / "before_repro.txt").write_text(
        f"$ python3 -B program/astack_home/etl/repros/repro_escaped_quotes.py\n"
        f"exit_code={before_proc.returncode}\n"
        f"{before_proc.stdout}{before_proc.stderr}",
        encoding="utf-8",
    )

    (ws / "repo" / "src" / "csv_stream.py").write_text(_FIXED_CSV_STREAM, encoding="utf-8")
    (ws / "repo" / "tests" / "test_csv_stream.py").write_text(_UPDATED_TEST_CSV, encoding="utf-8")

    after_proc = subprocess.run(
        [sys.executable, "-B", str(repro_path)],
        cwd=ws,
        capture_output=True,
        text=True,
        check=True,
    )
    ut_proc = subprocess.run(
        [sys.executable, "-B", "-m", "unittest", "discover", "-s", "tests", "-v"],
        cwd=ws / "repo",
        capture_output=True,
        text=True,
        check=True,
    )
    (review_dir / "after_proof.txt").write_text(
        f"$ python3 -B program/astack_home/etl/repros/repro_escaped_quotes.py\n"
        f"exit_code={after_proc.returncode}\n"
        f"{after_proc.stdout}{after_proc.stderr}\n"
        f"$ python3 -B -m unittest discover -s tests -v\n"
        f"exit_code={ut_proc.returncode}\n"
        f"{ut_proc.stdout}{ut_proc.stderr}",
        encoding="utf-8",
    )
    return {
        "final_text": (
            "Verdict: verified (trust-ladder rung 5: real artifact executed before and after fix).\n"
            "Fixed escaped double-quote handling in `./repo/src/csv_stream.py` and added unit tests in "
            "`./repo/tests/test_csv_stream.py`.\n"
            "Artifacts:\n"
            "- Repro: `program/astack_home/etl/repros/repro_escaped_quotes.py`\n"
            "- Before output: `program/astack_home/etl/reviews/2026-11-26T09-00-00Z/before_repro.txt`\n"
            "- After output: `program/astack_home/etl/reviews/2026-11-26T09-00-00Z/after_proof.txt`\n"
            "Proof command: `python3 -B program/astack_home/etl/repros/repro_escaped_quotes.py`"
        ),
    }
