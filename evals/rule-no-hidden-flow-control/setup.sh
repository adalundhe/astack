#!/bin/bash
set -euo pipefail
mkdir -p repo/src repo/tests

git -C repo init -q -b main
git -C repo config user.name "Eval"
git -C repo config user.email "eval@example.invalid"
git -C repo config commit.gpgsign false

cat > repo/README.md <<'EOF'
# User Profile Loader

Loads a JSON user profile from disk in `src/profile_loader.py`.

## Public Contract

### `load_user_profile(path: Path)`
Reads a UTF-8 JSON file containing `{"id": <int>, "name": <non-empty str>}`:
- On valid input, returns a typed success object (dataclass / typed value, not bare `dict` or `None`) containing the integer `id` and stripped `name`.
- On expected failures, catches only the narrow exception around the raising call and returns an explicit typed error value (never `None`) distinguishing:
  - Missing file (`FileNotFoundError`)
  - Malformed JSON (`json.JSONDecodeError`)
  - Invalid profile payload (non-object JSON, missing required key `KeyError`, non-integer / boolean `id`, or empty / non-string `name`)
- Must **not** use bare `except:` or `except Exception:`; unexpected errors (such as `RuntimeError`, `PermissionError`, or `KeyboardInterrupt`) must propagate to the caller.
EOF

cat > repo/src/__init__.py <<'EOF'
EOF

cat > repo/src/profile_loader.py <<'EOF'
from __future__ import annotations

import json
from pathlib import Path


def load_user_profile(path: Path) -> dict | None:
    try:
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
        return {"id": int(data["id"]), "name": data["name"].strip()}
    except Exception:
        return None
EOF

cat > repo/tests/__init__.py <<'EOF'
EOF

cat > repo/tests/test_profile_loader.py <<'EOF'
from pathlib import Path
import tempfile
import unittest

from src.profile_loader import load_user_profile


class ProfileLoaderTest(unittest.TestCase):
    def test_loads_valid_profile(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "profile.json"
            p.write_text('{"id": 42, "name": "  Ada Lovelace  "}', encoding="utf-8")
            profile = load_user_profile(p)
            self.assertEqual(profile["id"], 42)
            self.assertEqual(profile["name"], "Ada Lovelace")


if __name__ == "__main__":
    unittest.main()
EOF

git -C repo add -A
git -C repo commit -q -m "initial"
