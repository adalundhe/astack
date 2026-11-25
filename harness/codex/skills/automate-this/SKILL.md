---
name: automate-this
description: "Replace repeated manual commands, polling, and noisy searches with scripts, watchers, or subagents (using taskex, orchestral, or werkflow when python-stack is enabled) to keep bulk output out of context."
---

# Automate this

Replace repeated commands, manual polling, and noisy log dumps with scripts, watchers, and subagents, because manual chores burn context and hide real failures.

- **Use watchers instead of polling (**event-driven**):** for CI, long test runs, PRs, or agent progress, start one background watcher that returns on the event. Never re-check by hand.
- **Script anything you run twice:** turn repeated commands into a parameterized script with clear exit codes. Check `automation.mode` in `~/.config/astack/settings.json` (**setup**):
  - When `"agentic-only"` (or Python stack absent): use pure-agentic flows, shell/repo-native scripts, and subagents.
  - When `"python-stack"` is enabled (verify via `astack-tools doctor`; run via `astack-tools python` or `astack-tools werkflow`):
    - **taskex** (+ **checkpoint**, **suspend**, **resume**) for async/sync tasks, shell watchers, recurring schedules, and SQLite pause/resume;
    - **orchestral** (+ **checkpoint**, **suspend**, **resume**) for DAG waves, cycle checks, branch-aware skipping, and workflow-level pause/resume;
    - **werkflow** for decorator `@step` DAGs with return-value injection and `werkflow-modules` integrations.
- **Automate environment chores:** script setup, cleanup, and health checks instead of repeating manual steps.
- **Make helpers reusable:** save project scripts in `scripts/` (or capture recurring flows as a skill) and record shared tools in `<program>/TOOLS.md` (**analyze-environment**).
- **Keep bulk output out of context:** send wide searches and noisy logs to a subagent or filter script that returns only failures and conclusions.
- **Fail loudly:** exit non-zero on failure and print a one-line reason.

Referenced skills: `event-driven` (`../event-driven/SKILL.md`), `setup` (`../astack-setup/SKILL.md`), `taskex` (`../taskex/SKILL.md`), `checkpoint` (`../checkpoint/SKILL.md`), `suspend` (`../suspend/SKILL.md`), `resume` (`../resume/SKILL.md`), `orchestral` (`../orchestral/SKILL.md`), `werkflow` (`../werkflow/SKILL.md`), `analyze-environment` (`../analyze-environment/SKILL.md`). Read any cited skill file before acting when its trigger applies.

<!-- Adapts pstack's guard-the-context-window principle (MIT, Copyright (c) 2026 Lauren Tan). See NOTICE.md. -->
