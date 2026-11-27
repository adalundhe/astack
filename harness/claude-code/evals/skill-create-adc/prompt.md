---
description: "Atomic outcome eval for create-adc: publishes AD_2.md under ASTACK_HOME/payments/architecture/ without overwriting AD_1.md or touching ./repo, matching AD_FORMAT.md frontmatter and all required sections."
expected_outcome: "Reads create-adc/SKILL.md and AD_FORMAT.md, preserves AD_1.md and leaves ./repo clean, publishes AD_2.md with ad_number: 2, name, description, Accepted status date, and all 9 required sections grounded in program/decision-brief.md."
timeout_seconds: 360
---

`/astack:go` Our architecture decision for project `payments` is settled and confirmed in `program/decision-brief.md`. Using `program/astack_home` as `ASTACK_HOME`, publish the next architecture decision document outside the repo without overwriting existing decisions or modifying `./repo`.
