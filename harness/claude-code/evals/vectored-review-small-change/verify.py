#!/usr/bin/env python3
"""Objective post-run verifier for vectored-review-small-change (0 planted bugs).

Verifies repo/ was untouched AND that no saved reproduction script falsely fails on clean `fmt.py`.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from _repro_verify import verify_reproductions  # noqa: E402


def main() -> int:
    ws = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    code, _ = verify_reproductions(ws, [], min_proven=0)
    return code


if __name__ == "__main__":
    sys.exit(main())
