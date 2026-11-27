"""Separated offline oracle for `skill-play-with-me`."""
from __future__ import annotations

from pathlib import Path

_PROTOTYPE_SCRIPT = '''#!/usr/bin/env python3
"""Throwaway CLI prototype comparing immediate-undo vs two-step-confirm report deletion UX."""
from __future__ import annotations

import argparse

MOCK_REPORTS = ["q3-revenue", "churn-cohort", "latency-audit"]


def run_undo_flow(target: str) -> None:
    items = list(MOCK_REPORTS)
    print("=== Scenario: Immediate Undo Flow (mocked in-memory list + 5s undo window) ===")
    print(f"1. Initial active reports: {items}")
    items.remove(target)
    print(f"2. User runs `delete {target}` -> state: active -> pending_delete (5s undo window open)")
    print(f"   Visible list immediately hides {target!r}: {items}")
    items.insert(1, target)
    print(f"3. User presses Undo within 5s -> state: pending_delete -> restored (active)")
    print(f"   Final active reports: {items}")
    print("Trade-off: zero friction on routine deletes, reversible within 5s window.")


def run_confirm_flow(target: str) -> None:
    items = list(MOCK_REPORTS)
    print("=== Scenario: Two-Step Confirm Flow (mocked in-memory list + simulated [y/N] prompt) ===")
    print(f"1. Initial active reports: {items}")
    print(f"2. User runs `delete {target}` -> state: active -> awaiting_confirmation")
    print(f"   Prompt: Confirm delete '{target}'? [y/N]")
    print(f"3a. Path A (simulated 'n'): state -> cancelled; reports unchanged: {items}")
    after_yes = [r for r in items if r != target]
    print(f"3b. Path B (simulated 'y'): state -> deleted; remaining reports: {after_yes}")
    print("Trade-off: prevents accidental deletes up front, adds an extra step on every delete.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Throwaway UX prototype: undo vs confirm delete flows")
    parser.add_argument(
        "--scenario",
        choices=("undo", "confirm", "both"),
        default="both",
        help="Which UX state-transition flow to demonstrate",
    )
    parser.add_argument("--report", default="churn-cohort", help="Mock report name to delete")
    args = parser.parse_args()

    if args.scenario in ("undo", "both"):
        run_undo_flow(args.report)
    if args.scenario in ("confirm", "both"):
        run_confirm_flow(args.report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''


def apply(ws: Path) -> dict[str, object]:
    """Write the throwaway CLI prototype outside ./repo at program/prototype/demo.py."""
    proto = ws / "program" / "prototype" / "demo.py"
    proto.parent.mkdir(parents=True, exist_ok=True)
    proto.write_text(_PROTOTYPE_SCRIPT, encoding="utf-8")
    proto.chmod(0o755)
    return {
        "final_text": (
            "Built a throwaway CLI prototype at `program/prototype/demo.py` (strictly outside `./repo`, which stays unmodified).\n"
            "- **Mocked/stubbed:** uses an in-memory list of 3 sample reports plus simulated 5-second undo window and `[y/N]` prompt responses; makes zero disk or external calls.\n"
            "- **Try immediate undo:** `python3 -B program/prototype/demo.py --scenario undo`\n"
            "- **Try two-step confirm:** `python3 -B program/prototype/demo.py --scenario confirm`\n"
            "- **What to compare:** notice how `undo` completes in one step with a reversible `pending_delete -> restored` transition, while `confirm` pauses in `awaiting_confirmation` before any deletion occurs."
        ),
    }
