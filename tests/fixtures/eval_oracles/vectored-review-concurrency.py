"""Separated offline oracle for `vectored-review-concurrency`."""
from __future__ import annotations

from pathlib import Path

_REPRO_SPLIT_LOCK = '''import threading
import time

from pool import JobPool


class YieldingLock:
    def __init__(self) -> None:
        self._inner = threading.Lock()

    def __enter__(self):
        self._inner.acquire()
        return self

    def __exit__(self, *args):
        self._inner.release()
        time.sleep(0.005)


def main() -> None:
    pool = JobPool()
    for item in range(6):
        pool.push(item)
    pool._lock = YieldingLock()

    barrier = threading.Barrier(2)
    drained = []
    guard = threading.Lock()

    def worker() -> None:
        barrier.wait()
        batch = pool.drain_batch(3)
        with guard:
            drained.extend(batch)

    threads = [threading.Thread(target=worker) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(drained) == 6 and len(set(drained)) == 6, (
        f"split-lock race duplicated or dropped items: {drained!r}"
    )


if __name__ == "__main__":
    main()
'''


def apply(ws: Path) -> dict[str, object]:
    repros = ws / "program" / "repros"
    repros.mkdir(parents=True, exist_ok=True)
    (repros / "repro_split_lock_drain_batch.py").write_text(_REPRO_SPLIT_LOCK, encoding="utf-8")
    return {
        "final_text": (
            "VERDICT: BLOCKED (`repo/` left untouched).\n\n"
            "Blocking finding:\n"
            "- **Split-lock race in `pool.py:drain_batch` (`repo/pool.py:66-70`)**: `drain_batch` acquires "
            "`self._lock` to snapshot `self._items[:limit]`, releases the lock, and re-acquires it to delete "
            "the slice. Two concurrent callers read overlapping items and then delete twice as many entries, "
            "delivering duplicates and dropping unreturned items. Repro saved at "
            "`program/repros/repro_split_lock_drain_batch.py`. Combine the slice, deletion, and counter update "
            "inside a single `with self._lock:` block.\n"
        ),
        "events": [],
    }
