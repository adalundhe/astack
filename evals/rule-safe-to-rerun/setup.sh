#!/bin/bash
set -euo pipefail
mkdir -p repo/src repo/tests

git -C repo init -q -b main
git -C repo config user.name "Eval"
git -C repo config user.email "eval@example.invalid"
git -C repo config commit.gpgsign false

cat > repo/README.md <<'EOF'
# Ledger Exporter

Exports ledger transactions to a JSONL file in `src/ledger_exporter.py`.

## Public Contract

### `export_entries(target_path: Path, entries: list[dict[str, object]], *, on_row_written: Callable[[str], None] | None = None) -> int`
Each entry is a dict with `tx_id` (`str`), `account` (`str`), and `amount_cents` (`int`).

Requirements:
- **Idempotent convergence**: If `target_path` already exists, read its existing valid JSONL entries and merge with `entries` keyed by `tx_id` (deduplicating repeated `tx_id`s; entries sorted ascending by `tx_id`). Running `export_entries` twice with the same or overlapping batches must produce byte-identical output with zero duplicate `tx_id`s.
- **Atomic crash-safe writes**: Write the full converged JSONL to a PID-tagged temporary file in `target_path.parent` (named `.{target_path.name}.{pid}.tmp`), invoke `on_row_written(tx_id)` after each row is written to the temp file if provided, flush + `os.fsync`, and atomically swap into place with `os.replace`.
- **Crash preservation**: If an exception occurs mid-write (for example inside `on_row_written`), remove the incomplete temp file and re-raise while leaving `target_path` untouched with its prior contents.
- **Stale leftover cleanup**: Detect and remove stale `.{target_path.name}.*.tmp` leftovers in `target_path.parent` from crashed prior runs when rerunning.
- **Return value**: Total number of unique entries in the converged target file.
EOF

cat > repo/src/__init__.py <<'EOF'
EOF

cat > repo/src/ledger_exporter.py <<'EOF'
from __future__ import annotations

import json
from pathlib import Path
from typing import Callable


def export_entries(
    target_path: Path,
    entries: list[dict[str, object]],
    *,
    on_row_written: Callable[[str], None] | None = None,
) -> int:
    target_path.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with target_path.open("a", encoding="utf-8") as fh:
        for entry in entries:
            fh.write(json.dumps(entry, sort_keys=True) + "\n")
            fh.flush()
            written += 1
            if on_row_written is not None:
                on_row_written(str(entry["tx_id"]))
    return written
EOF

cat > repo/tests/__init__.py <<'EOF'
EOF

cat > repo/tests/test_ledger_exporter.py <<'EOF'
import json
from pathlib import Path
import tempfile
import unittest

from src.ledger_exporter import export_entries


class LedgerExporterBasicTest(unittest.TestCase):
    def test_writes_entries_to_new_file(self):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "ledger.jsonl"
            entries = [
                {"tx_id": "tx-001", "account": "acct-a", "amount_cents": 1500},
                {"tx_id": "tx-002", "account": "acct-b", "amount_cents": 2500},
            ]
            count = export_entries(target, entries)
            self.assertEqual(count, 2)
            rows = [json.loads(line) for line in target.read_text(encoding="utf-8").splitlines()]
            self.assertEqual([r["tx_id"] for r in rows], ["tx-001", "tx-002"])


if __name__ == "__main__":
    unittest.main()
EOF

git -C repo add -A
git -C repo commit -q -m "initial"
