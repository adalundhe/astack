---
name: go
description: "Single entry point for astack—routes to every workflow, review, benchmarking, research, catch-up, and coding-rule skill on demand by path so only one skill sits in context. Use for /astack:go or any engineering task using astack."
---

# Go mode

You are running in astack Go mode. Every other astack skill is hidden from the model catalog to keep session context small; load any skill on demand by reading its `SKILL.md` file before acting on its trigger.

Skill files live beside this one at `${CLAUDE_SKILL_DIR}/../<name>/SKILL.md`. Never guess a skill's instructions from the one-line summary below—read the file first when it applies.

The astack scripts (`astack-status`, `astack-verify-merge`, `astack-stamp`, `astack-decisions`, `astack-tools`) are on your PATH.

## Startup

1. Read `~/.config/astack/settings.json` (or `$XDG_CONFIG_HOME/astack/settings.json`) if present: timing (`worker_minutes`, `wind_down_minutes`, `check_in_minutes`, defaults `60 / 5 / 5`) and per-role `provider`, `model`, and `effort` (`lead`, `worker`, `reviewer`, `researcher`, defaulting to the active session when `"default"` or unset). Apply configured role models/effort when spawning subagents where the tool supports it.
2. Route immediately based on what the person asked for—don't pause to ask for permission before reading the matching skill(s).
3. Follow astack's core sequence on all engineering work: **work -> robust -> fast**, verify on the real system, settle technical questions yourself with evidence and log why, and interrupt the person only for genuine human calls.

## Workflow playbooks

Read the matching skill file(s) before starting:

- **Configure timing and per-role models/effort:** `${CLAUDE_SKILL_DIR}/../setup/SKILL.md`
- **Run a multi-lane program with parallel workers:** `${CLAUDE_SKILL_DIR}/../lead/SKILL.md`, plus `${CLAUDE_SKILL_DIR}/../dagify/SKILL.md`, `${CLAUDE_SKILL_DIR}/../workflow-this/SKILL.md`, `${CLAUDE_SKILL_DIR}/../track-it/SKILL.md`
- **Check status, catch up, or rebuild context after a break:**
  - Quick status of running workers and lanes: `${CLAUDE_SKILL_DIR}/../status/SKILL.md`
  - Single-pane-of-glass catch-up and context rebuild after a break or compaction (decisions waiting, bugs/regressions, features/milestones, hypotheses/experiments/research): `${CLAUDE_SKILL_DIR}/../whatsup/SKILL.md`
- **Understand, align, or challenge before building:**
  - Restate scope, done-when, and assumptions: `${CLAUDE_SKILL_DIR}/../run-it-back/SKILL.md`
  - Peer-to-peer adversarial challenge of hypotheses, repeated fixes, designs, or implementations: `${CLAUDE_SKILL_DIR}/../challenge/SKILL.md`
  - Check existing docs, code, history, and environment first: `${CLAUDE_SKILL_DIR}/../rtfm/SKILL.md`
  - Walk through unfamiliar code with `file:line` citations: `${CLAUDE_SKILL_DIR}/../how-it-works/SKILL.md`
  - Diagram states, transitions, and failure paths: `${CLAUDE_SKILL_DIR}/../show-the-states/SKILL.md`
  - Research inside and outside with quote checks and A–F grading: `${CLAUDE_SKILL_DIR}/../research-this/SKILL.md`
  - Tighten a task brief to expert standards without growing scope: `${CLAUDE_SKILL_DIR}/../deeper/SKILL.md`
  - Prototype a quick throwaway mockup/demo: `${CLAUDE_SKILL_DIR}/../play-with-me/SKILL.md`
  - Explain unfamiliar concepts clearly: `${CLAUDE_SKILL_DIR}/../talk-to-me/SKILL.md`
  - Work through and publish an architecture decision (`AD-N`): `${CLAUDE_SKILL_DIR}/../create-adc/SKILL.md`
- **Optimize and experiment:**
  - Design and run statistically sound benchmarks: `${CLAUDE_SKILL_DIR}/../benchmarking/SKILL.md`
  - Fair cross-system / competitor benchmarks: `${CLAUDE_SKILL_DIR}/../fair-benchmarks/SKILL.md`
  - Settle design/config choices by measurement: `${CLAUDE_SKILL_DIR}/../decide-by-data/SKILL.md`
  - Run isolated worktree A/B tests and graft winning parts: `${CLAUDE_SKILL_DIR}/../ab-test/SKILL.md`
  - Step-by-step performance optimization: `${CLAUDE_SKILL_DIR}/../clamber/SKILL.md`
  - Build competing architectures in parallel, graft best ideas, keep winner: `${CLAUDE_SKILL_DIR}/../explore-the-limits/SKILL.md`
- **Test, verify, and prove:**
  - Verify against the real artifact with runnable proof: `${CLAUDE_SKILL_DIR}/../prove-it/SKILL.md`
  - Reproduce bugs with realistic user scenarios first: `${CLAUDE_SKILL_DIR}/../bugs-by-scenario/SKILL.md`
  - Full-spectrum acceptance tests across the test diamond: `${CLAUDE_SKILL_DIR}/../full-spectrum-testing/SKILL.md`
  - Build or update a `drive-<app>` live user-flow verification skill: `${CLAUDE_SKILL_DIR}/../test-drive/SKILL.md`
  - Formal verification (TLA+, code verifiers, generated checks): `${CLAUDE_SKILL_DIR}/../every-case/SKILL.md`
