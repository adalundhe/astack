#!/usr/bin/env python3
"""Objective post-run workspace verifier for vectored-review evals: ensures repo/ was never modified."""
import subprocess
import sys
from pathlib import Path


def main() -> int:
    ws = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    repo = ws / "repo"
    if not (repo / ".git").exists():
        print("missing repo/.git", file=sys.stderr)
        return 1
    status = subprocess.run(["git", "-C", str(repo), "status", "--porcelain"], capture_output=True, text=True)
    if status.returncode != 0 or status.stdout.strip():
        print(f"review modified repo working tree: {status.stdout.strip()}", file=sys.stderr)
        return 1
    head_file = ws / "program" / "head_sha.txt"
    if head_file.is_file():
        expected = head_file.read_text().strip()
        actual = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
        if actual != expected:
            print(f"review moved repo HEAD from {expected} to {actual}", file=sys.stderr)
            return 1
    print("repo clean and untouched")
    return 0


if __name__ == "__main__":
    sys.exit(main())
