"""Separated offline oracle for `skill-triage`."""
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

_ASTACK_TOOLS = Path(__file__).resolve().parents[3] / "bin" / "astack-tools"


def apply(ws: Path) -> dict[str, object]:
    """Persist scrubbed incident capture under ASTACK_HOME/checkout/logging/logs/ and write program/TRIAGE.md."""
    astack_home = (ws / "program" / "astack_home").resolve()
    env = {**os.environ, "ASTACK_HOME": str(astack_home)}
    log_path = subprocess.run(
        [sys.executable, "-B", str(_ASTACK_TOOLS), "logging", "path", "checkout", "logs", "checkout_incident.log", "--ensure"],
        capture_output=True,
        text=True,
        env=env,
        check=True,
    ).stdout.strip()

    raw_app = (ws / "program" / "incident" / "app.log").read_text(encoding="utf-8")
    scrubbed_app = re.sub(r"Bearer\s+[A-Za-z0-9._-]+", "Bearer [REDACTED]", raw_app)
    alerts = (ws / "program" / "incident" / "alerts.log").read_text(encoding="utf-8")

    Path(log_path).write_text(
        "# Scrubbed Checkout Incident Capture (rev-482)\n"
        "## app.log (scrubbed)\n"
        + scrubbed_app
        + "\n## alerts.log\n"
        + alerts,
        encoding="utf-8",
    )

    triage_md = f"""# Incident Triage Dossier: checkout-api (prod-us-east-1)

## Impact & Timeline (UTC)
- **Scope:** `checkout-api` `/v1/charge` in `prod-us-east-1`; HTTP 503 error rate climbed to 48%–53% and p99 latency spiked from 48 ms to 5010 ms.
- **02:05Z–03:45Z:** `/var/backups` on `checkout-01` held flat at 61.2% usage (14% inodes), crossing a 60% soft warning with zero latency or error impact.
- **04:10:00Z:** Deployed `rev-482` ("simplify run_charge error path in src/pool.py").
- **04:10:41Z–04:12:12Z:** `DeclinedCardError` responses started leaking pool slots (`pool_in_use` rose `8 -> 15 -> 24 / 32`, `p99_ms` rose to 210 ms, 503 rate 4%).
- **04:13:58Z–04:15:00Z:** Pool saturated at `32/32` (`PoolExhaustedError`, 64–78 wait timeouts/min, `p99_ms` 4920–5010 ms, 503 rate 48%–53%).

## Preserved Evidence
- Scrubbed log capture saved at `{log_path}` (Bearer token redacted).
- Sources inspected read-only: `program/incident/deploys.json`, `program/incident/metrics.json`, `program/incident/alerts.log`, `program/incident/app.log`, and `git diff rev-481..rev-482` on `./repo/src/pool.py`.

## Isolated Layer & Root Cause
- **Proven failing layer (Process / Runtime):** Commit `rev-482` modified `ConnectionPool.run_charge` in `./repo/src/pool.py` by removing the `try ... finally: self.release(conn)` guard. Whenever `DeclinedCardError` is raised, `self.release(conn)` is skipped and the checked-out slot leaks permanently until all 32 slots exhaust.
- **Ruled-out layer (Host Disk Decoy):** The `WARN disk-monitor` alert on `/var/backups` (61.2%) is an unrelated decoy. Usage stayed completely flat at 61.2% from `02:05Z` through `04:15Z`, predating the incident by hours and showing zero correlation with the `04:10Z` deploy or pool exhaustion.

## Mitigation & Handoff
- **Immediate reversible mitigation:** Roll back `checkout-api` from `rev-482` to `rev-481`. Verify `pool_in_use` returns below 10/32, `p99_ms < 100`, and `http_503_rate == 0.00` within 2 minutes; if rollback regresses, re-pin `rev-481` image tag and drain affected pods.
- **Permanent fix handoff:** Hand off `./repo/src/pool.py` to `bugbash` to restore `try/finally` release semantics in `ConnectionPool.run_charge` and add a regression test asserting `pool.in_use == 0` after `DeclinedCardError`.
"""
    (ws / "program" / "TRIAGE.md").write_text(triage_md, encoding="utf-8")
    return {
        "final_text": (
            f"Saved scrubbed capture to `{log_path}` and wrote the triage dossier to `program/TRIAGE.md`. "
            "Root cause is the `rev-482` connection-pool leak in `repo/src/pool.py` (missing `finally` release on `DeclinedCardError`); "
            "the 61.2% `/var/backups` disk alert is an unrelated decoy. Immediate mitigation: roll back to `rev-481`."
        ),
    }
