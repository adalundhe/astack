---
name: decide-by-data
description: "Settle choices between designs, implementations, or configs by measuring them instead of arguing. Use when comparing approaches or before escalating a design question."
disable-model-invocation: true
---

# Decide by data

Settle choices between designs, implementations, or settings by measuring them (**ab-test**), not by debating them.

- Measure across the extremes the claim covers and trigger each option's failure modes.
- Once the measurements are in, make the call yourself and delete the losing variants in the same change.
- Only escalate to the person when the decision involves a trade-off data can't settle (**never-trade-functionality**).

Referenced skills: `ab-test` (`${CLAUDE_SKILL_DIR}/../ab-test/SKILL.md`), `never-trade-functionality` (`${CLAUDE_SKILL_DIR}/../never-trade-functionality/SKILL.md`). Read any cited skill file before acting when its trigger applies.
