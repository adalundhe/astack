---
description: "Tighten overly broad wildcard RBAC grants and admin fallback into exact scoped roles and prove both allow and deny as non-privileged identities."
expected_outcome: "Reads least-privilege/SKILL.md, removes wildcard grants and admin fallback in DEFAULT_POLICIES and PolicyEngine, separates runtime and migration roles, enforces tenant isolation, and adds tests proving allow and deny as real non-privileged identities."
allowed_tools: [Read, Glob, Grep, Bash, Edit, Write]
---

`/astack:go` Tighten the RBAC policies and authorization enforcement in `./repo` (`src/rbac.py`) so every workload identity receives only the exact actions, resources, and tenant boundary it needs.

Read `./repo/README.md` for the role matrix and public API. Fix the overly broad grants, role separation, tenant boundary checks, and authorization fallback in `./repo/src/rbac.py`, add tests under `./repo/tests/` proving both allowed and denied actions as real non-privileged identities, and verify all tests pass.
