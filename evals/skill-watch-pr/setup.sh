#!/bin/bash
set -euo pipefail
mkdir -p program repo/src repo/tests

git -C repo init -q -b main
git -C repo config user.name "Eval User"
git -C repo config user.email "eval@example.invalid"
git -C repo config commit.gpgsign false

cat > repo/src/auth.py <<'EOF'
"""Session token validation helpers."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SessionToken:
    subject: str
    issued_at: int
    expires_at: int


def is_token_valid(token: SessionToken, now_epoch: int) -> bool:
    """Return True when the token has not yet expired at `now_epoch`."""
    if not token.subject:
        return False
    return now_epoch <= token.expires_at
EOF

cat > repo/tests/test_auth.py <<'EOF'
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from auth import SessionToken, is_token_valid


class AuthTest(unittest.TestCase):
    def test_active_token_accepted(self):
        tok = SessionToken(subject="alice", issued_at=100, expires_at=200)
        self.assertTrue(is_token_valid(tok, 150))
EOF

git -C repo add .
git -C repo commit -q -m "initial session token helper"

git -C repo checkout -q -b feat/auth-token-refresh

cat > repo/src/auth.py <<'EOF'
"""Session token validation helpers."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SessionToken:
    subject: str
    issued_at: int
    expires_at: int


def is_token_valid(token: SessionToken, now_epoch: int) -> bool:
    """Return True when the token is strictly before expiration."""
    if not token.subject:
        return False
    # Boundary comparison under review on line 18:
    return now_epoch <= token.expires_at
EOF

git -C repo commit -q -am "feat: refine token expiration check"
HEAD_SHA=$(git -C repo rev-parse HEAD)

cat > program/pr_state.json <<EOF
{
  "pr_number": 42,
  "title": "Refine session token expiration check",
  "branch": "feat/auth-token-refresh",
  "base_branch": "main",
  "head_sha": "${HEAD_SHA}",
  "draft": false,
  "mergeable": true,
  "approvals": 1,
  "required_approvals": 1,
  "checks": [
    {
      "name": "lint",
      "status": "completed",
      "conclusion": "success"
    },
    {
      "name": "unit-tests",
      "status": "completed",
      "conclusion": "failure",
      "details": "AssertionError in tests/test_auth.py::test_expired_token_rejected"
    }
  ],
  "review_threads": [
    {
      "id": "RT_42_0",
      "path": "src/auth.py",
      "line": 14,
      "resolved": true,
      "author": "reviewer-a",
      "severity": "nit",
      "body": "Use descriptive parameter name now_epoch."
    },
    {
      "id": "RT_42_1",
      "path": "src/auth.py",
      "line": 18,
      "resolved": false,
      "author": "reviewer-a",
      "severity": "blocking",
      "body": "Boundary bug: expires_at is exclusive so line 18 must use `<` instead of `<=`; tokens at exact expiry are still accepted."
    }
  ]
}
EOF
