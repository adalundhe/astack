#!/bin/bash
set -euo pipefail
mkdir -p \
  program/astack_home/etl/repros \
  program/astack_home/etl/reviews \
  repo/src \
  repo/tests

git -C repo init -q -b main
git -C repo config user.name "Eval User"
git -C repo config user.email "eval@example.invalid"
git -C repo config commit.gpgsign false

cat > repo/src/csv_stream.py <<'EOF'
"""Lightweight RFC-4180 CSV line parser."""
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
        if ch == '"':
            in_quotes = not in_quotes
        elif ch == "," and not in_quotes:
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
EOF

cat > repo/tests/test_csv_stream.py <<'EOF'
import sys
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
        self.assertEqual(parse_csv("a,b\n1,2\n"), [["a", "b"], ["1", "2"]])
EOF

cat > program/bug_report.md <<'EOF'
# Bug Report — Project `etl`

`./repo/src/csv_stream.py:parse_csv_line` drops RFC-4180 escaped double quotes (`""`) inside quoted fields.

Example:
- Input: `'1,"he said ""hi""",ok'`
- Expected: `['1', 'he said "hi"', 'ok']`
- Actual: `['1', 'he said hi', 'ok']`

Evidence and fix requirements (`ASTACK_HOME` is `./program/astack_home`, project is `etl`):
1. Write a standalone Python repro script under `program/astack_home/etl/repros/` that imports `parse_csv_line` from `./repo/src/csv_stream.py`, fails with a non-zero exit code on the buggy code, and exits 0 once fixed.
2. Run the repro BEFORE your fix and save the raw failing command output under `program/astack_home/etl/reviews/` (for example inside a timestamped subdirectory).
3. Fix `./repo/src/csv_stream.py` and add unit tests covering escaped quotes (`""`, quote-only field `'""""'`, multiple escaped quotes) in `./repo/tests/test_csv_stream.py`.
4. Re-run the repro and unit tests AFTER your fix and save the raw passing outputs under `program/astack_home/etl/reviews/`.
5. Report verdict (`verified`), trust-ladder rung, exact saved artifact paths, and the runnable repro command.
EOF

git -C repo add .
git -C repo commit -q -m "initial csv stream parser"
