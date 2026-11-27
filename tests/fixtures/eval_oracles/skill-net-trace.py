"""Separated offline oracle for `skill-net-trace`."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

_ASTACK_TOOLS = Path(__file__).resolve().parents[3] / "bin" / "astack-tools"


def apply(ws: Path) -> dict[str, object]:
    """Save trace capture under ASTACK_HOME/edge-gw/logging/traces/ and write program/NET_TRACE.md."""
    astack_home = (ws / "program" / "astack_home").resolve()
    env = {**os.environ, "ASTACK_HOME": str(astack_home)}
    trace_path = subprocess.run(
        [sys.executable, "-B", str(_ASTACK_TOOLS), "logging", "path", "edge-gw", "traces", "subnet_app_2_egress.trace", "--ensure"],
        capture_output=True,
        text=True,
        env=env,
        check=True,
    ).stdout.strip()

    flow_logs = (ws / "program" / "net_bundle" / "flow_logs.log").read_text(encoding="utf-8")
    Path(trace_path).write_text(
        "# Retained Flow-Log Trace Capture (edge-gw: subnet-app-2 -> 198.51.100.44:443)\n"
        + flow_logs,
        encoding="utf-8",
    )

    report = f"""# Network Trace Report: edge-gw (`subnet-app-2` -> `api.partner.internal:443`)

## Wire Symptom
- Silent TCP connect timeout (`connect() timed out after 10000ms before ClientHello`) from `subnet-app-2` (`10.20.2.21`) to `198.51.100.44:443`. Matches stateful/stateless policy drop.

## Hop-by-Hop Verdict
1. **DNS (Cleared):** Both `subnet-app-1` and `subnet-app-2` resolve `api.partner.internal` via CNAME `gw-prod.edge.internal` -> `198.51.100.44` (`NOERROR`, TTL 300).
2. **Routing (Cleared):** Both `rtb-app-1` and `rtb-app-2` have active routes for `198.51.100.0/24` via `nat-gw-01`.
3. **TLS Cert Chain (Cleared):** Server presents a valid chain (`CN=api.partner.internal`, SANs match, valid `2026-01-01` to `2027-06-01`, TLSv1.3, `Verify return code: 0`). `subnet-app-2` never reaches TLS ClientHello due to TCP SYN drop.
4. **Healthy Decoy Control (`subnet-app-1`, Cleared):** Flow logs show `dir=EGRESS action=ACCEPT` and `dir=INGRESS action=ACCEPT` on `sg-app-1`/`nacl-app-1`, returning HTTP/2 200 OK in 18 ms.
5. **Failing Hop (`subnet-app-2` Egress Policy, PROVEN):**
   - `flow_logs.log` records repeated verdicts:
     `subnet=subnet-app-2 sg=sg-app-2 nacl=nacl-app-2 src=10.20.2.21:49812 dst=198.51.100.44:443 proto=TCP dir=EGRESS action=DROP reason=NO_MATCHING_EGRESS_RULE`
   - `policies.json` confirms `sg-app-2` only allows outbound TCP/5432 to `10.20.10.0/24` and `nacl-app-2` outbound only has rule 110 (TCP/5432). Both are missing the outbound TCP/443 allow rule to `198.51.100.44/32`. Inbound ephemeral return traffic (TCP `1024-65535` from `198.51.100.44/32`) is already allowed by `nacl-app-2` rule 100.

## Preserved Trace Evidence
- Saved header/flow-log trace to `{trace_path}`.

## Minimal Least-Privilege Fix
- Add outbound `ALLOW` rule on `sg-app-2` for `tcp/443` scoped strictly to `198.51.100.44/32`.
- Add outbound `ALLOW` rule `100` on `nacl-app-2` for `tcp/443` scoped strictly to `198.51.100.44/32`.
- Apply through IaC review (`safe-iac`, `least-privilege`, `safe-to-deploy`) and re-verify handshake + flow-log `ACCEPT` from `subnet-app-2`.
"""
    (ws / "program" / "NET_TRACE.md").write_text(report, encoding="utf-8")
    return {
        "final_text": (
            f"Saved flow-log trace capture to `{trace_path}` and wrote `program/NET_TRACE.md`. "
            "Pinpointed failing hop: `subnet-app-2` egress TCP/443 `DROP` (`NO_MATCHING_EGRESS_RULE`) due to missing outbound TCP/443 allow rules to `198.51.100.44/32` on `sg-app-2` and `nacl-app-2`. "
            "DNS, routing, TLS cert, and `subnet-app-1` are all healthy."
        ),
    }
