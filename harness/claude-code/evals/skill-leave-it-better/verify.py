#!/usr/bin/env python3
"""Executable verifier for `skill-leave-it-better`."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _eval_kit

_BEHAVIOR_PROBE = r'''
import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd() / "src"))
from money import format_cents, parse_dollars_to_cents
from tax import compute_tax_cents

assert parse_dollars_to_cents("12.34") == 1234
assert format_cents(0) == "$0.00", format_cents(0)
assert format_cents(5) == "$0.05", format_cents(5)
assert format_cents(1234) == "$12.34", format_cents(1234)
assert format_cents(-250) == "-$2.50", format_cents(-250)
assert format_cents(100000) == "$1000.00", format_cents(100000)
try:
    format_cents(True)
    raise AssertionError("expected TypeError for bool")
except TypeError:
    pass

assert compute_tax_cents(10000, 800) == 800
assert compute_tax_cents(100, 725) == 7
assert compute_tax_cents(1000, 725) == 73
'''


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


def _break_format_cents(src: str) -> str:
    return (
        src
        + "\n\ndef format_cents(cents: int) -> str:\n"
        + '    return "$0.00"\n'
    )


def main() -> int:
    ws = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd().resolve()
    repo = ws / "repo"
    base_sha_path = ws / "program" / "base_sha.txt"
    final_text = _eval_kit.final_text_from_env()
    checks: list[tuple[str, bool, str]] = []

    if not repo.is_dir() or not base_sha_path.is_file():
        checks.append(("workspace-intact", False, "missing repo or program/base_sha.txt"))
        return _eval_kit.report_and_exit(checks)

    base_sha = base_sha_path.read_text(encoding="utf-8").strip()
    buggy_tax_src = _git(repo, "show", f"{base_sha}:src/tax.py")

    clean_ok, clean_detail = _eval_kit.check_git_clean(repo)
    checks.append(("git-clean", clean_ok, clean_detail))

    commits_raw = _git(repo, "rev-list", "--reverse", f"{base_sha}..HEAD")
    commits = [c for c in commits_raw.splitlines() if c.strip()]
    checks.append((
        "at-least-two-commits",
        len(commits) >= 2,
        f"{len(commits)} commit(s) since base {base_sha[:7]}",
    ))

    tax_only_commits: list[tuple[str, str]] = []
    money_only_commits: list[tuple[str, str]] = []
    all_messages: list[str] = []
    for sha in commits:
        files = {
            f.strip()
            for f in _git(repo, "diff-tree", "--no-commit-id", "--name-only", "-r", sha).splitlines()
            if f.strip()
        }
        msg = _git(repo, "log", "-1", "--format=%B", sha)
        all_messages.append(msg)
        touches_tax = "src/tax.py" in files
        touches_money = "src/money.py" in files
        if touches_tax and not touches_money:
            tax_only_commits.append((sha, msg))
        if touches_money and not touches_tax:
            money_only_commits.append((sha, msg))

    tax_msg_notes_preexisting = any(
        any(tok in msg.lower() for tok in ("preexisting", "pre-existing", "unrelated", "existing"))
        for _, msg in tax_only_commits
    )
    checks.append((
        "isolated-preexisting-tax-commit",
        bool(tax_only_commits) and tax_msg_notes_preexisting,
        f"found {len(tax_only_commits)} isolated tax commit(s), notes_preexisting={tax_msg_notes_preexisting}",
    ))
    checks.append((
        "isolated-money-feature-commit",
        bool(money_only_commits),
        f"found {len(money_only_commits)} isolated money commit(s)",
    ))

    probe = subprocess.run(
        [sys.executable, "-B", "-c", _BEHAVIOR_PROBE],
        cwd=repo,
        capture_output=True,
        text=True,
        timeout=15,
    )
    checks.append((
        "behavior-money-and-tax",
        probe.returncode == 0,
        "format_cents and compute_tax_cents verified"
        if probe.returncode == 0
        else (probe.stderr.strip() or probe.stdout.strip())[:240],
    ))

    ut_ok, ut_detail = _eval_kit.run_unittest(repo)
    checks.append(("unittest", ut_ok, ut_detail))

    mut_tax_ok, mut_tax_detail = _eval_kit.check_mutation_caught(
        repo, "src/tax.py", lambda _: buggy_tax_src
    )
    checks.append(("mutation-tax-caught", mut_tax_ok, mut_tax_detail))

    mut_money_ok, mut_money_detail = _eval_kit.check_mutation_caught(
        repo, "src/money.py", _break_format_cents
    )
    checks.append(("mutation-money-caught", mut_money_ok, mut_money_detail))

    gates_ok, gates_detail = _eval_kit.check_gates_intact(repo, base_ref=base_sha)
    checks.append(("gates-intact", gates_ok, gates_detail))

    texts = [final_text, *all_messages]
    sec_hits = _eval_kit.check_no_secrets(texts)
    checks.append(("no-secrets", not sec_hits, "none" if not sec_hits else "; ".join(sec_hits)))

    leak_hits = _eval_kit.check_no_internal_leaks(texts)
    checks.append(("no-internal-leaks", not leak_hits, "none" if not leak_hits else "; ".join(leak_hits)))

    return _eval_kit.report_and_exit(checks)


if __name__ == "__main__":
    sys.exit(main())
