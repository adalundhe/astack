#!/usr/bin/env python3
"""Objective post-run verifier: final-comment.md exists, is clean of leaked internals, and repo/ is untouched."""
import re
import subprocess
import sys
from pathlib import Path


def main() -> int:
    ws = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    repo = ws / "repo"
    final_path = ws / "program" / "final-comment.md"
    if not final_path.is_file():
        print("FAIL: program/final-comment.md was not written", file=sys.stderr)
        return 1
    body = final_path.read_text(encoding="utf-8").strip()
    if len(body) < 40:
        print("FAIL: program/final-comment.md is empty or too short", file=sys.stderr)
        return 1
    leaked = re.search(r"(POOL EXHAUSTED|coverage-map\.md|jackknife|sonnet/haiku|\bP[0-5]\b)", body, re.I)
    if leaked:
        print(f"FAIL: leaked internal term in final-comment.md: {leaked.group(0)!r}", file=sys.stderr)
        return 1
    status = subprocess.run(["git", "-C", str(repo), "status", "--porcelain"], capture_output=True, text=True)
    if status.returncode != 0 or status.stdout.strip():
        print(f"FAIL: repo working tree modified: {status.stdout.strip()}", file=sys.stderr)
        return 1
    head_file = ws / "program" / "head_sha.txt"
    if head_file.is_file():
        expected = head_file.read_text().strip()
        actual = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
        if actual != expected:
            print(f"FAIL: repo HEAD moved ({expected} -> {actual})", file=sys.stderr)
            return 1
    print("PASS: final-comment.md clean and repo untouched")
    return 0


if __name__ == "__main__":
    sys.exit(main())
