#!/bin/bash
set -euo pipefail
mkdir -p program repo/src repo/tests

git -C repo init -q -b main
git -C repo config user.name eval
git -C repo config user.email eval@example.invalid
git -C repo config commit.gpgsign false

cat > repo/src/token.py <<'EOF'
"""HMAC token verifier."""
from __future__ import annotations


def is_token_valid(expires_at: int, now: int) -> bool:
    return True
EOF

cat > repo/src/export.py <<'EOF'
"""CSV export helper."""
from __future__ import annotations


def format_csv_row(fields: list[str]) -> str:
    # Bug (#102): does not quote fields containing embedded commas
    return ",".join(fields)
EOF

cat > repo/src/metrics.py <<'EOF'
"""Latency histogram metrics (work in progress for #103)."""
from __future__ import annotations


def record_latency_ms(value: int) -> None:
    pass
EOF

cat > repo/tests/test_token.py <<'EOF'
import unittest
from src.token import is_token_valid


class TokenTest(unittest.TestCase):
    def test_rejects_expired_token(self):
        self.assertTrue(is_token_valid(expires_at=200, now=150))
        self.assertFalse(is_token_valid(expires_at=100, now=150))


if __name__ == "__main__":
    unittest.main()
EOF

cat > repo/tests/test_export.py <<'EOF'
import unittest
from src.export import format_csv_row


class ExportTest(unittest.TestCase):
    def test_quotes_fields_with_commas(self):
        self.assertEqual(format_csv_row(["Acme, Inc.", "42"]), '"Acme, Inc.",42')


if __name__ == "__main__":
    unittest.main()
EOF

git -C repo add .
git -C repo commit -q -m "initial token, export, and metrics modules"

cat > repo/src/token.py <<'EOF'
"""HMAC token verifier."""
from __future__ import annotations


def is_token_valid(expires_at: int, now: int) -> bool:
    return now < expires_at
EOF

git -C repo add src/token.py
git -C repo commit -q -m "feat(#101): enforce HMAC token expiry check"

cat > program/LANES.md <<'EOF'
# Active Program Lanes (Epic #100)

- **#101 — Enforce HMAC token expiry check:** Landed on `main` in `./repo`; `python3 -m unittest tests/test_token.py` passes. Ready to close with commit proof.
- **#102 — Escape embedded commas in CSV export:** Blocked. `python3 -m unittest tests/test_export.py` currently fails on embedded comma quoting, and implementation is waiting on upstream RFC-4180 quoting policy decision in `#98`. Keep open and mark blocked.
- **#103 — Add latency histogram metrics:** Currently in progress; worker lane active. Keep open.
EOF

cat > program/issues.json <<'EOF'
{
  "tracker": "local-mirror",
  "epic": "#100",
  "issues": [
    {
      "id": "#101",
      "title": "Enforce HMAC token expiry check",
      "status": "open",
      "state": "in_progress",
      "proof_sha": null,
      "notes": []
    },
    {
      "id": "#102",
      "title": "Escape embedded commas in CSV export",
      "status": "open",
      "state": "in_progress",
      "blocked_by": [],
      "notes": []
    },
    {
      "id": "#103",
      "title": "Add latency histogram metrics",
      "status": "open",
      "state": "in_progress",
      "notes": []
    }
  ]
}
EOF
