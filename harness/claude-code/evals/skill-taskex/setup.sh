#!/usr/bin/env bash
set -euo pipefail

mkdir -p program/astack_home repo/src

git -C repo init -q -b main
git -C repo config user.name "Eval"
git -C repo config user.email "eval@example.invalid"
git -C repo config commit.gpgsign false

cat > repo/README.md <<'EOF'
# ops-portal

Internal operations portal repository (`project_name`: `ops-portal`).

## Local health check
Run `python3 src/healthcheck.py --manifest src/services.json` to inspect local service manifests and exit 0 when all services are healthy, or non-zero when any service is degraded.
EOF

cat > repo/src/services.json <<'EOF'
{
  "services": [
    {"name": "gateway", "status": "ok"},
    {"name": "billing-worker", "status": "ok"}
  ]
}
EOF

cat > repo/src/healthcheck.py <<'EOF'
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Check ops-portal service manifest health.")
    parser.add_argument("--manifest", required=True, help="Path to services JSON manifest")
    args = parser.parse_args()
    data = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    unhealthy = [s["name"] for s in data.get("services", []) if s.get("status") != "ok"]
    if unhealthy:
        print(f"DEGRADED: {', '.join(unhealthy)}", file=sys.stderr)
        return 1
    print(f"OK: {len(data.get('services', []))} services healthy")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
EOF

git -C repo add .
git -C repo commit -q -m "initial ops-portal healthcheck manifest and script"

cat > program/request.md <<'EOF'
# Automation Request: ops-portal Health Watcher

- **Project slug:** `ops-portal`
- **Goal:** Save a recurring TaskEx health-check watcher under `$ASTACK_HOME/ops-portal/automations/<automation_name>/` (never inside `./repo`).
- **Behavior:**
  - Runs `python3` against `./repo/src/healthcheck.py --manifest ./repo/src/services.json` using safe subprocess arguments (`shell=False`, merged `{**os.environ, ...}` if overriding env).
  - Supports `--once`, `--dry-run`, `--resume`, and `--clear-checkpoints` flags.
  - Supports recurring cadence (e.g. `schedule="60s"` when not in `--once` mode) and stores durable checkpoints at `Path(__file__).resolve().parent / "state" / "checkpoints.db"`.
  - Checks `RunStatus.COMPLETE` explicitly and exits non-zero on failure.
  - Includes `automation.json` with `runner: "taskex"` and `entrypoint`, plus a secret-free `config.example.json` if parameterized.
EOF
