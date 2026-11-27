#!/bin/bash
set -euo pipefail
mkdir -p program repo/infra repo/src repo/tests

git -C repo init -q -b main
git -C repo config user.name "Eval"
git -C repo config user.email "eval@example.invalid"
git -C repo config commit.gpgsign false

cat > repo/infra/live_state.json <<'EOF'
{
  "environment": "prod-us-east-1",
  "resources": {
    "primary_db": {
      "type": "postgres_database",
      "stateful": true,
      "engine_version": "15.4",
      "instance_class": "db.m6g.large",
      "availability_zone": "us-east-1a",
      "storage_encrypted": true,
      "backup_retention_days": 14,
      "prevent_destroy": true
    },
    "api_service": {
      "type": "container_service",
      "stateful": false,
      "image": "registry.acme.internal/api:1.12.0@sha256:a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4",
      "min_replicas": 2,
      "max_replicas": 10,
      "log_retention_days": 30
    }
  }
}
EOF

cat > repo/infra/desired.json <<'EOF'
{
  "environment": "prod-us-east-1",
  "resources": {
    "primary_db": {
      "type": "postgres_database",
      "stateful": true,
      "engine_version": "15.4",
      "instance_class": "db.m6g.xlarge",
      "availability_zone": "us-east-1b",
      "storage_encrypted": true,
      "backup_retention_days": 14,
      "prevent_destroy": false
    },
    "api_service": {
      "type": "container_service",
      "stateful": false,
      "image": "registry.acme.internal/api:latest",
      "min_replicas": 2,
      "max_replicas": null,
      "log_retention_days": null
    }
  }
}
EOF

cat > repo/src/__init__.py <<'EOF'
EOF

cat > repo/src/plan.py <<'EOF'
#!/usr/bin/env python3
"""Dry-run infrastructure planner comparing live state and desired manifest."""
from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any

IMMUTABLE_FIELDS: dict[str, tuple[str, ...]] = {
    "postgres_database": ("availability_zone", "storage_encrypted"),
}


def plan_changes(live: dict[str, Any], desired: dict[str, Any]) -> list[dict[str, Any]]:
    """Compute per-resource plan actions against live state."""
    live_res = live.get("resources", {})
    des_res = desired.get("resources", {})
    actions: list[dict[str, Any]] = []

    for name in sorted(set(live_res) | set(des_res)):
        if name not in live_res:
            actions.append({"resource": name, "action": "create", "changed_fields": sorted(des_res[name])})
            continue
        if name not in des_res:
            actions.append({"resource": name, "action": "destroy", "changed_fields": []})
            continue
        cur = live_res[name]
        nxt = des_res[name]
        changed = sorted(k for k in set(cur) | set(nxt) if cur.get(k) != nxt.get(k))
        if not changed:
            actions.append({"resource": name, "action": "noop", "changed_fields": []})
            continue
        immut = set(IMMUTABLE_FIELDS.get(cur.get("type", ""), ()))
        if any(field in immut for field in changed):
            actions.append({"resource": name, "action": "replace", "changed_fields": changed})
        else:
            actions.append({"resource": name, "action": "update", "changed_fields": changed})
    return actions


def validate_plan(
    live: dict[str, Any],
    desired: dict[str, Any],
    actions: list[dict[str, Any]],
) -> list[str]:
    """Return safety violations blocking this plan. Currently only checks environment match."""
    violations: list[str] = []
    if live.get("environment") != desired.get("environment"):
        violations.append(
            f"environment mismatch: live={live.get('environment')!r} desired={desired.get('environment')!r}"
        )
    return violations


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 2:
        print("usage: plan.py <live_state.json> <desired.json>", file=sys.stderr)
        return 2
    live = json.loads(Path(args[0]).read_text(encoding="utf-8"))
    desired = json.loads(Path(args[1]).read_text(encoding="utf-8"))
    actions = plan_changes(live, desired)
    violations = validate_plan(live, desired, actions)
    print(json.dumps({"actions": actions, "violations": violations}, indent=2))
    return 1 if violations else 0


if __name__ == "__main__":
    raise SystemExit(main())
EOF
chmod +x repo/src/plan.py

cat > repo/tests/__init__.py <<'EOF'
EOF

cat > repo/tests/test_plan.py <<'EOF'
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from plan import plan_changes


class PlannerBaselineTest(unittest.TestCase):
    def test_mutable_field_produces_in_place_update(self):
        live = {
            "environment": "prod",
            "resources": {
                "primary_db": {
                    "type": "postgres_database",
                    "stateful": True,
                    "instance_class": "db.m6g.large",
                    "availability_zone": "us-east-1a",
                    "prevent_destroy": True,
                }
            },
        }
        desired = {
            "environment": "prod",
            "resources": {
                "primary_db": {
                    "type": "postgres_database",
                    "stateful": True,
                    "instance_class": "db.m6g.xlarge",
                    "availability_zone": "us-east-1a",
                    "prevent_destroy": True,
                }
            },
        }
        actions = plan_changes(live, desired)
        self.assertEqual(actions[0]["action"], "update")
        self.assertEqual(actions[0]["changed_fields"], ["instance_class"])


if __name__ == "__main__":
    unittest.main()
EOF

git -C repo add .
git -C repo commit -q -m "initial infra manifest and planner"
git -C repo rev-parse HEAD > program/base_sha.txt
