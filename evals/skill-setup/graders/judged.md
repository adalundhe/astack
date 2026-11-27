---
type: llm
---

Evaluate the updated `program/settings.json` against `setup`.

PASS if all of these hold:
- Leaves `./repo` completely untouched (no edits or status changes).
- Updates `program/settings.json` into valid JSON with all five positive integer timers (`worker_minutes`, `reviewer_minutes`, `researcher_minutes`, `check_in_minutes`, `wind_down_minutes`) satisfying `wind_down_minutes < min(role timers)`.
- Preserves `lead`, `worker`, and `researcher` roles, removes the retired `roles.reviewer` key, and populates `reviewer_pool` with the migrated OpenAI entry plus the approved Anthropic entry.
- Adds valid `autonomy` (`supervised`, disjoint `allow`/`deny` with safety guardrails) and `automation` (`agentic-only`) sections with zero secrets.

FAIL otherwise.
