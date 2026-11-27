---
description: "Migrates all callers from legacy parse_v1/parse_records/ENABLE_LEGACY_MODE directly to parse_csv, deletes retired shims and dead flags in the same change, and updates tests to the single remaining path."
expected_outcome: "Reads yagni/SKILL.md, updates repo/src/importer.py and repo/src/report.py to call parse_csv directly, deletes parse_v1, parse_records, ENABLE_LEGACY_MODE, and legacy_compat from repo/src/parser.py, and migrates repo/tests/test_pipeline.py to test all consumers on parse_csv."
max_turns: 16
timeout_seconds: 300
allowed_tools: [Read, Glob, Grep, Bash, Edit, Write]
---

`/astack:go` `./repo` is halfway through moving from `parse_v1` to `parse_csv` in `src/parser.py`. No external consumers depend on `parse_v1`, `parse_records`, `ENABLE_LEGACY_MODE`, or the `legacy_compat` parameter, and no temporary backward-compatibility window is needed.

Migrate every caller in `./repo/src/` directly to `parse_csv`, delete the legacy parser, deprecated alias, compatibility parameter, and dead feature flag in the same change, and update `./repo/tests/test_pipeline.py` so all consumers are tested on the single remaining `parse_csv` path (including quoted CSV fields with embedded commas).
