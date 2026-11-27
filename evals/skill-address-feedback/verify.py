#!/usr/bin/env python3
"""Executable verifier for `skill-address-feedback`."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _eval_kit

_BEHAVIOR_PROBE = r'''
import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd() / "src"))
from pages import paginate

p1 = paginate([10, 20, 30, 40, 50], page=1, page_size=2)
assert p1["items"] == [10, 20], f"page 1 wrong: {p1}"
assert p1["total"] == 5 and p1["total_pages"] == 3 and p1["has_next"] is True, p1

p2 = paginate([10, 20, 30, 40, 50], page=2, page_size=2)
assert p2["items"] == [30, 40], f"page 2 wrong: {p2}"
assert p2["has_next"] is True, p2

p3 = paginate([10, 20, 30, 40, 50], page=3, page_size=2)
assert p3["items"] == [50], f"page 3 wrong: {p3}"
assert p3["has_next"] is False, p3

empty = paginate([], page=1, page_size=5)
assert empty["items"] == [], f"empty items wrong: {empty}"
assert empty["total"] == 0 and empty["total_pages"] == 0 and empty["has_next"] is False, empty
'''


def _root_commit(repo: Path) -> str:
    proc = subprocess.run(
        ["git", "-C", str(repo), "rev-list", "--max-parents=0", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    )
    return proc.stdout.strip().splitlines()[0]


def _inject_empty_input_bug(src: str) -> str:
    return (
        src
        + "\n\n_orig_paginate_for_mut = paginate\n"
        + "def paginate(items, *args, **kwargs):\n"
        + "    if len(items) == 0:\n"
        + "        raise RuntimeError('mutation: empty input unhandled')\n"
        + "    return _orig_paginate_for_mut(items, *args, **kwargs)\n"
    )


def _extract_thread_records(payload: object) -> dict[str, str]:
    records: dict[str, str] = {}
    if isinstance(payload, dict):
        for container_key in ("threads", "resolved_threads", "resolved", "resolutions"):
            val = payload.get(container_key)
            if isinstance(val, list):
                for entry in val:
                    if isinstance(entry, dict):
                        tid = str(entry.get("id") or entry.get("thread_id") or "").strip()
                        if tid:
                            records[tid] = json.dumps(entry, sort_keys=True)
            elif isinstance(val, dict):
                for tid, entry in val.items():
                    records[str(tid)] = json.dumps(entry, sort_keys=True) if not isinstance(entry, str) else entry
        for tid in ("thread-1", "thread-2"):
            if tid in payload and tid not in records:
                val = payload[tid]
                records[tid] = json.dumps(val, sort_keys=True) if not isinstance(val, str) else val
    elif isinstance(payload, list):
        for entry in payload:
            if isinstance(entry, dict):
                tid = str(entry.get("id") or entry.get("thread_id") or "").strip()
                if tid:
                    records[tid] = json.dumps(entry, sort_keys=True)
    return records


def main() -> int:
    ws = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd().resolve()
    repo = ws / "repo"
    resolved_path = ws / "program" / "resolved_threads.json"
    final_text = _eval_kit.final_text_from_env()
    checks: list[tuple[str, bool, str]] = []

    if not repo.is_dir():
        checks.append(("repo-exists", False, f"missing repo directory: {repo}"))
        return _eval_kit.report_and_exit(checks)

    base_sha = _root_commit(repo)
    buggy_src = subprocess.run(
        ["git", "-C", str(repo), "show", f"{base_sha}:src/pages.py"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout

    probe = subprocess.run(
        [sys.executable, "-B", "-c", _BEHAVIOR_PROBE],
        cwd=repo,
        capture_output=True,
        text=True,
        timeout=15,
    )
    checks.append((
        "behavior-paginate",
        probe.returncode == 0,
        "1-indexed pagination and empty input verified"
        if probe.returncode == 0
        else (probe.stderr.strip() or probe.stdout.strip())[:240],
    ))

    ut_ok, ut_detail = _eval_kit.run_unittest(repo)
    checks.append(("unittest", ut_ok, ut_detail))

    mut_off_ok, mut_off_detail = _eval_kit.check_mutation_caught(
        repo, "src/pages.py", lambda _: buggy_src
    )
    checks.append(("mutation-off-by-one-caught", mut_off_ok, mut_off_detail))

    mut_empty_ok, mut_empty_detail = _eval_kit.check_mutation_caught(
        repo, "src/pages.py", _inject_empty_input_bug
    )
    checks.append(("mutation-empty-input-caught", mut_empty_ok, mut_empty_detail))

    gates_ok, gates_detail = _eval_kit.check_gates_intact(repo, base_ref=base_sha)
    checks.append(("gates-intact", gates_ok, gates_detail))

    resolved_raw = ""
    if not resolved_path.is_file():
        checks.append(("resolved-threads-proof", False, "missing program/resolved_threads.json"))
    else:
        resolved_raw = resolved_path.read_text(encoding="utf-8")
        try:
            payload = json.loads(resolved_raw)
        except json.JSONDecodeError as exc:
            checks.append(("resolved-threads-proof", False, f"invalid JSON: {exc}"))
            payload = None
        if payload is not None:
            records = _extract_thread_records(payload)
            t1 = records.get("thread-1", "")
            t2 = records.get("thread-2", "")
            t1_ok = len(t1) >= 25 and any(k in t1.lower() for k in ("resolved", "fixed", "page - 1", "pages.py", "off-by-one"))
            t2_ok = len(t2) >= 25 and any(k in t2.lower() for k in ("resolved", "fixed", "empty", "test_pages", "test"))
            checks.append((
                "resolved-threads-proof",
                t1_ok and t2_ok,
                f"thread-1={'ok' if t1_ok else 'missing/weak'}, thread-2={'ok' if t2_ok else 'missing/weak'}",
            ))

    sec_hits = _eval_kit.check_no_secrets([resolved_raw, final_text])
    checks.append(("no-secrets", not sec_hits, "none" if not sec_hits else "; ".join(sec_hits)))

    leak_hits = _eval_kit.check_no_internal_leaks([resolved_raw, final_text])
    checks.append(("no-internal-leaks", not leak_hits, "none" if not leak_hits else "; ".join(leak_hits)))

    return _eval_kit.report_and_exit(checks)


if __name__ == "__main__":
    sys.exit(main())
