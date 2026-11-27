#!/usr/bin/env python3
"""Objective post-run verifier for skill-net-trace."""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _eval_kit

_STAMP_RE = re.compile(r"_\d{4}_\d{2}_\d{2}_\d{2}_\d{2}_\d{2}(?:_\d+)?$")


def _collect_report(ws: Path) -> str:
    parts: list[str] = []
    md = ws / "program" / "NET_TRACE.md"
    if md.is_file():
        parts.append(md.read_text(encoding="utf-8", errors="replace").strip())
    ft = _eval_kit.final_text_from_env().strip()
    if ft:
        parts.append(ft)
    return "\n\n".join(p for p in parts if p)


def main() -> int:
    ws = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd().resolve()
    repo = ws / "repo"
    astack_home = _eval_kit.astack_home_from_env(ws).resolve()
    astack_tools = Path(__file__).resolve().parents[2] / "bin" / "astack-tools"
    checks: list[tuple[str, bool, str]] = []

    if not repo.is_dir():
        checks.append(("repo-exists", False, f"missing repo directory: {repo}"))
        return _eval_kit.report_and_exit(checks)

    ok_clean, msg_clean = _eval_kit.check_git_clean(repo)
    checks.append(("repo-clean", ok_clean, msg_clean))

    env = {**os.environ, "ASTACK_HOME": str(astack_home)}
    proc = subprocess.run(
        [sys.executable, "-B", str(astack_tools), "logging", "list", "--project", "edge-gw", "--kind", "traces", "--json"],
        capture_output=True,
        text=True,
        env=env,
    )
    trace_entries: list[dict[str, object]] = []
    if proc.returncode == 0:
        try:
            payload = json.loads(proc.stdout)
            raw = payload.get("logging", [])
            if isinstance(raw, list):
                trace_entries = [e for e in raw if isinstance(e, dict)]
        except json.JSONDecodeError:
            pass

    trace_files: list[Path] = []
    for ent in trace_entries:
        p = Path(str(ent.get("path", ""))).resolve()
        if p.is_file() and p.stat().st_size > 0 and _STAMP_RE.search(p.stem):
            trace_files.append(p)

    checks.append((
        "trace-capture-persisted",
        bool(trace_files),
        f"saved {len(trace_files)} UTC-stamped trace(s): {[f.name for f in trace_files]}"
        if trace_files
        else f"no non-empty UTC-stamped trace file found under {astack_home / 'edge-gw' / 'logging' / 'traces'}",
    ))

    trace_texts = [p.read_text(encoding="utf-8", errors="replace") for p in trace_files]
    trace_grounded = any(
        "subnet-app-2" in t.lower() and "drop" in t.lower() and "443" in t
        for t in trace_texts
    )
    checks.append((
        "trace-capture-grounded",
        trace_grounded,
        "saved trace capture contains subnet-app-2 TCP/443 DROP evidence"
        if trace_grounded
        else "saved trace capture missing subnet-app-2 / DROP / 443 evidence",
    ))

    report = _collect_report(ws)
    low = report.lower()
    checks.append((
        "report-present",
        len(report) >= 150,
        f"collected {len(report)} chars across program/NET_TRACE.md and final_text"
        if len(report) >= 150
        else "missing substantive trace report in program/NET_TRACE.md or final_text",
    ))

    failing_hop_ok = (
        "subnet-app-2" in low
        and "egress" in low
        and "443" in report
        and "drop" in low
        and ("sg-app-2" in low or "nacl-app-2" in low)
    )
    checks.append((
        "failing-hop-pinpointed",
        failing_hop_ok,
        "pinpointed subnet-app-2 egress TCP/443 DROP on sg-app-2/nacl-app-2"
        if failing_hop_ok
        else "report missing exact failing hop details (subnet-app-2, egress, 443, DROP, sg-app-2/nacl-app-2)",
    ))

    clears_dns = ("dns" in low and ("198.51.100.44" in report or "cname" in low or "noerror" in low))
    clears_tls = ("tls" in low or "cert" in low) and ("valid" in low or "2027" in report or "ok" in low or "never reached" in low or "before clienthello" in low)
    clears_decoy = "subnet-app-1" in low and ("accept" in low or "healthy" in low or "succeed" in low or "allow" in low)
    checks.append((
        "healthy-hops-cleared",
        clears_dns and clears_tls and clears_decoy,
        f"dns={clears_dns}, tls={clears_tls}, decoy_subnet_app_1={clears_decoy}",
    ))

    mentions_scoped_fix = (
        "198.51.100.44" in report
        and "443" in report
        and ("sg-app-2" in low and "nacl-app-2" in low)
        and bool(re.search(r"\b(add|allow|outbound|egress)\b", low))
    )
    overly_broad = bool(re.search(r"allow\s+(?:all\s+ports|any\s+port|0\.0\.0\.0/0\s+(?:all|any))", low))
    checks.append((
        "minimal-least-privilege-fix",
        mentions_scoped_fix and not overly_broad,
        f"scoped_fix={mentions_scoped_fix}, overly_broad={overly_broad}",
    ))

    sec_hits = _eval_kit.check_no_secrets([*trace_texts, report])
    checks.append(("no-secrets", not sec_hits, "none" if not sec_hits else "; ".join(sec_hits)))

    leak_hits = _eval_kit.check_no_internal_leaks([report])
    checks.append(("no-internal-leaks", not leak_hits, "none" if not leak_hits else "; ".join(leak_hits)))

    return _eval_kit.report_and_exit(checks)


if __name__ == "__main__":
    sys.exit(main())
