---
description: "Cold-start skill discovery eval: NO /astack:go prefix, NO skill names, NO skills path. Tests whether a normal user prompt ('Review repo/retry_client.py before we merge it') still auto-discovers astack and reads hidden leaf SKILL.md files."
expected_outcome: "Auto-triggers astack Go mode (or locates installed skills via astack-tools skills-dir / plugin cache), reads at least one hidden leaf SKILL.md (such as review, adversarial-review, no-hidden-flow-control, no-picked-constants, or event-driven), and reports the concrete bugs and rule violations in repo/retry_client.py without modifying the repo."
max_turns: 14
timeout_seconds: 300
allowed_tools: [Read, Glob, Grep, Bash, Agent, Skill]
---

Review `repo/retry_client.py` against `main` before we merge branch `lane/retry-client`. Do not edit any files in `repo/`—just report what's wrong and how to fix it.
