---
description: "Audits a dry-run infrastructure plan against live state, stops unintended stateful DB replacement, pins floating image tags, bounds autoscaling and retention spend, and enforces planner guards."
expected_outcome: "Reads safe-iac/SKILL.md, fixes repo/infra/desired.json so primary_db upgrades in-place with prevent_destroy=true while pinning api_service image and bounding max_replicas/log_retention_days, hardens src/plan.py validation guards, and adds planner guard tests."
max_turns: 16
timeout_seconds: 300
allowed_tools: [Read, Glob, Grep, Bash, Edit, Write]
---

`/astack:go` We need to scale `primary_db` to `db.m6g.xlarge` and update `api_service` in `./repo/infra/desired.json` without disrupting live production state, and harden the dry-run planner in `./repo/src/plan.py` so unsafe plans fail before apply.

Run `./repo/src/plan.py ./repo/infra/live_state.json ./repo/infra/desired.json` to inspect the actual diff against live state, fix the manifest issues in `./repo/infra/desired.json` while keeping the `db.m6g.xlarge` upgrade, enforce safety validation in `./repo/src/plan.py` (stateful protection, immutable image versions, and bounded scaling/retention), and add tests in `./repo/tests/test_plan.py`.
