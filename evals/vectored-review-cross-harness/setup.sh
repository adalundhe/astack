#!/bin/bash
set -euo pipefail
mkdir -p program/repros repo
if [ -n "${ASTACK_EVAL_SETTINGS_JSON:-}" ]; then
  printf '%s\n' "$ASTACK_EVAL_SETTINGS_JSON" > program/settings.json
else
CODEX_MODEL="default"
if [ -f "${CODEX_HOME:-$HOME/.codex}/config.toml" ]; then
  DETECTED=$(sed -n 's/^[[:space:]]*model[[:space:]]*=[[:space:]]*"\([^"]*\)".*/\1/p' "${CODEX_HOME:-$HOME/.codex}/config.toml" | head -n 1)
  if [ -n "$DETECTED" ]; then
    CODEX_MODEL="$DETECTED"
  fi
fi
cat > program/settings.json <<EOF
{
  "roles": {
    "worker": {"provider": "anthropic", "model": "haiku", "effort": "medium"}
  },
  "reviewer_pool": [
    {"provider": "anthropic", "model": "sonnet", "effort": "medium", "harness": "claude"},
    {"provider": "openai", "model": "$CODEX_MODEL", "effort": "medium", "harness": "codex"}
  ]
}
EOF
fi

git -C repo init -q -b main
git -C repo config user.name eval
git -C repo config user.email eval@example.invalid
git -C repo config commit.gpgsign false
cat > repo/auth.py <<'EOF'
from __future__ import annotations

import hashlib
import hmac
import time


def sign_token(secret: bytes, subject: str, expires_at: int) -> str:
    payload = f"{subject}:{expires_at}"
    sig = hmac.new(secret, payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}:{sig}"


def verify_token(secret: bytes, token: str, now: int | None = None) -> str | None:
    parts = token.split(":")
    if len(parts) != 3:
        return None
    subject, exp_raw, sig = parts
    try:
        expires_at = int(exp_raw)
    except ValueError:
        return None
    now_ts = int(time.time()) if now is None else now
    if expires_at <= now_ts:
        return None
    expected = hmac.new(secret, f"{subject}:{expires_at}".encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, sig):
        return None
    return subject
EOF
git -C repo add auth.py
git -C repo commit -q -m "initial signed session token verifier"

git -C repo checkout -q -b lane/token-refresh
cat > repo/auth.py <<'EOF'
from __future__ import annotations

import hashlib
import hmac
import time


def sign_token(secret: bytes, subject: str, expires_at: int, refreshed: bool = False) -> str:
    tag = "r" if refreshed else "i"
    payload = f"{subject}:{expires_at}:{tag}"
    sig = hmac.new(secret, payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}:{sig}"


def verify_token(secret: bytes, token: str, now: int | None = None) -> str | None:
    parts = token.split(":")
    if len(parts) != 4:
        return None
    subject, exp_raw, tag, sig = parts
    try:
        expires_at = int(exp_raw)
    except ValueError:
        return None
    now_ts = int(time.time()) if now is None else now
    if tag != "r" and expires_at <= now_ts:
        return None
    expected = hmac.new(secret, f"{subject}:{expires_at}:{tag}".encode(), hashlib.sha256).hexdigest()
    if expected != sig:
        return None
    return subject
EOF
git -C repo add auth.py
git -C repo commit -q -m "add refreshed token tag to session token verifier"
git -C repo diff main..lane/token-refresh > program/change.diff
mkdir -p program/base
git -C repo show main:auth.py > program/base/auth.py
