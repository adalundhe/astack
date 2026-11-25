#!/usr/bin/env python3
"""Objective post-run workspace verifier: ensures repo/ was never modified."""
import subprocess
import sys
from pathlib import Path


def main() -> int:
    ws = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    repo = ws / "repo"
    status = subprocess.run(["git", "-C", str(repo), "status", "--porcelain"], capture_output=True, text=True)
    if status.returncode != 0 or status.stdout.strip():
        print(f"FAIL: repo modified: {status.stdout.strip()}", file=sys.stderr)
        return 1
    expected = (ws / "program" / "head_sha.txt").read_text().strip()
    actual = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    if actual != expected:
        print(f"FAIL: HEAD moved ({expected} -> {actual})", file=sys.stderr)
        return 1
    print("PASS: repo clean and untouched")
    return 0


if __name__ == "__main__":
    sys.exit(main())
