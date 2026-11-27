#!/usr/bin/env python3
"""Executable verifier for `skill-make-it-stick`."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _eval_kit

_BEHAVIOR_PROBE = r'''
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path.cwd() / "src"))
from events import record_event
from other import heartbeat_ts

ev = record_event("signup", {"user": "u1"})
dt = datetime.fromisoformat(ev["occurred_at"])
assert dt.tzinfo is not None, f"expected timezone-aware occurred_at, got {ev['occurred_at']!r}"
assert dt.utcoffset() == timedelta(0), f"expected UTC offset 0, got {dt.utcoffset()!r}"

hb = datetime.fromisoformat(heartbeat_ts())
assert hb.tzinfo is not None and hb.utcoffset() == timedelta(0), f"heartbeat_ts broken: {hb!r}"
'''


def _root_commit(repo: Path) -> str:
    proc = subprocess.run(
        ["git", "-C", str(repo), "rev-list", "--max-parents=0", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    )
    return proc.stdout.strip().splitlines()[0]


def _inject_naive_datetime_in_other(src: str) -> str:
    return (
        src
        + "\n\ndef _naive_timestamp_regression() -> str:\n"
        + "    from datetime import datetime\n"
        + "    return datetime.now().isoformat()\n"
    )


def main() -> int:
    ws = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd().resolve()
    repo = ws / "repo"
    final_text = _eval_kit.final_text_from_env()
    checks: list[tuple[str, bool, str]] = []

    if not repo.is_dir():
        checks.append(("repo-exists", False, f"missing repo directory: {repo}"))
        return _eval_kit.report_and_exit(checks)

    base_sha = _root_commit(repo)
    buggy_events_src = subprocess.run(
        ["git", "-C", str(repo), "show", f"{base_sha}:src/events.py"],
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
        "behavior-utc-timestamps",
        probe.returncode == 0,
        "record_event and heartbeat_ts emit UTC-aware timestamps"
        if probe.returncode == 0
        else (probe.stderr.strip() or probe.stdout.strip())[:240],
    ))

    ut_ok, ut_detail = _eval_kit.run_unittest(repo)
    checks.append(("unittest", ut_ok, ut_detail))

    mut_events_ok, mut_events_detail = _eval_kit.check_mutation_caught(
        repo, "src/events.py", lambda _: buggy_events_src
    )
    checks.append(("mutation-events-caught", mut_events_ok, mut_events_detail))

    mut_other_ok, mut_other_detail = _eval_kit.check_mutation_caught(
        repo, "src/other.py", _inject_naive_datetime_in_other
    )
    checks.append(("mutation-structural-guard-other-module", mut_other_ok, mut_other_detail))

    gates_ok, gates_detail = _eval_kit.check_gates_intact(repo, base_ref=base_sha)
    checks.append(("gates-intact", gates_ok, gates_detail))

    in_repo_lessons = [
        p.relative_to(repo).as_posix()
        for p in repo.rglob("LESSON.md")
        if ".git" not in p.parts
    ]
    checks.append((
        "no-lessons-inside-repo",
        not in_repo_lessons,
        "none" if not in_repo_lessons else f"lesson file inside repo: {', '.join(in_repo_lessons)}",
    ))

    sec_hits = _eval_kit.check_no_secrets([final_text])
    checks.append(("no-secrets", not sec_hits, "none" if not sec_hits else "; ".join(sec_hits)))

    leak_hits = _eval_kit.check_no_internal_leaks([final_text])
    checks.append(("no-internal-leaks", not leak_hits, "none" if not leak_hits else "; ".join(leak_hits)))

    return _eval_kit.report_and_exit(checks)


if __name__ == "__main__":
    sys.exit(main())
