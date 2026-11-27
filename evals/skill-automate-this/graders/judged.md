---
type: llm
---

Evaluate the automation script and final response against `automate-this/SKILL.md`.

PASS if all of these hold:
- Saves an executable, idempotent, secret-safe Python script outside `./repo` (under `program/astack_home/log-audit/automations/log_audit/` or `program/scripts/`) summarizing error counts across `./repo/sample_logs/`.
- Produces compact, deterministic output with zero raw bearer/API tokens across stdout, stderr, script source, and final response.
- Fails loudly with a non-zero exit code and one-line error on missing log directories.
- Leaves `./repo` untouched and reports the reusable command without internal harness jargon.

FAIL otherwise.
