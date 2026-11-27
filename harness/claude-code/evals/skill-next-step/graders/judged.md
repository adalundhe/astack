---
type: llm
---

Evaluate the next-step recommendations against `next-step/SKILL.md`.

PASS if all of these hold:
- Verifies `program/astack_home/cli-kit/docs/contracts/cli-contract.md` against `repo/src/cli.py` and cites exact `file:line` evidence.
- Maps current Tier 0 capabilities (`list`, `run <task>`, `--config`, `CLI_KIT_CONFIG`) to minimal-surface Tier 1+ rungs (`--dry-run`, `--json`, `--tag`) while explicitly confirming zero regression for simpler callers.
- Ranks proposals by consumer impact relative to new contract surface added, directly resolving the friction recorded in `repo/docs/user_feedback.md`.
- Leaves `./repo` clean and omits internal astack jargon.

FAIL otherwise.
