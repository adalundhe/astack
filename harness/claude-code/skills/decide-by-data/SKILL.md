---
name: decide-by-data
description: "Settle technical choices with real telemetry, UX probes, or controlled A/B measurements instead of debate. Use before debating approaches or escalating a design call."
disable-model-invocation: true
---

# Decide by data

Settle technical choices with evidence instead of debate, because engineering intuition on bottlenecks and usage frequencies is routinely wrong.

1. **Check real telemetry first:** pull logs, traces, metrics, or query counts (`prove-it`, `research-this`). Measure what actually occurs before inventing options.
2. **Probe UX or API ergonomics:** run a throwaway spike (`play-with-me`) when interaction feel drives the choice.
3. **Benchmark competing variants:** compare any number of candidates via **ab-test** (including Holm–Bonferroni control and its graft-then-delete step).
4. **Act by role:**
   - **Lead and workers:** once data settles the choice, pick the winner and delete losers in the same change. Escalate only trade-offs data cannot settle (**never-trade-functionality**).
   - **Researchers and reviewers:** stay read-only. Return measured evidence, trade-offs, and your pick without deleting files or escalating directly.

**Done when:** the winner and evidence are logged as `decided:` (in `LANES.md` or your report), and losing variants are deleted.

Referenced skills: `ab-test` (`${CLAUDE_SKILL_DIR}/../ab-test/SKILL.md`), `never-trade-functionality` (`${CLAUDE_SKILL_DIR}/../never-trade-functionality/SKILL.md`). Read any cited skill file before acting when its trigger applies.
