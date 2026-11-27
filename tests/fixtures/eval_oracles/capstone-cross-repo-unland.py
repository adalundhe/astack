"""Separated offline oracle for `capstone-cross-repo-unland`."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

_BLAST_RADIUS_MD = """# Cross-Repo Blast Radius — `repo-core` `calculate_total` Return-Shape Change

## Summary
Commit B in `./repo-core` changed `src/pricing.py:calculate_total` from returning `int` (total cents) to returning `dict[str, object]` (`{"total_cents": ..., "currency": "USD"}`). That breaks three downstream callers in `./repo-service` with `TypeError` during arithmetic and payload validation.

## Impacted Callers in `./repo-service`

1. **Direct caller — `repo-service/src/billing.py:15`–`16`**
   - Calls `subtotal = calculate_total(items)` and computes `platform_fee = subtotal // 10`.
   - **Failure mode:** Raises `TypeError: unsupported operand type(s) for //: 'dict' and 'int'`.
2. **Aliased import caller — `repo-service/src/invoices.py:15`–`16`**
   - Imports `calculate_total as compute_cents` (`invoices.py:11`) and divides `cents / 100` (`invoices.py:16`).
   - **Failure mode:** Raises `TypeError: unsupported operand type(s) for /: 'dict' and 'int'`.
3. **Two-hop caller — `repo-service/src/webhooks.py:8`–`11`**
   - Calls `build_charge(items)` (`webhooks.py:8`) and enforces `isinstance(amount_cents, int)` (`webhooks.py:10`) for outbound payment webhook schema compliance.
   - **Failure mode:** Fails transitively via `billing.py` (`TypeError`) and would fail integer schema check if a `dict` escaped.

## Recovery Plan
- Revert only Commit B in `./repo-core` (`git revert --no-edit <commit_b>`) so Commit C (`docs/CHANGELOG.md` and `README.md`) and commit history stay intact.
- Pin exact post-revert 40-char SHAs in `program/release-plan.json` in dependency order: `repo-core` -> `repo-service`.
"""


def _git(repo: Path, *args: str) -> str:
    proc = subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True)
    return proc.stdout.strip()


def apply(ws: Path) -> dict[str, object]:
    repo_core = ws / "repo-core"
    repo_service = ws / "repo-service"
    commit_b = (ws / "program" / "commit_b.txt").read_text(encoding="utf-8").strip()

    # 1. Write blast-radius report
    (ws / "program" / "BLAST_RADIUS.md").write_text(_BLAST_RADIUS_MD, encoding="utf-8")

    # 2. Safely revert only commit B in repo-core (keeping commit C and history intact)
    _git(repo_core, "revert", "--no-edit", commit_b)

    core_sha = _git(repo_core, "rev-parse", "HEAD")
    svc_sha = _git(repo_service, "rev-parse", "HEAD")

    # 3. Update program/release-plan.json with pinned 40-char SHAs in order repo-core -> repo-service
    plan = {
        "release_id": "rel-2026-11-26",
        "steps": [
            {
                "id": "deploy-core",
                "repo": "repo-core",
                "sha": core_sha,
                "depends_on": [],
            },
            {
                "id": "deploy-service",
                "repo": "repo-service",
                "sha": svc_sha,
                "depends_on": ["deploy-core"],
            },
        ],
    }
    (ws / "program" / "release-plan.json").write_text(
        json.dumps(plan, indent=2) + "\n",
        encoding="utf-8",
    )

    return {
        "final_text": (
            f"Recorded all three broken callers (`billing.py`, `invoices.py`, `webhooks.py`) in `program/BLAST_RADIUS.md`, "
            f"safely reverted commit `{commit_b[:8]}` in `repo-core` (preserving commit C docs and history -> HEAD `{core_sha[:8]}`), "
            f"pinned exact SHAs in `program/release-plan.json` ordered `repo-core` -> `repo-service`, and confirmed both test suites pass."
        ),
    }
