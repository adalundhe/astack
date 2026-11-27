---
description: "Discover the real local SQLite telemetry source for telemetry-hub, wrap it in a reusable read-only connection script under ASTACK_HOME automations, document usage under ASTACK_HOME docs, verify live query output, and keep ./repo clean with zero secret leaks."
expected_outcome: "Reads jack-in/SKILL.md, inspects ./repo/config/env.json and ./repo/data/metrics.db, creates an executable read-only query script under program/astack_home/telemetry-hub/automations/<name>/ that verifies local-dev context and outputs real rows from metrics.db without modifying metrics.db, saves usage docs under program/astack_home/telemetry-hub/docs/, keeps ./repo clean, and leaks zero secrets."
allowed_tools: [Read, Glob, Grep, Bash, Write, Edit]
---

`/astack:go` Connect us to the `local-dev` telemetry data store for project `telemetry-hub` (repository at `./repo`, isolated project store at `ASTACK_HOME=./program/astack_home`).

Inspect `./repo/config/env.json` and the local tooling/data sources in `./repo` rather than assuming a preset vendor stack. Build a runnable, read-only connection and inspection script saved under `$ASTACK_HOME/telemetry-hub/automations/<name>/` (defaulting to `./repo` so it runs in one command with no required arguments), verify it executes and returns real metrics from `./repo/data/metrics.db` without mutating the database, and save brief usage and prerequisite docs under `$ASTACK_HOME/telemetry-hub/docs/`. Keep `./repo` unmodified and never print any credential values.
