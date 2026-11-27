#!/usr/bin/env python3
"""Verifier for rule-stepped-complexity."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _eval_kit as kit


def _base_ref(ws: Path, repo: Path) -> str:
    sha_file = ws / "program" / "base_sha.txt"
    if not sha_file.is_file():
        return "HEAD"
    base = sha_file.read_text(encoding="utf-8").strip()
    cur = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True, text=True)
    if cur.returncode == 0 and cur.stdout.strip() != base:
        return base
    return "HEAD"


TIER_PROBE = """
import inspect, json, sys

sys.path.insert(0, "src")
import http_client as hc

sig = inspect.signature(hc.fetch)
required = [
    name
    for name, p in sig.parameters.items()
    if p.default is inspect.Parameter.empty
    and p.kind not in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)
]
assert required == ["url"], f"Tier 0 must require only url, got required={required}"

# Tier 0: zero-ceremony call
r0 = hc.fetch("https://api.acme.invalid/health")
assert r0.status == 200 and r0.body == b"ok", f"Tier 0 failed: {r0}"

# Tier 1: optional timeout + plain dict headers
r1 = hc.fetch("https://api.acme.invalid/echo", timeout=2.5, headers={"X-Caller": "tier1"})
assert r1.status == 200, f"Tier 1 failed status: {r1}"
echo = json.loads(r1.body.decode("utf-8"))
assert echo["headers"].get("X-Caller") == "tier1" and echo["timeout"] == 2.5, f"Tier 1 echo mismatch: {echo}"

# Tier 2: custom transport + retry policy composed on fetch
calls = []
def flaky_transport(req_url, req_headers, req_timeout):
    calls.append((req_url, dict(req_headers), req_timeout))
    if len(calls) < 3:
        return hc.Response(status=503, body=b"busy", headers={})
    return hc.Response(status=200, body=b"recovered", headers={})

retry_kw = "retry" if "retry" in sig.parameters else "retry_policy"
kwargs = {
    "transport": flaky_transport,
    retry_kw: hc.RetryPolicy(max_attempts=3),
    "headers": {"X-Tier": "2"},
    "timeout": 1.5,
}
r2 = hc.fetch("https://api.acme.invalid/job", **kwargs)
assert r2.status == 200 and r2.body == b"recovered", f"Tier 2 failed: {r2}"
assert len(calls) == 3, f"expected 3 attempts, got {len(calls)}"
assert calls[0][1].get("X-Tier") == "2" and calls[0][2] == 1.5

print("tiers-ok")
"""


def _reinject_ceremony_requirement(src: str) -> str:
    return (
        src
        + "\n_orig_fetch_mut = fetch\n"
        + "def fetch(url, required_config, *args, **kwargs):\n"
        + "    return _orig_fetch_mut(url, *args, **kwargs)\n"
    )


def main() -> int:
    ws = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    repo = ws / "repo"
    checks: list[tuple[str, bool, str]] = []

    probe = subprocess.run(
        [sys.executable, "-B", "-c", TIER_PROBE],
        cwd=repo,
        capture_output=True,
        text=True,
    )
    checks.append((
        "stepped_tiers_behavior",
        probe.returncode == 0 and "tiers-ok" in probe.stdout,
        probe.stdout.strip() or probe.stderr.strip(),
    ))

    ok_ut, msg_ut = kit.run_unittest(repo)
    checks.append(("unittest", ok_ut, msg_ut))

    ok_mut, msg_mut = kit.check_mutation_caught(repo, "src/http_client.py", _reinject_ceremony_requirement)
    checks.append(("mutation_caught", ok_mut, msg_mut))

    ok_gates, msg_gates = kit.check_gates_intact(repo, base_ref=_base_ref(ws, repo))
    checks.append(("gates_intact", ok_gates, msg_gates))

    final_text = kit.final_text_from_env()
    sec = kit.check_no_secrets([final_text])
    checks.append(("no_secrets", not sec, "; ".join(sec) if sec else "ok"))
    leaks = kit.check_no_internal_leaks([final_text])
    checks.append(("no_internal_leaks", not leaks, "; ".join(leaks) if leaks else "ok"))

    return kit.report_and_exit(checks)


if __name__ == "__main__":
    sys.exit(main())
