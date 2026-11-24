---
description: "Go mode routes an adversarial review request to review and spawns the dedicated astack:reviewer subagent rather than general-purpose."
expected_outcome: "Reads review/SKILL.md and invokes the Agent tool with subagent_type astack:reviewer."
allowed_tools: [Read, Glob, Grep, Agent]
---

`/astack:go` Run an adversarial review of `bin/astack-decisions` checking edge cases and error handling. Dispatch a reviewer subagent to audit it and report the verdict.
