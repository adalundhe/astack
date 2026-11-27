#!/usr/bin/env bash
set -euo pipefail

mkdir -p program/astack_home repo/src repo/tests

git -C repo init -q -b main
git -C repo config user.name "Eval"
git -C repo config user.email "eval@example.invalid"
git -C repo config commit.gpgsign false

cat > repo/README.md <<'EOF'
# pipe-walk

Three-stage event aggregation pipeline: `src/ingest.py` -> `src/transform.py` -> `src/sink.py`.
EOF

cat > repo/src/ingest.py <<'EOF'
"""Stage 1: parse raw JSONL request lines into raw event dicts."""
from __future__ import annotations

import json


def parse_event(raw: str) -> dict | None:
    """Decode one JSON object line; return None for blank or malformed lines."""
    stripped = raw.strip()
    if not stripped:
        return None
    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError:
        return None
    if not isinstance(parsed, dict):
        return None
    parsed["ingested_version"] = 1
    return parsed


def ingest_batch(lines: list[str]) -> list[dict]:
    """Parse a batch of raw JSON lines, dropping blank and invalid entries."""
    events: list[dict] = []
    for line in lines:
        item = parse_event(line)
        if item is not None:
            events.append(item)
    return events
EOF

cat > repo/src/transform.py <<'EOF'
"""Stage 2: normalize event fields and drop non-positive amounts."""
from __future__ import annotations


def normalize_record(record: dict) -> dict | None:
    """Normalize kind to lowercase and coerce amount_cents to positive int."""
    kind = str(record.get("kind") or "").strip().lower()
    if not kind:
        return None
    try:
        amount_cents = int(record["amount_cents"])
    except (KeyError, TypeError, ValueError):
        return None
    if amount_cents <= 0:
        return None
    return {
        "kind": kind,
        "amount_cents": amount_cents,
        "ingested_version": int(record.get("ingested_version", 1)),
    }


def transform_batch(records: list[dict]) -> list[dict]:
    """Normalize and filter a list of ingested records."""
    cleaned: list[dict] = []
    for rec in records:
        norm = normalize_record(rec)
        if norm is not None:
            cleaned.append(norm)
    return cleaned
EOF

cat > repo/src/sink.py <<'EOF'
"""Stage 3: aggregate normalized records and expose the end-to-end runner."""
from __future__ import annotations

from collections import defaultdict

from ingest import ingest_batch
from transform import transform_batch


def format_summary(records: list[dict]) -> dict[str, object]:
    """Aggregate accepted record counts and totals by normalized kind."""
    totals: dict[str, int] = defaultdict(int)
    for rec in records:
        totals[str(rec["kind"])] += int(rec["amount_cents"])
    return {
        "accepted_count": len(records),
        "totals_by_kind": dict(sorted(totals.items())),
    }


def run_pipeline(lines: list[str]) -> dict[str, object]:
    """Execute ingest -> transform -> sink end-to-end on raw JSONL input."""
    raw_events = ingest_batch(lines)
    normalized = transform_batch(raw_events)
    return format_summary(normalized)
EOF

cat > repo/tests/test_pipeline.py <<'EOF'
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from sink import run_pipeline


class PipelineTest(unittest.TestCase):
    def test_end_to_end_pipeline(self):
        lines = [
            '{"kind": "Order", "amount_cents": 1500}',
            'not-json',
            '{"kind": "order", "amount_cents": 500}',
            '{"kind": "refund", "amount_cents": -100}',
            '{"kind": "Fee", "amount_cents": 250}',
        ]
        summary = run_pipeline(lines)
        self.assertEqual(summary, {"accepted_count": 3, "totals_by_kind": {"fee": 250, "order": 2000}})
EOF

git -C repo add .
git -C repo commit -q -m "add 3-stage pipe-walk pipeline and unit test"
