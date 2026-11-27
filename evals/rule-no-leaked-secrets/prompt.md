---
description: "Scrub hardcoded API keys and credential exposure from request logs, exception messages, stderr, and debug snapshots in an API connector."
expected_outcome: "Reads no-leaked-secrets/SKILL.md, removes the hardcoded API key default from src/connector.py, redacts Authorization headers and tokens across logs, errors, stderr, and debug_snapshot(), and adds regression tests proving zero credential leakage across success and failure paths."
allowed_tools: [Read, Glob, Grep, Bash, Edit, Write]
---

`/astack:go` Security audit flagged credential exposure in `./repo` (`src/connector.py`): the connector contains a hardcoded fallback API key and exposes raw bearer tokens and request headers across logs, error messages, stderr output, and diagnostic snapshots.

Read `./repo/README.md` for the connector contract. Remove the hardcoded credential, redact secrets across every log, error, stderr, and diagnostic output while preserving functional request authentication and `correlation_id` reporting, add regression tests under `./repo/tests/` asserting zero credential leakage across failure paths, and verify all tests pass. Do not print any raw credential values in your final response.
