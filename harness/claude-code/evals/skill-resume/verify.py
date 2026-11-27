#!/usr/bin/env python3
"""Executable verifier for `skill-resume`."""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _eval_kit

_STAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}Z (?P<rest>.+)$")

_BEHAVIOR_PROBE = r'''
import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd() / "src"))
from sync import TransientSyncError, checkpoint_offset, sync_batch

# Step 1 preserved
assert checkpoint_offset(10, 5) == 15
try:
    checkpoint_offset(-1, 1)
    raise AssertionError("expected ValueError for negative offset")
except ValueError:
    pass

# Step 2: negative max_retries rejected
try:
    sync_batch(lambda x: x, [1], max_retries=-1)
    raise AssertionError("expected ValueError for max_retries=-1")
except ValueError:
    pass

# Step 2: succeeds within retry cap (2 failures + 1 success = 3 attempts with max_retries=2)
attempts = []
def flaky_ok(item):
    attempts.append(item)
    if len(attempts) <= 2:
        raise TransientSyncError("temporary glitch")
    return item * 10

assert sync_batch(flaky_ok, [3], max_retries=2) == [30]
assert len(attempts) == 3, f"expected 3 attempts, got {len(attempts)}"

# Step 2: stops at 1 + max_retries when always failing
always_calls = []
def always_fail(item):
    always_calls.append(item)
    raise TransientSyncError("still failing")

try:
    sync_batch(always_fail, [9], max_retries=2)
    raise AssertionError("expected TransientSyncError")
except TransientSyncError:
    pass
assert len(always_calls) == 3, f"expected 3 attempts (1 + 2 retries), got {len(always_calls)}"

# Step 2: max_retries=0 means exactly 1 attempt
zero_calls = []
def fail_once(item):
    zero_calls.append(item)
    raise TransientSyncError("fail immediately")

try:
    sync_batch(fail_once, [7], max_retries=0)
    raise AssertionError("expected TransientSyncError for max_retries=0")
except TransientSyncError:
    pass
assert len(zero_calls) == 1, f"expected 1 attempt for max_retries=0, got {len(zero_calls)}"
'''


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


def _log_lines(lanes_text: str) -> tuple[list[str], list[str]]:
    stamped: list[str] = []
    unstamped: list[str] = []
    in_log = False
    for line in lanes_text.splitlines():
        if line.startswith("## "):
            in_log = line.strip() == "## Log"
            continue
        if not in_log or not line.strip():
            continue
        if _STAMP_RE.match(line):
            stamped.append(line)
        else:
            unstamped.append(line)
    return stamped, unstamped


def main() -> int:
    ws = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd().resolve()
    repo = ws / "repo"
    sha_path = ws / "program" / "step1_sha.txt"
    lanes_path = ws / "program" / "LANES.md"
    final_text = _eval_kit.final_text_from_env()
    checks: list[tuple[str, bool, str]] = []

    if not repo.is_dir() or not sha_path.is_file() or not lanes_path.is_file():
        checks.append(("workspace-intact", False, "missing repo, step1_sha.txt, or LANES.md"))
        return _eval_kit.report_and_exit(checks)

    step1_sha = sha_path.read_text(encoding="utf-8").strip()
    step1_sync_src = _git(repo, "show", f"{step1_sha}:src/sync.py")

    branch = _git(repo, "rev-parse", "--abbrev-ref", "HEAD")
    checks.append(("branch-lane-sync", branch == "lane/sync", f"branch={branch}"))

    probe = subprocess.run(
        [sys.executable, "-B", "-c", _BEHAVIOR_PROBE],
        cwd=repo,
        capture_output=True,
        text=True,
        timeout=15,
    )
    checks.append((
        "behavior-step1-and-step2",
        probe.returncode == 0,
        "step 1 intact and step 2 retry cap verified"
        if probe.returncode == 0
        else (probe.stderr.strip() or probe.stdout.strip())[:240],
    ))

    ut_ok, ut_detail = _eval_kit.run_unittest(repo)
    checks.append(("unittest", ut_ok, ut_detail))

    mut_ok, mut_detail = _eval_kit.check_mutation_caught(
        repo, "src/sync.py", lambda _: step1_sync_src
    )
    checks.append(("mutation-retry-cap-caught", mut_ok, mut_detail))

    gates_ok, gates_detail = _eval_kit.check_gates_intact(repo, base_ref=step1_sha)
    checks.append(("gates-intact", gates_ok, gates_detail))

    lanes_text = lanes_path.read_text(encoding="utf-8")
    has_marker = lanes_text.startswith("<!-- astack lane log -->")
    stamped, unstamped = _log_lines(lanes_text)
    has_prior = any("paused w1 on lane/sync" in ln for ln in stamped)
    has_resume_entry = any(
        "resum" in ln.lower() and "paused w1 on lane/sync" not in ln
        for ln in stamped
    )
    lanes_ok = has_marker and has_prior and has_resume_entry and (len(unstamped) == 0)
    checks.append((
        "lanes-resumption-logged",
        lanes_ok,
        f"marker={has_marker}, prior={has_prior}, resume_entry={has_resume_entry}, unstamped={len(unstamped)}",
    ))

    texts = [lanes_text, final_text]
    sec_hits = _eval_kit.check_no_secrets(texts)
    checks.append(("no-secrets", not sec_hits, "none" if not sec_hits else "; ".join(sec_hits)))

    leak_hits = _eval_kit.check_no_internal_leaks(texts)
    checks.append(("no-internal-leaks", not leak_hits, "none" if not leak_hits else "; ".join(leak_hits)))

    return _eval_kit.report_and_exit(checks)


if __name__ == "__main__":
    sys.exit(main())
