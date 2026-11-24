---
name: astack-go
description: "Single entry point for astack—routes to every workflow, review, benchmarking, research, catch-up, and coding-rule skill on demand by path so only one skill sits in context. Use for /astack-go or any engineering task using astack."
---

# Go mode

You are running in astack Go mode. Every other astack skill is hidden from the model catalog to keep session context small; load any skill on demand by reading its `SKILL.md` file before acting on its trigger.

Skill files live beside this one at `../<name>/SKILL.md`. Never guess a skill's instructions from the one-line summary below—read the file first when it applies.

The astack scripts (`astack-status`, `astack-verify-merge`, `astack-stamp`, `astack-decisions`, `astack-tools`) are in this package's `bin/` folder, two folders up from this file; run them by that path.

## Startup

1. Read `~/.config/astack/settings.json` (or `$XDG_CONFIG_HOME/astack/settings.json`) if present: timing (`worker_minutes`, `wind_down_minutes`, `check_in_minutes`, defaults `60 / 5 / 5`) and per-role `provider`, `model`, and `effort` (`lead`, `worker`, `reviewer`, `researcher`, defaulting to the active session when `"default"` or unset). Apply configured role models/effort when spawning subagents where the tool supports it.
2. Route immediately based on what the person asked for—don't pause to ask for permission before reading the matching skill(s).
3. Follow astack's core sequence on all engineering work: **work -> robust -> fast**, verify on the real system, settle technical questions yourself with evidence and log why, and interrupt the person only for genuine human calls.

## Workflow playbooks

Read the matching skill file(s) before starting:

- **Configure timing and per-role models/effort:** `../astack-setup/SKILL.md`
- **Run a multi-lane program with parallel workers:** `../astack-lead/SKILL.md`, plus `../dagify/SKILL.md`, `../workflow-this/SKILL.md`, `../track-it/SKILL.md`
- **Check status, catch up, or rebuild context after a break:**
  - Quick status of running workers and lanes: `../astack-status/SKILL.md`
  - Single-pane-of-glass catch-up and context rebuild after a break or compaction (decisions waiting, bugs/regressions, features/milestones, hypotheses/experiments/research): `../whatsup/SKILL.md`
- **Understand, align, or challenge before building:**
  - Restate scope, done-when, and assumptions: `../run-it-back/SKILL.md`
  - Peer-to-peer adversarial challenge of hypotheses, repeated fixes, designs, or implementations: `../challenge/SKILL.md`
  - Check existing docs, code, history, and environment first: `../rtfm/SKILL.md`
  - Walk through unfamiliar code with `file:line` citations: `../how-it-works/SKILL.md`
  - Diagram states, transitions, and failure paths: `../show-the-states/SKILL.md`
  - Research inside and outside with quote checks and A–F grading: `../research-this/SKILL.md`
  - Tighten a task brief to expert standards without growing scope: `../deeper/SKILL.md`
  - Prototype a quick throwaway mockup/demo: `../play-with-me/SKILL.md`
  - Explain unfamiliar concepts clearly: `../talk-to-me/SKILL.md`
  - Work through and publish an architecture decision (`AD-N`): `../create-adc/SKILL.md`
- **Optimize and experiment:**
  - Design and run statistically sound benchmarks: `../benchmarking/SKILL.md`
  - Fair cross-system / competitor benchmarks: `../fair-benchmarks/SKILL.md`
  - Settle design/config choices by measurement: `../decide-by-data/SKILL.md`
  - Run isolated worktree A/B tests and graft winning parts: `../ab-test/SKILL.md`
  - Step-by-step performance optimization: `../clamber/SKILL.md`
  - Build competing architectures in parallel, graft best ideas, keep winner: `../explore-the-limits/SKILL.md`
