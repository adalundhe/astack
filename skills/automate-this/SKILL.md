---
name: automate-this
description: "Replace repeated commands, manual polling, and noisy searches with scripts, watchers, or Python runners. Use whenever work repeats or dumps noisy output."
disable-model-invocation: true
---

# Automate this

Replace repeated commands, manual polling, and noisy logs with scripts and watchers, because manual chores burn context and hide real failures.

- **Use watchers instead of polling (**event-driven**):** use `astack-watch-pr` for PRs and CI, or `astack-status` for lane state. For other waits, start one background watcher that returns on the event. Never re-check by hand.
- **Script anything you run twice:** turn repeated commands into a parameterized script with clear exit codes. Check `automation.mode` in `~/.config/astack/settings.json` (set via `setup`):
  - **`"agentic-only"`** (or Python stack absent): use shell or repo-native scripts, watchers, and pure-agentic flows.
  - **`"python-stack"`:** verify via `astack-tools doctor`. Run scripts through `astack-tools python` or `astack-tools werkflow`.
  - **taskex**: async or sync tasks, shell watchers, and recurring schedules.
  - **orchestral**: DAG waves, cycle checks, and branch-aware skipping.
  - **Pause and recovery:** pair either runner with **checkpoint**, **suspend**, and **resume**.
  - **werkflow**: decorator `@step` DAGs with return-value injection and `werkflow-modules` integrations.
- **Automate environment chores:** script setup, cleanup, and health checks instead of repeating manual steps.
- **Make helpers reusable:** save project scripts in `scripts/`, or capture recurring flows as a skill. Record shared tools in `<program>/TOOLS.md` (`analyze-environment`).
- **Keep bulk output out of context:** filter wide searches and noisy logs through a script—or a subagent if Lead. Return only failures and conclusions.
- **Fail loudly:** exit non-zero on failure and print a one-line reason, because silent exits let broken scripts look successful.

**Done when:** the repeated step runs via one reusable script or watcher with clean exit codes and compact output.

<!-- Adapts pstack's guard-the-context-window principle (MIT, Copyright (c) 2026 Lauren Tan). See NOTICE.md. -->
