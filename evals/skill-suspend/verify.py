#!/usr/bin/env python3
"""Executable verifier for `skill-suspend`."""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _eval_kit

_STAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}Z (?P<rest>.+)$")


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
    pre_sha_path = ws / "program" / "pre_suspend_sha.txt"
    lanes_path = ws / "program" / "LANES.md"
    suspended_path = ws / "program" / "SUSPENDED.md"
    final_text = _eval_kit.final_text_from_env()
    checks: list[tuple[str, bool, str]] = []

    if not repo.is_dir() or not pre_sha_path.is_file() or not lanes_path.is_file():
        checks.append(("workspace-intact", False, "missing repo, pre_suspend_sha.txt, or LANES.md"))
        return _eval_kit.report_and_exit(checks)

    pre_sha = pre_sha_path.read_text(encoding="utf-8").strip()

    branch = _git(repo, "rev-parse", "--abbrev-ref", "HEAD")
    checks.append(("branch-lane-sync", branch == "lane/sync", f"branch={branch}"))

    clean_ok, clean_detail = _eval_kit.check_git_clean(repo)
    checks.append(("git-clean", clean_ok, clean_detail))

    head_sha = _git(repo, "rev-parse", "HEAD")
    short_sha = head_sha[:7]
    committed_wip = head_sha != pre_sha
    sync_src = (repo / "src" / "sync.py").read_text(encoding="utf-8")
    wip_preserved = committed_wip and ("def checkpoint_offset" in sync_src)
    checks.append((
        "wip-committed-and-preserved",
        wip_preserved,
        f"WIP committed at {short_sha} with checkpoint_offset intact"
        if wip_preserved
        else f"HEAD={short_sha} (pre={pre_sha[:7]}), has_checkpoint_offset={'def checkpoint_offset' in sync_src}",
    ))

    ut_ok, ut_detail = _eval_kit.run_unittest(repo)
    checks.append(("unittest", ut_ok, ut_detail))

    gates_ok, gates_detail = _eval_kit.check_gates_intact(repo, base_ref=pre_sha)
    checks.append(("gates-intact", gates_ok, gates_detail))

    lanes_text = lanes_path.read_text(encoding="utf-8")
    has_marker = lanes_text.startswith("<!-- astack lane log -->")
    stamped, unstamped = _log_lines(lanes_text)
    has_original = any("started w1 on lane/sync" in ln for ln in stamped)
    has_pause_line = any(
        any(tok in ln.lower() for tok in ("paus", "suspend"))
        and any(tok in ln.lower() for tok in ("lane/sync", "w1"))
        and "started w1" not in ln
        for ln in stamped
    )
    lanes_ok = has_marker and has_original and has_pause_line and (len(unstamped) == 0)
    checks.append((
        "lanes-pause-entry",
        lanes_ok,
        f"marker={has_marker}, original={has_original}, pause_entry={has_pause_line}, unstamped={len(unstamped)}",
    ))

    suspended_text = ""
    if not suspended_path.is_file():
        checks.append(("suspended-md", False, "missing program/SUSPENDED.md"))
    else:
        suspended_text = suspended_path.read_text(encoding="utf-8")
        low = suspended_text.lower()
        has_branch = "lane/sync" in suspended_text
        has_sha = (head_sha in suspended_text) or (short_sha in suspended_text)
        has_resume_cmd = (
            any(tok in low for tok in ("git checkout lane/sync", "git switch lane/sync", "git -c", "unittest"))
            and ("resume" in low or "checkout" in low or "switch" in low)
        )
        susp_ok = has_branch and has_sha and has_resume_cmd
        checks.append((
            "suspended-md",
            susp_ok,
            f"branch={has_branch}, sha({short_sha})={has_sha}, resume_cmd={has_resume_cmd}",
        ))

    texts = [lanes_text, suspended_text, final_text]
    sec_hits = _eval_kit.check_no_secrets(texts)
    checks.append(("no-secrets", not sec_hits, "none" if not sec_hits else "; ".join(sec_hits)))

    leak_hits = _eval_kit.check_no_internal_leaks(texts)
    checks.append(("no-internal-leaks", not leak_hits, "none" if not leak_hits else "; ".join(leak_hits)))

    return _eval_kit.report_and_exit(checks)


if __name__ == "__main__":
    sys.exit(main())
