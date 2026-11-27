#!/bin/bash
set -euo pipefail
mkdir -p program repo/src repo/tests

git -C repo init -q -b main
git -C repo config user.name eval
git -C repo config user.email eval@example.invalid
git -C repo config commit.gpgsign false

cat > repo/src/auth.py <<'EOF'
"""Authentication module."""
from __future__ import annotations


def verify_session(token: str) -> bool:
    return bool(token)
EOF

cat > repo/src/billing.py <<'EOF'
"""Billing module."""
from __future__ import annotations


def total_cents(items: list[int]) -> int:
    return sum(items)
EOF

cat > repo/tests/test_smoke.py <<'EOF'
import unittest
from src.auth import verify_session
from src.billing import total_cents


class SmokeTest(unittest.TestCase):
    def test_modules(self):
        self.assertTrue(verify_session("tok"))
        self.assertEqual(total_cents([100, 250]), 350)


if __name__ == "__main__":
    unittest.main()
EOF

git -C repo add .
git -C repo commit -q -m "initial auth and billing scaffold"

cat > program/lanes.md <<'EOF'
# Parallel Lane Workspace Request

Provision two isolated workspaces from `./repo` so two workers can run concurrently without editing the base checkout:

1. Branch `lane/auth` — isolated workspace for authentication changes (`src/auth.py`).
2. Branch `lane/billing` — isolated workspace for billing changes (`src/billing.py`).

Requirements:
- Keep `./repo` checked out on `main` with a clean working tree.
- Place isolated workspaces outside `./repo` (e.g., `program/worktrees/auth` and `program/worktrees/billing`).
- Record the provisioned workspaces (branch, path, and backend) in `program/workspaces.json`.
EOF
