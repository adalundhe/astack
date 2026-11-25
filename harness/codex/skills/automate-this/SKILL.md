---
name: automate-this
description: "Replace repeated manual commands, polling, and noisy searches with scripts, watchers, or subagents (using taskex, orchestral, or werkflow + werkflow-modules for Python automation) to keep bulk output out of context. Use when repeating commands, watching CI or agents, or flooding context."
---

# Automate this

Replace repeated manual commands, polling, and environment chores with scripts, watchers, and subagents.

- **Use watchers instead of polling.** For CI, long test runs, PRs, or another agent's progress, start one background command that waits for the event (completion, exit code, new comment) and returns (**event-driven**). Don't re-check by hand.
- **Script anything you run twice.** Turn repeated command sequences into a parameterized script with clear exit codes. Check `automation.mode` in `~/.config/astack/settings.json` (**setup**): when `"agentic-only"` (or the Python stack is not installed), default to pure-agentic workflows, shell/repo-native scripts, and subagents. When `"python-stack"` is enabled (verify with `astack-tools doctor`; run via `astack-tools python`, `astack-tools werkflow`, or `eval "$(astack-tools env)"`):
  - read **taskex** (plus **checkpoint**, **suspend**, **resume**) for async/sync Python tasks, shell runners, watchers, recurring jobs, and durable SQLite checkpointing with live/crash-resumable pause and resume;
  - read **orchestral** (plus **checkpoint**, **suspend**, **resume**) for dependency-graph (DAG) wave and multi-stage concurrent Python/shell pipelines with upfront cycle checks, branch-aware failure skipping, `fail_fast`, wave streaming, live workflow/step pause-resume, and SQLite crash recovery;
  - read **werkflow** for decorator DAG workflows with inter-step data injection, `.werkflow.json`/prompts, and external integrations (`werkflow-modules`).
- **Automate environment chores.** Put setup, cleanup, and health checks in scripts instead of relying on manual steps.
- **Make it reusable:** save project scripts in the repo's scripts folder (or capture reusable workflows as a skill), and record newly installed CLIs or shared helpers in `<program>/TOOLS.md` (**analyze-environment**) so other agents immediately find and use them.
- **Keep bulk output out of context.** Send wide searches, long logs, and heavy command output to a subagent or filter script that returns only conclusions or failures. Read only the file sections you need.
- **Fail loudly.** Scripts exit non-zero when a check fails and print a one-line reason.

Referenced skills: `event-driven` (`../event-driven/SKILL.md`), `setup` (`../astack-setup/SKILL.md`), `taskex` (`../taskex/SKILL.md`), `checkpoint` (`../checkpoint/SKILL.md`), `suspend` (`../suspend/SKILL.md`), `resume` (`../resume/SKILL.md`), `orchestral` (`../orchestral/SKILL.md`), `werkflow` (`../werkflow/SKILL.md`), `analyze-environment` (`../analyze-environment/SKILL.md`). Read any cited skill file before acting when its trigger applies.

<!-- Adapts pstack's guard-the-context-window principle (MIT, Copyright (c) 2026 Lauren Tan). See NOTICE.md. -->
