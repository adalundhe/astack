#!/usr/bin/env bash
set -euo pipefail

mkdir -p program/astack_home repo/data

git -C repo init -q -b main
git -C repo config user.name "Eval"
git -C repo config user.email "eval@example.invalid"
git -C repo config commit.gpgsign false

cat > repo/README.md <<'EOF'
# jira-migrate

Backlog migration repository (`project_name`: `jira-migrate`).

## Input data
`data/backlog.json` contains epic and story records to validate and prepare for Jira migration.
EOF

cat > repo/data/backlog.json <<'EOF'
{
  "project_key": "PLAT",
  "epics": [
    {"key": "MIG-1", "summary": "Migrate billing workers", "stories": ["Audit env vars", "Verify rollback path"]},
    {"key": "MIG-2", "summary": "Migrate search index", "stories": ["Snapshot index", "Run parity diff"]}
  ]
}
EOF

git -C repo add .
git -C repo commit -q -m "initial jira-migrate backlog fixture"

cat > program/request.md <<'EOF'
# Automation Request: jira-migrate Werkflow Pipeline

- **Project slug:** `jira-migrate`
- **Goal:** Save a composable Werkflow automation under `$ASTACK_HOME/jira-migrate/automations/<automation_name>/` (never inside `./repo`).
- **Requirements:**
  - Uses `werkflow` (`Workflow`, `WorkflowGroup`, `@step`, `@requires`) and `werkflow-modules` (such as `werkflow_file.File` and `werkflow_jira.Jira`).
  - Organizes multiple `Workflow` subclasses (e.g., backlog loading/validation and Jira issue batch preparation) under a single `WorkflowGroup` so every workflow is grouped (avoiding `MultipleWorkflowsViolationError`).
  - Passes data implicitly between `@step` methods via returned dicts and matching parameters.
  - Closes every module inside `async def close(self)`.
  - Includes `automation.json` (`runner: "werkflow"`, `entrypoint: "workflow.py"`, `modules: [...]`) and a secret-free `.werkflow.json.example` (`project_options` template; credentials read from env vars or `werkflow-secrets`).
EOF
