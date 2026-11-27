#!/usr/bin/env bash
set -euo pipefail

mkdir -p program/astack_home repo/src

git -C repo init -q -b main
git -C repo config user.name "Eval"
git -C repo config user.email "eval@example.invalid"
git -C repo config commit.gpgsign false

cat > repo/README.md <<'EOF'
# data-sync

Warehouse sync tooling (`project_name`: `data-sync`).

## Sync Stages
1. Wave 1 (parallel): extract `users` snapshot and extract `orders` snapshot into isolated staging files.
2. Wave 2 (fan-in after both wave-1 steps succeed): merge snapshots, conditionally skip empty partitions in step code, and emit a deterministic sync summary.
EOF

cat > repo/src/stages.py <<'EOF'
from __future__ import annotations

import json
from pathlib import Path


def extract_users(out_file: Path) -> int:
    rows = [{"user_id": "u1", "active": True}, {"user_id": "u2", "active": False}]
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(json.dumps(rows), encoding="utf-8")
    return len(rows)


def extract_orders(out_file: Path) -> int:
    rows = [{"order_id": "o1", "user_id": "u1", "amount": 4200}]
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(json.dumps(rows), encoding="utf-8")
    return len(rows)
EOF

git -C repo add .
git -C repo commit -q -m "initial data-sync stage helpers"

cat > program/request.md <<'EOF'
# Automation Request: data-sync Multi-Wave DAG

- **Project slug:** `data-sync`
- **Goal:** Save a concise Orchestral multi-wave DAG workflow under `$ASTACK_HOME/data-sync/automations/<automation_name>/` (never inside `./repo`).
- **Requirements:**
  - Wave 1 runs `extract_users` and `extract_orders` in parallel into isolated output files.
  - Wave 2 (`reconcile_and_export`) declares `dependencies=[...]` on both wave-1 steps, owns state-passing and conditional branching in step code (skips export if no active orders exist), and uses SQLite checkpoints at `Path(__file__).resolve().parent / "state" / "workflow.db"`.
  - Validates waves upfront with `orch.execution_order()` and checks both `orch.status == WorkflowStatus.COMPLETED` and every step's `RunStatus.COMPLETE`.
  - Exposes CLI flags `--dry-run`, `--show-waves`, `--resume`, `--clear-checkpoints`, and `--fail-fast`.
  - Includes `automation.json` with `runner: "orchestral"`, `entrypoint`, and `workflow_id`.
EOF
