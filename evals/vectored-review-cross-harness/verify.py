#!/usr/bin/env python3
"""Objective post-run verifier for vectored-review-cross-harness.

Verifies ALL THREE objective invariants:
  1. `repo/` was untouched.
  2. Saved reproduction scripts fail on the buggy `auth.py` and pass on the fixed version
     (requiring objective proof of `bug1_expired_refresh` and tracking `bug2_timing_compare`).
  3. A cross-harness reviewer from `program/settings.json`'s `reviewer_pool` ACTUALLY ran
     and succeeded (verified by persisted `*.receipt.json` inside the workspace matching an
     approved cross-harness pool entry with `role == "reviewer"`, `harness != host`,
     `exit_code == 0`, `timed_out == false`, and non-empty output) so the host harness alone
     cannot pass this eval.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from _repro_verify import PlantedBug, verify_reproductions  # noqa: E402


def fix_bug1_expired_refresh(repo: Path) -> None:
    p = repo / "auth.py"
    text = p.read_text(encoding="utf-8")
    old = '    if tag != "r" and expires_at <= now_ts:\n        return None'
    new = "    if expires_at <= now_ts:\n        return None"
    assert old in text, "bug1 anchor missing in auth.py"
    p.write_text(text.replace(old, new, 1), encoding="utf-8")


def fix_bug2_timing_compare(repo: Path) -> None:
    p = repo / "auth.py"
    text = p.read_text(encoding="utf-8")
    old = "    if expected != sig:\n        return None"
    new = "    if not hmac.compare_digest(expected, sig):\n        return None"
    assert old in text, "bug2 anchor missing in auth.py"
    p.write_text(text.replace(old, new, 1), encoding="utf-8")


PLANTED_BUGS = [
    PlantedBug("bug1_expired_refresh", "verify_token skips expiry check for refreshed tokens", fix_bug1_expired_refresh, attempts=1),
    PlantedBug("bug2_timing_compare", "verify_token uses != instead of hmac.compare_digest", fix_bug2_timing_compare, attempts=1),
]


def _host_native_provider(host: str) -> str:
    return {
        "claude": "anthropic",
        "codex": "openai",
        "agy": "google",
        "cursor": "cursor",
        "devin": "devin",
    }.get(host, "")


def verify_cross_harness_receipts(ws: Path) -> tuple[bool, list[dict], str]:
    """Verify at least one successful cross-harness reviewer receipt exists for an approved pool model."""
    host = (os.environ.get("ASTACK_EVAL_HARNESS") or "claude").strip().lower()
    settings_path = ws / "program" / "settings.json"
    if not settings_path.is_file():
        return False, [], "missing program/settings.json"
    try:
        settings = json.loads(settings_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return False, [], f"invalid program/settings.json: {exc}"

    pool = settings.get("reviewer_pool") if isinstance(settings, dict) else None
    if not isinstance(pool, list):
        return False, [], "program/settings.json missing reviewer_pool list"

    native_prov = _host_native_provider(host)
    cross_entries: set[tuple[str, str, str]] = set()  # (provider_lower, model, expected_harness)
    for ent in pool:
        if not isinstance(ent, dict):
            continue
        prov = str(ent.get("provider", "")).strip().lower()
        mod = str(ent.get("model", "")).strip()
        h = str(ent.get("harness", "")).strip().lower()
        if not prov or not mod:
            continue
        is_cross = (bool(h) and h != host) or (not h and bool(native_prov) and prov != native_prov)
        if is_cross:
            cross_entries.add((prov, mod, h))

    if not cross_entries:
        return False, [], f"no cross-harness entries configured in reviewer_pool for host={host!r}"

    repo_resolved = (ws / "repo").resolve()
    valid_receipts: list[dict] = []
    seen_files: list[str] = []
    for rpath in sorted(ws.resolve().rglob("*.receipt.json")):
        try:
            rpath.relative_to(repo_resolved)
            continue  # ignore anything inside repo/
        except ValueError:
            pass
        seen_files.append(str(rpath.relative_to(ws.resolve())))
        try:
            rec = json.loads(rpath.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(rec, dict):
            continue
        role = str(rec.get("role", "")).strip().lower()
        rh = str(rec.get("harness", "")).strip().lower()
        rprov = str(rec.get("provider", "")).strip().lower()
        rmod = str(rec.get("model", "")).strip()
        exit_code = rec.get("exit_code")
        timed_out = bool(rec.get("timed_out", False))
        stdout_len = int(rec.get("stdout_len", 0) or 0)
        if role != "reviewer" or not rh or rh == host or exit_code != 0 or timed_out or stdout_len <= 0:
            continue
        matched = any(
            rprov == ep and rmod == em and (not eh or rh == eh)
            for ep, em, eh in cross_entries
        )
        if matched:
            valid_receipts.append(
                {
                    "file": str(rpath.relative_to(ws.resolve())),
                    "harness": rh,
                    "provider": rprov,
                    "model": rmod,
                    "exit_code": exit_code,
                    "stdout_len": stdout_len,
                }
            )

    if not valid_receipts:
        return (
            False,
            [],
            f"no successful cross-harness reviewer dispatch receipt found for host={host!r} "
            f"(expected one of {sorted(cross_entries)}; found receipt files: {seen_files})",
        )
    return True, valid_receipts, f"verified {len(valid_receipts)} cross-harness reviewer receipt(s)"


def main() -> int:
    ws = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    repro_code, report = verify_reproductions(ws, PLANTED_BUGS, min_proven=1, require_all=("bug1_expired_refresh",))
    rc_ok, valid_receipts, rc_msg = verify_cross_harness_receipts(ws)
    report["cross_harness_verified"] = rc_ok
    report["cross_harness_receipts"] = valid_receipts
    if not rc_ok:
        print(f"FAIL: {rc_msg}", file=sys.stderr)
        print("PROVEN_BUGS_JSON: " + json.dumps(report))
        return 1
    if repro_code != 0:
        return repro_code
    print(f"PASS: {rc_msg}")
    print("PROVEN_BUGS_JSON: " + json.dumps(report))
    return 0


if __name__ == "__main__":
    sys.exit(main())
