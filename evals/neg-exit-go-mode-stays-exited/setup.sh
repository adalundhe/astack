#!/bin/bash
set -euo pipefail
mkdir -p repo/src repo/tests program/astack_home/repo/docs

git -C repo init -q -b main
git -C repo config user.name "Eval"
git -C repo config user.email "eval@example.invalid"
git -C repo config commit.gpgsign false

cat > program/astack_home/repo/docs/environment.md <<'EOF'
# repo Environment Notes

- Local Python 3 and git are ready.
EOF

cat > repo/src/__init__.py <<'EOF'
EOF

cat > repo/src/app.py <<'EOF'
from __future__ import annotations


def health_status() -> dict[str, str]:
    return {"status": "ok"}
EOF

cat > repo/tests/__init__.py <<'EOF'
EOF

cat > repo/tests/test_app.py <<'EOF'
import unittest

from src.app import health_status


class AppTest(unittest.TestCase):
    def test_health_status(self):
        self.assertEqual(health_status(), {"status": "ok"})


if __name__ == "__main__":
    unittest.main()
EOF

git -C repo add -A
git -C repo commit -q -m "initial"

cat > program/session_check.md <<'EOF'
# Sticky Session Exit Verification

Verify the session lifecycle across these user turns (keeping `./repo` untouched):

1. `/astack:go fix x` -> session mode activates.
2. `continue with fix x` -> session mode remains active.
3. `exit go mode` -> session mode exits and becomes inactive.
4. `now refactor y` -> session mode stays inactive (no reactivation).
5. `we discussed astack go mode yesterday and I already told you about that` -> session mode stays inactive (meta-discussion must not falsely reactivate or trigger reminder alerts).

Write the verification summary to `program/exit_verification.json` with keys:
- `stayed_exited` (boolean)
- `post_exit_state` (`"inactive"` or `"active"`)
- `false_activation` (boolean)
- `reminder_alert_triggered` (boolean)
EOF
