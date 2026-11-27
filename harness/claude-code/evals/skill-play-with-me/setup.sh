#!/usr/bin/env bash
set -euo pipefail

mkdir -p program/prototype repo/src

git -C repo init -q -b main
git -C repo config user.name "Eval"
git -C repo config user.email "eval@example.invalid"
git -C repo config commit.gpgsign false

cat > repo/src/reports.py <<'EOF'
"""Production report catalog module (do not modify during prototyping)."""
from __future__ import annotations


class ReportCatalog:
    def __init__(self, reports: list[str] | None = None) -> None:
        self._reports = list(reports or ["q3-revenue", "churn-cohort", "latency-audit"])

    def list_reports(self) -> list[str]:
        return list(self._reports)

    def remove(self, name: str) -> bool:
        if name in self._reports:
            self._reports.remove(name)
            return True
        return False
EOF

git -C repo add .
git -C repo commit -q -m "add production ReportCatalog stub"

cat > program/design_question.md <<'EOF'
# Design Question: Report Deletion UX

We want to compare two state-transition UX flows for deleting a saved report (`churn-cohort`) before implementing anything in `./repo/src/reports.py`:

1. **`undo` (immediate undo flow):** Delete transitions the report immediately from `active` -> `pending_delete` with a 5-second undo window; choosing undo transitions `pending_delete` -> `restored` (back to `active`) without a blocking dialog before deletion.
2. **`confirm` (two-step confirm flow):** Delete enters `awaiting_confirmation` and prompts `Confirm delete 'churn-cohort'? [y/N]`; declining cancels back to `active` (`cancelled`), while confirming transitions to `deleted`.

## Prototype Contract
- Place the throwaway prototype at `./program/prototype/demo.py` (strictly outside `./repo`).
- Support non-interactive execution via `--scenario`:
  - `python3 -B program/prototype/demo.py --scenario undo`
  - `python3 -B program/prototype/demo.py --scenario confirm`
- Touch no real files or production code in `./repo`; stub the in-memory report list and simulated user input/timer, and explicitly state what is mocked.
EOF
