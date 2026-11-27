#!/usr/bin/env bash
set -euo pipefail

mkdir -p program/astack_home/reports repo/src repo/tests

cat > program/LANES.md <<'EOF'
# Integration Brief & Lanes — `reports`

Project name: `reports`
Workspace durable home: `program/astack_home/reports/`

## Active Feature Branches in `./repo`

1. **`lane/parser`** (branched from `main`, 4 noisy WIP commits; includes a fix committed by `Alice <alice@example.invalid>`):
   - Touches: `src/parser.py`, `tests/test_parser.py`
   - Needs commit consolidation down to 1–2 reviewable commits while preserving exact tree contents and Alice's authorship attribution.
2. **`lane/formatter`** (branched from `main`, 2 clean commits):
   - Touches: `src/formatter.py`, `tests/test_formatter.py`
   - Disjoint from `lane/parser`.
3. **Final integration on `main`:**
   - Touches: `src/pipeline.py`, `tests/test_pipeline.py`
   - Depends on both `lane/parser` and `lane/formatter`; wires `parse_rows` and `format_table` inside `src/pipeline.py:build_report`.

## Deliverables

1. Write `program/DAG.md` containing a fenced Mermaid `flowchart` and per-task sections (`Description`, `Implementation guide`, `Acceptance criteria`, `Tests`, `Touches`) showing disjoint parallel ownership before the final integration task.
2. Consolidate `lane/parser` cleanly (1–2 commits, identical tree, preserving `Alice <alice@example.invalid>` attribution).
3. Integrate both `lane/parser` and `lane/formatter` onto `main`, wire `src/pipeline.py` + `tests/test_pipeline.py`, and ensure `main` is checked out with a clean working tree and passing unit tests.
4. Record a focused active lesson under `program/astack_home/reports/lessons/<lesson_name>/LESSON.md` (never inside `./repo`).
EOF

cat > repo/src/__init__.py <<'EOF'
"""reports generation package."""
EOF

cat > repo/src/models.py <<'EOF'
"""Shared report data structures."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ReportRow:
    service: str
    status: str
    latency_ms: int
EOF

cat > repo/src/pipeline.py <<'EOF'
"""Report pipeline entrypoint (to be wired after parser and formatter land)."""
from __future__ import annotations


def build_report(raw_csv: str) -> str:
    """Parse raw CSV rows and render a markdown summary table."""
    raise NotImplementedError("wire parser and formatter once both feature lanes land")
EOF

cat > repo/tests/test_models.py <<'EOF'
"""Unit tests for shared report models."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from models import ReportRow


class ModelTests(unittest.TestCase):
    def test_report_row_fields(self) -> None:
        row = ReportRow(service="api", status="ok", latency_ms=42)
        self.assertEqual(row.service, "api")
        self.assertEqual(row.status, "ok")
        self.assertEqual(row.latency_ms, 42)


if __name__ == "__main__":
    unittest.main()
EOF

git -C repo init -q -b main
git -C repo config user.name "Dev"
git -C repo config user.email "dev@example.invalid"
git -C repo add .
git -C repo commit -q -m "chore: initial reports skeleton on main"
git -C repo rev-parse HEAD > program/base_sha.txt

# --- Branch 1: lane/parser (4 noisy WIP commits including Alice's commit) ---
git -C repo checkout -q -b lane/parser

cat > repo/src/parser.py <<'EOF'
"""CSV row parser for reports."""
from __future__ import annotations

from models import ReportRow


def parse_rows(raw_csv: str) -> list[ReportRow]:
    rows: list[ReportRow] = []
    for line in raw_csv.splitlines():
        if not line.strip():
            continue
        parts = line.split(",")
        rows.append(ReportRow(parts[0], parts[1], int(parts[2])))
    return rows
EOF
git -C repo add src/parser.py
git -C repo commit -q -m "wip: rough parser sketch"

cat > repo/src/parser.py <<'EOF'
"""CSV row parser for reports."""
from __future__ import annotations

import csv
import io

from models import ReportRow


def parse_rows(raw_csv: str) -> list[ReportRow]:
    """Parse CSV text with optional header into typed ReportRow records."""
    rows: list[ReportRow] = []
    reader = csv.reader(io.StringIO(raw_csv))
    for idx, fields in enumerate(reader):
        if not fields or all(not cell.strip() for cell in fields):
            continue
        if idx == 0 and fields[0].strip().lower() == "service":
            continue
        if len(fields) < 3:
            raise ValueError(f"row {idx + 1} expected 3 columns, got {len(fields)}")
        rows.append(
            ReportRow(
                service=fields[0].strip(),
                status=fields[1].strip(),
                latency_ms=int(fields[2].strip()),
            )
        )
    return rows