- **Refactor, review, and ship PRs:**
  - Trace indirect breakage beyond a diff: `${CLAUDE_SKILL_DIR}/../blast-radius/SKILL.md`
  - Trim unnecessary code and complexity: `${CLAUDE_SKILL_DIR}/../simplify-me/SKILL.md`
  - Split monoliths into single-purpose modules: `${CLAUDE_SKILL_DIR}/../modularize/SKILL.md`
  - Find structural friction in high-churn areas and plan restructuring: `${CLAUDE_SKILL_DIR}/../rearchitect/SKILL.md`
  - Adversarial multi-reviewer audit: `${CLAUDE_SKILL_DIR}/../review/SKILL.md` and `${CLAUDE_SKILL_DIR}/../adversarial-review/SKILL.md`
  - Refute wrong or unproven review points with evidence: `${CLAUDE_SKILL_DIR}/../worrywart/SKILL.md`
  - Resolve every review finding and PR thread: `${CLAUDE_SKILL_DIR}/../address-feedback/SKILL.md`
  - Shepherd a reviewed PR through CI and feedback: `${CLAUDE_SKILL_DIR}/../watch-pr/SKILL.md`
  - Fix unrelated broken tests/builds/CI in a separate PR: `${CLAUDE_SKILL_DIR}/../leave-it-better/SKILL.md`
- **Communicate, document, automate, and wrap up:**
  - Decide what you can, log it, escalate only real human calls: `${CLAUDE_SKILL_DIR}/../decisions-in-plain-words/SKILL.md`
  - Rewrite unclear/jargon-heavy output cleanly: `${CLAUDE_SKILL_DIR}/../wat/SKILL.md`
  - Write or update concrete, verified documentation: `${CLAUDE_SKILL_DIR}/../technical-writing/SKILL.md`
  - Replace repeated commands/polling with scripts and watchers: `${CLAUDE_SKILL_DIR}/../automate-this/SKILL.md`
  - Author/manage async tasks, shell runners, and watchers (`taskex`): `${CLAUDE_SKILL_DIR}/../taskex/SKILL.md`
  - Author/manage multi-stage concurrent pipelines (`orchestral`): `${CLAUDE_SKILL_DIR}/../orchestral/SKILL.md`
  - Author/manage modular DAG workflows and integrations (`werkflow` + `werkflow-modules`): `${CLAUDE_SKILL_DIR}/../werkflow/SKILL.md`
  - Remove temp files, build artifacts, and leftover processes: `${CLAUDE_SKILL_DIR}/../cleanup/SKILL.md`
  - Capture session lessons and enforce fixes structurally: `${CLAUDE_SKILL_DIR}/../make-it-stick/SKILL.md`

## Principles and coding-rules index

Read the matching rule file whenever its trigger applies to code you are designing, writing, or reviewing:

| Trigger | Rule file |
|---|---|
| Designing schemas, structs, state, or algorithms | `${CLAUDE_SKILL_DIR}/../data-structures-first/SKILL.md` |
| Behavior depends on prior state or lifecycle flags | `${CLAUDE_SKILL_DIR}/../no-implicit-states/SKILL.md` |
| Error handling, retries, exceptions, or fallbacks | `${CLAUDE_SKILL_DIR}/../no-hidden-flow-control/SKILL.md` |
| CLI flags, config files, env vars, or feature toggles | `${CLAUDE_SKILL_DIR}/../no-hidden-config/SKILL.md` |
| Caches, copies, denormalization, or long-lived state | `${CLAUDE_SKILL_DIR}/../minimize-state-stores/SKILL.md` |
| Parsing requests, CLI args, files, DB rows, or API replies | `${CLAUDE_SKILL_DIR}/../check-your-boundaries/SKILL.md` |
| Concurrent threads, processes, agents, or locks | `${CLAUDE_SKILL_DIR}/../no-shared-writes/SKILL.md` |
| Commands, migrations, deploy steps, jobs, or retries | `${CLAUDE_SKILL_DIR}/../safe-to-rerun/SKILL.md` |
| Adding a new requirement to existing code | `${CLAUDE_SKILL_DIR}/../no-bolt-ons/SKILL.md` |
| Replacing code, shims, legacy paths, or dead flags | `${CLAUDE_SKILL_DIR}/../yagni/SKILL.md` |
| Writing, reviewing, or cleaning up comments | `${CLAUDE_SKILL_DIR}/../comment-cop/SKILL.md` |
| User-facing UI, CLI, errors, defaults, or public APIs | `${CLAUDE_SKILL_DIR}/../delight-users/SKILL.md` |
| Limits, timeouts, batch/pool sizes, or thresholds | `${CLAUDE_SKILL_DIR}/../no-picked-constants/SKILL.md` |
| Waiting, polling loops, sleeps, timers, or CI checks | `${CLAUDE_SKILL_DIR}/../event-driven/SKILL.md` |
| Speedups, memory cuts, or approximate/deferred variants | `${CLAUDE_SKILL_DIR}/../never-trade-functionality/SKILL.md` |
| Writing, reviewing, or fixing any test or flake | `${CLAUDE_SKILL_DIR}/../tests-assert-behaviour/SKILL.md` |
