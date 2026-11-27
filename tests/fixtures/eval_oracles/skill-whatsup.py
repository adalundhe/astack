"""Separated offline oracle for `skill-whatsup`."""
from __future__ import annotations

from pathlib import Path


def apply(ws: Path) -> dict[str, object]:
    """Read durable repo/program state and produce a plain catch-up summary without editing repo."""
    merged_sha = (ws / "program" / "merged_sha.txt").read_text(encoding="utf-8").strip()
    summary = (
        "# Catch-Up Summary\n\n"
        "1. **Waiting on you:** `lane/cache` is blocked on the missing schema key `cache_ttl_seconds` "
        "in the config schema — decide whether to require it or default to 300s (pick: default to 300s).\n"
        "2. **Bugs, regressions, and losses:** none.\n"
        f"3. **Features, fixes, and milestones:** `lane/parser` merged nested JSON array parsing on `main` (verified `{merged_sha[:7]}` / `{merged_sha}`).\n"
        "4. **Hypotheses, experiments, and research:** benchmark showed 4x concurrent read throughput under SQLite WAL mode.\n"
        "5. **Decisions settled:** `decided:` local persistence journal mode -> SQLite WAL mode (measured benchmark).\n"
        "6. **In flight and next:** `lane/cache` waiting on schema key choice; next step is unblocking and finishing cache lane.\n"
    )
    (ws / "program" / "CATCHUP.md").write_text(summary, encoding="utf-8")
    return {"final_text": summary}
