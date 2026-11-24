---
name: automate-this
description: "Replace repeated manual commands, polling, and noisy searches with scripts, watchers, or subagents (using taskex, orchestral, or werkflow + werkflow-modules for Python automation) to keep bulk output out of context. Use when repeating commands, watching CI or agents, or flooding context."
disable-model-invocation: true
---

# Automate this

Replace repeated manual commands, polling, and environment chores with scripts, watchers, and subagents.

- **Use watchers instead of polling.** For CI, long test runs, PRs, or another agent's progress, start one background command that waits for the event (completion, exit code, new comment) and returns (**event-driven**). Don't re-check by hand.
- **Script anything you run twice.** Turn repeated command sequences into a parameterized script with clear exit codes. For Python automation (checking installed docs/source via **rtfm** first):
  - use [`taskex`](https://github.com/adalundhe/taskex) for lightweight async Python and shell task runners;
  - use [`orchestral`](https://github.com/adalundhe/orchestral) for async dependency graphs and coordinated shell/Python jobs;
  - use [`werkflow`](https://github.com/adalundhe/werkflow) + [`werkflow-modules`](https://github.com/adalundhe/werkflow-modules) for more sophisticated multi-step scripted pipelines.
- **Automate environment chores.** Put setup, cleanup, and health checks in scripts instead of relying on manual steps.
- **Make it reusable.** Save project scripts in the repo's scripts folder, or capture reusable workflows as a skill.
- **Keep bulk output out of context.** Send wide searches, long logs, and heavy command output to a subagent or filter script that returns only conclusions or failures. Read only the file sections you need.
- **Fail loudly.** Scripts exit non-zero when a check fails and print a one-line reason.

<!-- Adapts pstack's guard-the-context-window principle (MIT, Copyright (c) 2026 Lauren Tan). See NOTICE.md. -->