- **Test, verify, and prove:**
  - Verify against the real artifact with runnable proof: `../prove-it/SKILL.md`
  - Reproduce bugs with realistic user scenarios first: `../bugs-by-scenario/SKILL.md`
  - Full-spectrum acceptance tests across the test diamond: `../full-spectrum-testing/SKILL.md`
  - Build or update a `drive-<app>` live user-flow verification skill: `../test-drive/SKILL.md`
  - Formal verification (TLA+, code verifiers, generated checks): `../every-case/SKILL.md`
- **Refactor, review, and ship PRs:**
  - Trace indirect breakage beyond a diff: `../blast-radius/SKILL.md`
  - Trim unnecessary code and complexity: `../simplify-me/SKILL.md`
  - Split monoliths into single-purpose modules: `../modularize/SKILL.md`
  - Find structural friction in high-churn areas and plan restructuring: `../rearchitect/SKILL.md`
  - Adversarial multi-reviewer audit: `../astack-review/SKILL.md` and `../adversarial-review/SKILL.md`
  - Refute wrong or unproven review points with evidence: `../worrywart/SKILL.md`
  - Resolve every review finding and PR thread: `../address-feedback/SKILL.md`
  - Shepherd a reviewed PR through CI and feedback: `../watch-pr/SKILL.md`
  - Fix unrelated broken tests/builds/CI in a separate PR: `../leave-it-better/SKILL.md`
- **Communicate, document, automate, and wrap up:**
  - Decide what you can, log it, escalate only real human calls: `../decisions-in-plain-words/SKILL.md`
  - Rewrite unclear/jargon-heavy output cleanly: `../wat/SKILL.md`
  - Write or update concrete, verified documentation: `../technical-writing/SKILL.md`
  - Replace repeated commands/polling with scripts and watchers: `../automate-this/SKILL.md`
  - Author/manage async tasks, shell runners, and watchers (`taskex`): `../taskex/SKILL.md`
  - Author/manage multi-stage concurrent pipelines (`orchestral`): `../orchestral/SKILL.md`
  - Author/manage modular DAG workflows and integrations (`werkflow` + `werkflow-modules`): `../werkflow/SKILL.md`
  - Remove temp files, build artifacts, and leftover processes: `../cleanup/SKILL.md`
  - Capture session lessons and enforce fixes structurally: `../make-it-stick/SKILL.md`

## Principles and coding-rules index

Read the matching rule file whenever its trigger applies to code you are designing, writing, or reviewing:

| Trigger | Rule file |
|---|---|
| Designing schemas, structs, state, or algorithms | `../data-structures-first/SKILL.md` |
| Behavior depends on prior state or lifecycle flags | `../no-implicit-states/SKILL.md` |
| Error handling, retries, exceptions, or fallbacks | `../no-hidden-flow-control/SKILL.md` |
| CLI flags, config files, env vars, or feature toggles | `../no-hidden-config/SKILL.md` |
| Caches, copies, denormalization, or long-lived state | `../minimize-state-stores/SKILL.md` |
| Parsing requests, CLI args, files, DB rows, or API replies | `../check-your-boundaries/SKILL.md` |
| Concurrent threads, processes, agents, or locks | `../no-shared-writes/SKILL.md` |
| Commands, migrations, deploy steps, jobs, or retries | `../safe-to-rerun/SKILL.md` |
| Adding a new requirement to existing code | `../no-bolt-ons/SKILL.md` |
| Replacing code, shims, legacy paths, or dead flags | `../yagni/SKILL.md` |
| Writing, reviewing, or cleaning up comments | `../comment-cop/SKILL.md` |
| User-facing UI, CLI, errors, defaults, or public APIs | `../delight-users/SKILL.md` |
| Limits, timeouts, batch/pool sizes, or thresholds | `../no-picked-constants/SKILL.md` |
| Waiting, polling loops, sleeps, timers, or CI checks | `../event-driven/SKILL.md` |
| Speedups, memory cuts, or approximate/deferred variants | `../never-trade-functionality/SKILL.md` |
| Writing, reviewing, or fixing any test or flake | `../tests-assert-behaviour/SKILL.md` |
