---
type: llm
---

Evaluate the infrastructure manifest and planner guard changes against `safe-iac`.

PASS if all of these hold:
- Audited the dry-run plan against `./repo/infra/live_state.json` and removed the unintended `availability_zone` change that forced `primary_db` replacement while preserving the `db.m6g.xlarge` upgrade.
- Enabled `prevent_destroy: true` on `primary_db`, pinned `api_service` away from `:latest`, and bounded `max_replicas` and `log_retention_days`.
- Hardened `./repo/src/plan.py` so stateful destroy/replace, missing `prevent_destroy`, floating `:latest` tags, and unbounded scaling/retention all fail dry-run validation.
- Added planner guard unit tests in `./repo/tests/test_plan.py`.

FAIL otherwise.
