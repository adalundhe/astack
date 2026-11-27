"""Separated offline oracle for `skill-wat`."""
from __future__ import annotations

from pathlib import Path


def violate(ws: Path) -> dict[str, object]:
    """Return the raw buried-lede jargon draft unchanged (must fail RED)."""
    draft = (ws / "program" / "jargon_draft.md").read_text(encoding="utf-8")
    return {"final_text": draft}


def apply(ws: Path) -> dict[str, object]:
    """Rewrite jargon_draft.md putting the double-charge blocker and action first with zero internal leaks."""
    summary = (
        "Do not ship release v2.4: an `orders` table race condition causes double-charges when checkout requests retry concurrently.\n\n"
        "- **Measured in staging:** 3 of 12 concurrent retry requests created duplicate charge rows (p95 checkout latency: 180ms).\n"
        "- **Action needed:** add a row lock or unique idempotency constraint in `src/orders.py`, then re-run the concurrent checkout test before releasing v2.4.\n"
    )
    (ws / "program" / "SUMMARY.md").write_text(summary, encoding="utf-8")
    return {"final_text": summary}
