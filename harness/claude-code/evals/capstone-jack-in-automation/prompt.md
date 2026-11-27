---
description: "Onboard brand-new project ops-inventory: map local tooling to program/TOOLS.md and durable docs under ASTACK_HOME, build and execute a read-only TaskEx SQLite inspection automation leaving inventory.db unmodified, scope repo/config/roles.json, and remove stale --dump-all from repo/README.md."
expected_outcome: "Publishes program/TOOLS.md and a durable connection doc under program/astack_home/ops-inventory/docs/, registers and runs a read-only TaskEx automation under program/astack_home/ops-inventory/automations/<name>/ returning real inventory.db rows while preserving inventory.db SHA-256, removes wildcard grants from repo/config/roles.json with allow/deny tests, removes stale --dump-all from repo/README.md, and passes unittest, mutation, gate, and secret checks."
allowed_tools: [Read, Glob, Grep, Bash, Write, Edit, Agent]
timeout_seconds: 1200
---

`/astack:go` Read `program/brief.md` and onboard the brand-new project `ops-inventory` in `./repo` (with an initially empty `program/astack_home/`).

Map the host environment and access paths to `program/TOOLS.md` and a durable doc under `program/astack_home/ops-inventory/docs/`, build and run a read-only TaskEx automation under `program/astack_home/ops-inventory/automations/` that queries `./repo/data/inventory.db` without modifying the database file, tighten the overly broad permissions in `./repo/config/roles.json` with allow/deny unit tests, and update the stale `./repo/README.md` to match the real CLI.
