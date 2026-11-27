#!/usr/bin/env python3
"""Verifier for rule-comment-cop."""
from __future__ import annotations

import io
import re
import subprocess
import sys
import tokenize
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _eval_kit as kit


BANNED_COMMENT_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("ASCII banner", re.compile(r"={4,}|-{4,}")),
    ("narrating bucket init", re.compile(r"initialize the buckets", re.I)),
    ("narrating loop", re.compile(r"loop over timestamps", re.I)),
    ("narrating counter", re.compile(r"increment request counter|counter for total allowed", re.I)),
    ("narrating return", re.compile(r"return (?:true|false|the pruned)", re.I)),
    ("narrating config check", re.compile(r"check that (?:max_requests|window_seconds)|store configuration", re.I)),
    ("change history", re.compile(r"OPS-991|used to use list\.pop", re.I)),
    ("commented-out code", re.compile(r"old_limit\s*=|if\s+len\(bucket\)", re.I)),
)


def _extract_comments(source: str) -> list[str]:
    comments: list[str] = []
    for tok in tokenize.generate_tokens(io.StringIO(source).readline):
        if tok.type == tokenize.COMMENT:
            comments.append(tok.string)
    return comments


def _base_ref(ws: Path, repo: Path) -> str:
    sha_file = ws / "program" / "base_sha.txt"
    if not sha_file.is_file():
        return "HEAD"
    base = sha_file.read_text(encoding="utf-8").strip()
    cur = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True, text=True)
    if cur.returncode == 0 and cur.stdout.strip() != base:
        return base
    return "HEAD"


def _audit_comments(source: str) -> tuple[bool, str]:
    comments = _extract_comments(source)
    joined = "\n".join(comments)

    if "SPDX-License-Identifier: MIT" not in joined or "Copyright" not in joined:
        return False, "missing required SPDX/Copyright license header comment"
    if not (("RFC 6585" in joined or "4182" in joined) and ("Envoy" in joined or "Retry-After" in joined)):
        return False, "missing required external RFC 6585 / Envoy Retry-After constraint comment"

    banned_hits: list[str] = []
    for label, rx in BANNED_COMMENT_PATTERNS:
        if rx.search(joined):
            banned_hits.append(label)
    if banned_hits:
        return False, f"narrating/stale comments remain: {', '.join(banned_hits)}"
    if len(comments) > 6:
        return False, f"too many # comment lines remain ({len(comments)} > 6): {comments}"
    return True, f"kept {len(comments)} essential comment lines (license + external constraint), stripped narrating comments"


def main() -> int:
    ws = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    repo = ws / "repo"
    target = repo / "src" / "rate_limiter.py"
    checks: list[tuple[str, bool, str]] = []

    if not target.is_file():
        checks.append(("rate_limiter_exists", False, "src/rate_limiter.py missing"))
        return kit.report_and_exit(checks)

    src_text = target.read_text(encoding="utf-8")
    ok_comments, msg_comments = _audit_comments(src_text)
    checks.append(("comment_hygiene", ok_comments, msg_comments))

    # Strict invariant check: re-injecting a narrating comment must trip the comment audit
    re_injected = src_text + "\n# Increment request counter\n"
    ok_reinj, _ = _audit_comments(re_injected)
    checks.append((
        "comment_regression_detected",
        not ok_reinj,
        "re-injected narrating comment rejected by audit" if not ok_reinj else "audit failed to catch narrating comment",
    ))

    # Runtime behavioral verification
    probe = subprocess.run(
        [
            sys.executable, "-B", "-c",
            "import sys; sys.path.insert(0, 'src'); "
            "from rate_limiter import SlidingWindowLimiter; "
            "lim = SlidingWindowLimiter(2, 10.0); "
            "assert lim.allow('a', 1.0) is True; "
            "assert lim.allow('a', 2.0) is True; "
            "assert lim.allow('a', 3.0) is False; "
            "assert lim.retry_after_seconds('a', 9.2) == 2; "
            "assert lim.retry_after_seconds('a', 11.0) == 0; "
            "print('behavior-ok')",
        ],
        cwd=repo,
        capture_output=True,
        text=True,
    )
    checks.append((
        "runtime_behavior",
        probe.returncode == 0 and "behavior-ok" in probe.stdout,
        probe.stdout.strip() or probe.stderr.strip(),
    ))

    ok_ut, msg_ut = kit.run_unittest(repo)
    checks.append(("unittest", ok_ut, msg_ut))

    ok_mut, msg_mut = kit.check_mutation_caught(
        repo,
        "src/rate_limiter.py",
        lambda s: s + "\nSlidingWindowLimiter.retry_after_seconds = lambda self, key, now: 0\n",
    )
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
