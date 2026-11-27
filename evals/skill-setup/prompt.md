---
description: "Atomic outcome eval for setup: upgrades a partial legacy program/settings.json using recorded user preferences into valid JSON with all required role timers, migrated approved reviewer entries, autonomy rules, and automation mode without secrets or edits to ./repo."
expected_outcome: "Reads setup/SKILL.md, leaves ./repo clean and untouched, updates program/settings.json with all 5 positive integer timers, lead/worker/researcher roles (removing retired roles.reviewer), populated approved reviewer list, valid disjoint autonomy allow/deny, and automation mode without secrets."
timeout_seconds: 360
---

`/astack:go` Upgrade our legacy configuration file at `program/settings.json` using the approved choices recorded in `program/preferences.md`. Add the missing role timers, migrate any retired reviewer role layout into the current schema, add autonomy and automation configuration, validate all types and constraints, and leave `./repo` untouched without storing any secrets.
