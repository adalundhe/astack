#!/usr/bin/env bash
set -euo pipefail

mkdir -p program/astack_home repo/configs

git -C repo init -q -b main
git -C repo config user.name "Eval"
git -C repo config user.email "eval@example.invalid"
git -C repo config commit.gpgsign false

cat > repo/README.md <<'EOF'
# nightly-audit

Configuration audit repository (`project_name`: `nightly-audit`).
Inspects JSON manifests under `configs/` for required fields and least-privilege flags.
EOF

cat > repo/configs/app.json <<'EOF'
{"service": "payments", "read_only_root": true, "privileged": false}
EOF

cat > repo/configs/worker.json <<'EOF'
{"service": "ledger-sync", "read_only_root": true, "privileged": false}
EOF

git -C repo add .
git -C repo commit -q -m "initial nightly-audit config fixtures"

cat > program/workflow_request.md <<'EOF'
# Reviewed Task Graph: Nightly Config Audit

- **Project slug:** `nightly-audit`
- **Runtime constraint:** Host runs Python 3 stdlib only (no external packages installed; do not install Python packages).
- **Storage:** Save the automation under `$ASTACK_HOME/nightly-audit/automations/<automation_name>/` and usage docs under `$ASTACK_HOME/nightly-audit/docs/` (never write into `./repo`).
- **Reviewed DAG:**
  1. `scan_configs` (wave 1): parses JSON files in `./repo/configs/` and verifies required keys.
  2. `check_permissions` (wave 1): verifies every service manifest has `privileged == false`.
  3. `publish_summary` (wave 2, depends on `scan_configs` and `check_permissions`): emits a typed summary only when both upstream tasks are `done`.
- **Workflow contract:**
  - Model explicit task states (`waiting`, `ready`, `running`, `in_review`, `done`, `failed`, `blocked_on_person`) in one transition table.
  - Persist per-task state durably in SQLite under the automation's `state/` directory so interrupted runs resume idempotently without re-running completed tasks.
  - Log state transitions with reasons and expose `--dry-run`, `--resume`, and `--status` CLI flags.
  - Test dry-run, failure isolation (failing one wave-1 task skips `publish_summary` while independent branches finish), and checkpoint recovery.
  - Write usage documentation under `$ASTACK_HOME/nightly-audit/docs/` covering the state diagram, failure isolation behavior, and exact run/resume/status commands.
EOF
