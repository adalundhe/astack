"""Separated offline oracle for `rule-safe-to-rerun`."""
from __future__ import annotations

from pathlib import Path

FIXED_SRC = r'''from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Callable


def _cleanup_stale_temps(target_path: Path) -> None:
    prefix = f".{target_path.name}."
    for candidate in target_path.parent.glob(f"{prefix}*.tmp"):
        try:
            candidate.unlink()
        except FileNotFoundError:
            pass


def _load_existing(target_path: Path) -> dict[str, dict[str, object]]:
    by_id: dict[str, dict[str, object]] = {}
    if not target_path.is_file():
        return by_id
    for line in target_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        record = json.loads(stripped)
        by_id[str(record["tx_id"])] = record
    return by_id


def export_entries(
    target_path: Path,
    entries: list[dict[str, object]],
    *,
    on_row_written: Callable[[str], None] | None = None,
) -> int:
    target_path.parent.mkdir(parents=True, exist_ok=True)
    _cleanup_stale_temps(target_path)

    converged = _load_existing(target_path)
    for entry in entries:
        converged[str(entry["tx_id"])] = dict(entry)

    ordered_ids = sorted(converged)
    tmp_path = target_path.parent / f".{target_path.name}.{os.getpid()}.tmp"
    try:
        with tmp_path.open("w", encoding="utf-8") as fh:
            for tx_id in ordered_ids:
                fh.write(json.dumps(converged[tx_id], sort_keys=True) + "\n")
                fh.flush()
                if on_row_written is not None:
                    on_row_written(tx_id)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp_path, target_path)
    except BaseException:
        try:
            tmp_path.unlink()
        except FileNotFoundError:
            pass
        raise

    return len(ordered_ids)
'''

FIXED_TESTS = '''import json
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

    def test_double_run_and_overlapping_rerun_are_idempotent(self):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "ledger.jsonl"
            batch1 = [
                {"tx_id": "tx-002", "account": "acct-b", "amount_cents": 2000},
                {"tx_id": "tx-001", "account": "acct-a", "amount_cents": 1000},
            ]
            self.assertEqual(export_entries(target, batch1), 2)
            first_bytes = target.read_bytes()
            self.assertEqual(export_entries(target, batch1), 2)
            self.assertEqual(target.read_bytes(), first_bytes)

            batch2 = [
                {"tx_id": "tx-002", "account": "acct-b", "amount_cents": 2000},
                {"tx_id": "tx-003", "account": "acct-c", "amount_cents": 3000},
            ]
            self.assertEqual(export_entries(target, batch2), 3)
            rows = [json.loads(line) for line in target.read_text(encoding="utf-8").splitlines()]
            self.assertEqual([r["tx_id"] for r in rows], ["tx-001", "tx-002", "tx-003"])

    def test_mid_write_crash_preserves_target_and_rerun_recovers(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            target = root / "ledger.jsonl"
            export_entries(
                target,
                [
                    {"tx_id": "tx-001", "account": "acct-a", "amount_cents": 1000},
                    {"tx_id": "tx-002", "account": "acct-b", "amount_cents": 2000},
                ],
            )
            snapshot = target.read_bytes()

            def crash_on_second(tx_id: str) -> None:
                if tx_id == "tx-002":
                    raise RuntimeError("mid-write disk crash")

            with self.assertRaises(RuntimeError):
                export_entries(
                    target,
                    [{"tx_id": "tx-003", "account": "acct-c", "amount_cents": 3000}],
                    on_row_written=crash_on_second,
                )

            self.assertEqual(target.read_bytes(), snapshot)
            self.assertEqual(list(root.glob("*.tmp")), [])

            stale_tmp = root / f".{target.name}.999999.tmp"
            stale_tmp.write_text("partial", encoding="utf-8")
            self.assertEqual(
                export_entries(target, [{"tx_id": "tx-003", "account": "acct-c", "amount_cents": 3000}]),
                3,
            )
            self.assertFalse(stale_tmp.exists())
            rows = [json.loads(line) for line in target.read_text(encoding="utf-8").splitlines()]
            self.assertEqual([r["tx_id"] for r in rows], ["tx-001", "tx-002", "tx-003"])


if __name__ == "__main__":
    unittest.main()
'''


def apply(ws: Path) -> dict[str, object]:
    repo = ws / "repo"
    (repo / "src" / "ledger_exporter.py").write_text(FIXED_SRC, encoding="utf-8")
    (repo / "tests" / "test_ledger_exporter.py").write_text(FIXED_TESTS, encoding="utf-8")
    return {
        "final_text": (
            "Updated src/ledger_exporter.py to converge existing and incoming entries by tx_id "
            "without duplicates, write sorted JSONL to a same-directory PID-tagged temp file "
            "committed via fsync and os.replace, clean stale temp leftovers on rerun, preserve "
            "the prior file on mid-write crashes, and added idempotence and crash-recovery tests."
        ),
    }
