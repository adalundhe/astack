#!/bin/bash
set -euo pipefail
mkdir -p program repo/src repo/tests

git -C repo init -q -b main
git -C repo config user.name "Eval User"
git -C repo config user.email "eval@example.invalid"
git -C repo config commit.gpgsign false

cat > repo/src/parser.py <<'EOF'
"""JSON payload parser."""
from __future__ import annotations

import json


def parse_record(raw: str) -> dict:
    return json.loads(raw)
EOF

cat > repo/tests/test_parser.py <<'EOF'
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from parser import parse_record


class ParserTest(unittest.TestCase):
    def test_parse_record(self):
        self.assertEqual(parse_record('{"ok": true}'), {"ok": True})
EOF

git -C repo add .
git -C repo commit -q -m "initial parser module"

cat > repo/src/parser.py <<'EOF'
"""JSON payload parser with nested array flattening."""
from __future__ import annotations

import json


def parse_record(raw: str) -> dict:
    return json.loads(raw)


def parse_nested_arrays(raw: str) -> list:
    data = json.loads(raw)
    if not isinstance(data, list):
        raise ValueError("expected JSON array")
    return data
EOF

git -C repo commit -q -am "feat(parser): support nested JSON arrays (lane/parser)"
MERGED_SHA=$(git -C repo rev-parse HEAD)
MERGED_SHORT="${MERGED_SHA:0:7}"
echo "${MERGED_SHA}" > program/merged_sha.txt

cat > program/LANES.md <<EOF
<!-- astack lane log -->
# Storage & Parser Program

Repository: ./repo

## Log
2026-11-26T06:00Z started w1 on lane/parser (agent worker-1) | branch main | wind-down 2026-11-26T06:50Z | ends 2026-11-26T07:00Z
2026-11-26T06:40Z ended w1: landed nested JSON array parser at ${MERGED_SHORT} (${MERGED_SHA})
2026-11-26T06:45Z closed lane/parser: merged at ${MERGED_SHA}
2026-11-26T07:00Z started w2 on lane/cache (agent worker-2) | branch lane/cache | wind-down 2026-11-26T07:50Z | ends 2026-11-26T08:00Z
2026-11-26T07:15Z asked: lane/cache is blocked on missing schema key \`cache_ttl_seconds\` in config schema — should we require it or default to 300s?
2026-11-26T07:20Z decided: local persistence journal mode -> SQLite WAL mode (settled by benchmark; evidence: 4x concurrent read throughput under write load)
EOF

cat > program/DECISIONS.md <<EOF
# Decisions Log

- **2026-11-26T07:20Z** \`decided:\` local persistence journal mode -> **SQLite WAL mode** (settled by benchmark; evidence: 4x concurrent read throughput under write load without reader stalls).
- **Open blocker (lane/cache):** blocked on missing schema key \`cache_ttl_seconds\` in config schema; awaiting human choice (require key vs. default to 300s).
- **Shipped (lane/parser):** merged nested JSON array parser on \`main\` at \`${MERGED_SHA}\`.
EOF