EOF
git -C repo add src/parser.py
GIT_AUTHOR_NAME="Alice" GIT_AUTHOR_EMAIL="alice@example.invalid" \
    git -C repo commit -q -m "fix: handle quoted CSV cells, blank lines, and optional header"

cat > repo/src/parser.py <<'EOF'
"""CSV row parser for reports."""
from __future__ import annotations

import csv
import io

from models import ReportRow


def parse_rows(raw_csv: str) -> list[ReportRow]:
    """Parse CSV text with optional header into typed ReportRow records."""
    rows: list[ReportRow] = []
    reader = csv.reader(io.StringIO(raw_csv))
    for idx, fields in enumerate(reader):
        if not fields or all(not cell.strip() for cell in fields):
            continue
        if idx == 0 and fields[0].strip().lower() == "service":
            continue
        if len(fields) < 3:
            raise ValueError(f"row {idx + 1} expected 3 columns, got {len(fields)}")
        service = fields[0].strip()
        status = fields[1].strip()
        latency_ms = int(fields[2].strip())
        if latency_ms < 0:
            raise ValueError(f"row {idx + 1} latency_ms must be non-negative")
        rows.append(ReportRow(service=service, status=status, latency_ms=latency_ms))
    return rows
EOF
git -C repo add src/parser.py
git -C repo commit -q -m "fixup: reject negative latency"

cat > repo/tests/test_parser.py <<'EOF'
"""Unit tests for reports CSV parser."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from models import ReportRow
from parser import parse_rows


class ParserTests(unittest.TestCase):
    def test_parses_header_quoted_cells_and_blank_lines(self) -> None:
        raw = 'service,status,latency_ms\n"pay,core",ok,120\n\nedge,degraded,340\n'
        rows = parse_rows(raw)
        self.assertEqual(
            rows,
            [
                ReportRow(service="pay,core", status="ok", latency_ms=120),
                ReportRow(service="edge", status="degraded", latency_ms=340),
            ],
        )

    def test_rejects_negative_latency(self) -> None:
        with self.assertRaises(ValueError):
            parse_rows("api,ok,-5\n")


if __name__ == "__main__":
    unittest.main()
EOF
git -C repo add tests/test_parser.py
git -C repo commit -q -m "wip: add parser tests"
git -C repo rev-parse 'lane/parser^{tree}' > program/parser_pre_squish_tree.txt

# --- Branch 2: lane/formatter (2 clean commits on disjoint files) ---
git -C repo checkout -q main
git -C repo checkout -q -b lane/formatter

cat > repo/src/formatter.py <<'EOF'
"""Markdown table formatter for report rows."""
from __future__ import annotations

from models import ReportRow


def _escape_cell(text: str) -> str:
    return text.replace("|", "\\|")


def format_table(rows: list[ReportRow]) -> str:
    """Render ReportRow records as a GitHub-flavored markdown table."""
    lines = [
        "| Service | Status | Latency (ms) |",
        "| --- | --- | ---: |",
    ]
    for row in rows:
        lines.append(
            f"| {_escape_cell(row.service)} | {_escape_cell(row.status)} | {row.latency_ms} |"
        )
    return "\n".join(lines) + "\n"
EOF
git -C repo add src/formatter.py
git -C repo commit -q -m "feat: add markdown table formatter with pipe escaping"

cat > repo/tests/test_formatter.py <<'EOF'
"""Unit tests for markdown table formatter."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from formatter import format_table
from models import ReportRow


class FormatterTests(unittest.TestCase):
    def test_formats_rows_and_escapes_pipes(self) -> None:
        out = format_table([
            ReportRow(service="edge|gw", status="ok", latency_ms=55),
            ReportRow(service="pay", status="warn", latency_ms=210),
        ])
        self.assertIn("| Service | Status | Latency (ms) |", out)
        self.assertIn("| edge\\|gw | ok | 55 |", out)
        self.assertIn("| pay | warn | 210 |", out)


if __name__ == "__main__":
    unittest.main()
EOF
git -C repo add tests/test_formatter.py
git -C repo commit -q -m "test: add formatter unit tests"
git -C repo rev-parse HEAD > program/formatter_sha.txt

# Return to main
git -C repo checkout -q main
