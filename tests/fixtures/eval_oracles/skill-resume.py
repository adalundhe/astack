"""Separated offline oracle for `skill-resume`."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path


def apply(ws: Path) -> dict[str, object]:
    """Complete step 2 retry cap in src/sync.py + tests and log resumption in LANES.md."""
    repo = ws / "repo"
    (repo / "src" / "sync.py").write_text(
        '"""Incremental sync helpers."""\n'
        "from __future__ import annotations\n\n\n"
        "class TransientSyncError(RuntimeError):\n"
        '    """Raised when a remote sync call fails transiently."""\n\n\n'
        "def normalize_batch(records: list[str]) -> list[str]:\n"
        "    return [r.strip() for r in records if r.strip()]\n\n\n"
        "def checkpoint_offset(offset: int, processed: int) -> int:\n"
        '    """Advance a sync cursor offset monotonically."""\n'
        "    if offset < 0 or processed < 0:\n"
        '        raise ValueError("offset and processed must be non-negative")\n'
        "    return offset + processed\n\n\n"
        "def sync_batch(fetch_fn, items: list, *, max_retries: int = 3) -> list:\n"
        '    """Fetch each item via fetch_fn(item), retrying TransientSyncError up to max_retries times.\n\n'
        "    Total attempts per item = 1 initial attempt + up to max_retries retries.\n"
        "    Raises ValueError if max_retries < 0.\n"
        "    If all attempts fail with TransientSyncError, raises the last TransientSyncError.\n"
        '    """\n'
        "    if max_retries < 0:\n"
        '        raise ValueError("max_retries must be >= 0")\n'
        "    results = []\n"
        "    for item in items:\n"
        "        last_err: TransientSyncError | None = None\n"
        "        for _ in range(max_retries + 1):\n"
        "            try:\n"
        "                results.append(fetch_fn(item))\n"
        "                last_err = None\n"
        "                break\n"
        "            except TransientSyncError as exc:\n"
        "                last_err = exc\n"
        "        if last_err is not None:\n"
        "            raise last_err\n"
        "    return results\n",
        encoding="utf-8",
    )
    (repo / "tests" / "test_sync.py").write_text(
        "import sys\n"
        "import unittest\n"
        "from pathlib import Path\n\n"
        'sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))\n'
        "from sync import TransientSyncError, checkpoint_offset, normalize_batch, sync_batch\n\n\n"
        "class SyncTest(unittest.TestCase):\n"
        "    def test_normalize_batch(self):\n"
        '        self.assertEqual(normalize_batch([" a ", "", "b"]), ["a", "b"])\n\n'
        "    def test_checkpoint_offset(self):\n"
        "        self.assertEqual(checkpoint_offset(10, 5), 15)\n"
        "        with self.assertRaises(ValueError):\n"
        "            checkpoint_offset(-1, 2)\n\n"
        "    def test_sync_batch_happy_path(self):\n"
        "        self.assertEqual(sync_batch(lambda x: x * 2, [1, 2, 3]), [2, 4, 6])\n\n"
        "    def test_sync_batch_enforces_retry_cap(self):\n"
        "        calls = []\n"
        "        def fail_always(item):\n"
        "            calls.append(item)\n"
        '            raise TransientSyncError("down")\n'
        "        with self.assertRaises(TransientSyncError):\n"
        "            sync_batch(fail_always, [1], max_retries=2)\n"
        "        self.assertEqual(len(calls), 3)\n\n"
        "    def test_sync_batch_succeeds_before_retry_cap(self):\n"
        "        calls = []\n"
        "        def fail_twice(item):\n"
        "            calls.append(item)\n"
        "            if len(calls) <= 2:\n"
        '                raise TransientSyncError("glitch")\n'
        "            return item + 1\n"
        "        self.assertEqual(sync_batch(fail_twice, [4], max_retries=2), [5])\n"
        "        self.assertEqual(len(calls), 3)\n\n"
        "    def test_sync_batch_rejects_negative_max_retries(self):\n"
        "        with self.assertRaises(ValueError):\n"
        "            sync_batch(lambda x: x, [1], max_retries=-1)\n",
        encoding="utf-8",
    )

    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
    lanes_path = ws / "program" / "LANES.md"
    existing = lanes_path.read_text(encoding="utf-8")
    prefix = "" if existing.endswith("\n") else "\n"
    lanes_path.write_text(
        existing + prefix + f"{stamp} resumed lane/sync from checkpoint; completed step 2 retry cap in src/sync.py\n",
        encoding="utf-8",
    )
    return {
        "final_text": (
            "Resumed `lane/sync` from `program/SUSPENDED.md`, preserved step 1 (`checkpoint_offset`), "
            "implemented the `max_retries` cap in `src/sync.py` with regression tests in `tests/test_sync.py`, "
            f"verified unittest passes, and logged resumption at `{stamp}` in `program/LANES.md`."
        ),
    }
