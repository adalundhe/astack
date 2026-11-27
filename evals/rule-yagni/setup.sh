#!/bin/bash
set -euo pipefail
mkdir -p program repo/src repo/tests

git -C repo init -q -b main
git -C repo config user.name "Eval"
git -C repo config user.email "eval@example.invalid"
git -C repo config commit.gpgsign false

cat > repo/src/__init__.py <<'EOF'
EOF

cat > repo/src/parser.py <<'EOF'
"""CSV record parsing utilities with leftover v1 shims and dead flags."""
from __future__ import annotations

import csv
import io
import os

ENABLE_LEGACY_MODE = os.environ.get("ENABLE_LEGACY_MODE", "").lower() in ("1", "true", "yes")


def parse_v1(raw: str) -> list[dict[str, str]]:
    """Deprecated naive comma-splitting parser."""
    lines = [ln for ln in raw.strip().splitlines() if ln.strip()]
    if not lines:
        return []
    headers = [h.strip() for h in lines[0].split(",")]
    rows: list[dict[str, str]] = []
    for line in lines[1:]:
        parts = [p.strip() for p in line.split(",")]
        rows.append(dict(zip(headers, parts)))
    return rows


def parse_csv(raw: str, legacy_compat: bool = False) -> list[dict[str, str]]:
    """Canonical RFC-4180 CSV parser."""
    if legacy_compat or ENABLE_LEGACY_MODE:
        return parse_v1(raw)
    text = raw.strip()
    if not text:
        return []
    return list(csv.DictReader(io.StringIO(text)))


parse_records = parse_v1
EOF

cat > repo/src/importer.py <<'EOF'
"""Contact importer still coupled to legacy parser shim and dead flag."""
from __future__ import annotations

import parser as record_parser


def load_records(raw: str) -> list[dict[str, str]]:
    if record_parser.ENABLE_LEGACY_MODE:
        return record_parser.parse_v1(raw)
    return record_parser.parse_csv(raw)


def import_contacts(raw: str) -> list[tuple[str, str]]:
    rows = record_parser.parse_v1(raw)
    return [(row["name"], row["region"]) for row in rows]
EOF

cat > repo/src/report.py <<'EOF'
"""Regional sales report still using deprecated parse_records alias."""
from __future__ import annotations

from collections import defaultdict
from parser import parse_records


def summarize_by_region(raw: str) -> dict[str, int]:
    totals: dict[str, int] = defaultdict(int)
    for row in parse_records(raw):
        totals[row["region"]] += int(row["amount"])
    return dict(sorted(totals.items()))
EOF

cat > repo/tests/__init__.py <<'EOF'
EOF

cat > repo/tests/test_pipeline.py <<'EOF'
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import importer
import parser as record_parser
import report


class LegacyPipelineBaselineTest(unittest.TestCase):
    def test_parse_v1_basic(self):
        rows = record_parser.parse_v1("name,region,amount\nAlice,west,100\n")
        self.assertEqual(rows, [{"name": "Alice", "region": "west", "amount": "100"}])

    def test_importer_legacy_mode(self):
        prev = record_parser.ENABLE_LEGACY_MODE
        record_parser.ENABLE_LEGACY_MODE = True
        try:
            rows = importer.load_records("name,region,amount\nAlice,west,100\n")
            self.assertEqual(rows, [{"name": "Alice", "region": "west", "amount": "100"}])
        finally:
            record_parser.ENABLE_LEGACY_MODE = prev

    def test_report_summary(self):
        totals = report.summarize_by_region("name,region,amount\nAlice,west,100\nBob,west,50\n")
        self.assertEqual(totals, {"west": 150})


if __name__ == "__main__":
    unittest.main()
EOF

git -C repo add .
git -C repo commit -q -m "initial pipeline with legacy parse_v1 shim and dead flag"
git -C repo rev-parse HEAD > program/base_sha.txt
