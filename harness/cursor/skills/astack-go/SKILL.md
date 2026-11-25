---
name: astack-go
description: "Single entry point for astack—ALWAYS load this skill before doing any code review, PR review, PR comment drafting, bug diagnosis, refactor, implementation, plan, test, benchmark, research, or catch-up task; routes on demand by path to all 70 hidden engineering workflows and coding-rule skills so only one skill sits in context."
---

# Go mode

You are running in astack Go mode. Every other astack skill is hidden from the model catalog to keep session context small; a missing catalog entry does **not** mean astack is absent, and calling a `Skill` tool on hidden skills will fail. Always load any matching skill directly with your file-reading tool (`Read` / `read_file` / `cat`) before acting on its trigger, and cite only skills or coding rules whose `SKILL.md` you actually read this session.

Skill files live beside this one at `../<name>/SKILL.md` (and `astack-tools skills-dir` prints the exact absolute `skills/` directory from any shell). Never guess a skill's instructions from the one-line summary below—read the file first when it applies. Whenever spawning any worker, reviewer, or researcher subagent, put the **resolved absolute path** to the astack `skills/` directory (never a relative `..` path) on line 1 of its brief so the subagent can read hidden skills immediately.

Run the astack scripts (`astack-status`, `astack-verify-merge`, `astack-check-gates`, `astack-review-ledger`, `astack-dispatch`, `astack-watch-pr`, `astack-watch-github`, `astack-watch-gitlab`, `astack-watch-bitbucket`, `astack-stamp`, `astack-decisions`, `astack-statechart`, `astack-tools`) from `PATH` (once `/astack-setup` links them into `~/.local/bin`) or directly from `../../bin/`.

## Startup

1. Read `~/.config/astack/settings.json` (or `$XDG_CONFIG_HOME/astack/settings.json`) if present: timing (`worker_minutes`, `reviewer_minutes`, `researcher_minutes`, `wind_down_minutes`, `check_in_minutes`, defaults `60 / 30 / 30 / 5 / 5`, falling back to `worker_minutes` if per-role limits are unset), per-role `provider`, `model`, `effort`, and optional `harness` (`lead`, `worker`, `researcher`, defaulting to the active session when `"default"` or unset), `reviewer_pool` (the user-approved list of `{provider, model, effort}` reviewer models with optional `harness`—which also decides which vendors see the code; treat the active session model as a 1-model pool if unset), `autonomy` (`mode`: `"supervised"` default vs `"unattended"`, plus explicit `allow`/`deny` boundaries honored per **decisions-in-plain-words**), and `automation.mode` (`agentic-only` default vs `python-stack` with managed `uv` venv). Apply configured provider/model/effort/harness, `autonomy` boundaries, and per-role time limits / check-ins when dispatching workers, reviewers, and researchers (using the host subagent tool when supported natively, or `astack-dispatch run` across `claude`, `codex`, `agy`, `cursor-agent`/`agent`, `devin`, `pi`, `gemini`, or custom CLIs when cross-harness or cross-provider; report any unreachable approved model rather than silently substituting), and default to pure-agentic workflows when `automation.mode` is `agentic-only`.
2. Route immediately based on what the person asked for—don't pause to ask for permission before reading the matching skill(s). When verifying a worker's branch/claim or checking whether a branch is safe to merge, read `../astack-lead/SKILL.md` and run `astack-check-gates <base>..<head>` / `astack-verify-merge` structurally (plus **review** for semantic/risk checks) rather than only skimming diffs by eye.
3. Follow astack's core sequence on all engineering work: **work -> robust -> fast**, verify on the real system, inspect repo/PR/linked context before asking (**rtfm**), settle technical questions yourself with evidence and log why, state contradictions and issues plainly (**wat**), and interrupt the person only for genuine human calls.

## Subagents

You own orchestration, planning, verification, and the final reply—delegate isolated implementation, adversarial review, and wide research to astack's dedicated subagents rather than generic subagents (which skip astack's contracts and drift). Enforce configured time limits (`worker_minutes`, `reviewer_minutes`, `researcher_minutes`, `wind_down_minutes`) and `check_in_minutes` check-ins across **all** spawned workers, reviewers, and researchers (stamping UTC `Started / Wind down at / End by` into briefs, passing `--settings`/`--timeout` to `astack-dispatch run`, reminding at wind-down, and stopping/replacing past-limit agents).

- **Lead (`astack-lead`), Workers (`astack-worker`), Reviewers (`astack-reviewer`), and Researchers (`astack-researcher`):**
- **Workers (`astack-worker`):** For multi-task dependency graphs, plan with **dagify** and run parallel lanes with **lead** (or delegate to `astack-lead` for full multi-lane program coordination). Workers must implement in isolated **Slates VFS volumes** (preferred when available) or **git worktrees** (and reviewers testing reproductions or proposed fixes must use isolated **Slates VFS volumes** or **throwaway scratch worktrees**). For any delegated code-writing task, isolated fix, or parallel worktree variant in Go mode, spawn the `astack-worker` subagent in the background with a brief naming the resolved absolute path to the astack `skills/` directory (parent of this skill's folder, or `astack-tools skills-dir`—never relative `..`), `Deliverable`, `Done when`, `Writable paths`, checks, and `roles.worker.model` from settings when set (or dispatch via `astack-dispatch run --role worker` when cross-harness or cross-provider). Never substitute `generalPurpose`.
- **Reviewers (`astack-reviewer`):** Whenever running **review**, checking a **dagify** plan, or gating a change before landing, spawn the `astack-reviewer` subagent in the background with the resolved absolute path to the astack `skills/` directory (parent of this skill's folder, or `astack-tools skills-dir`—never relative `..`), scope/diff, assigned vector, stated intent, reproduction folder, and the assigned `reviewer_pool` entry's `model` from settings (using `astack-reviewer` when Cursor can reach that model natively, or `astack-dispatch run` when cross-harness or unsupported; report any unreachable model rather than substituting). Never substitute `generalPurpose`. Follow **review**'s vectored dispatch everywhere reviewers are used: gather PR/issue/discussion/ADR linked context first (**rtfm**), enforce astack's coding rules and disciplines, classify vectors by risk (triggers: shared interfaces, concurrency, persistence, auth/security, or a large diff; add a `seams` vector via **blast-radius** when sliced), start risky vectors with at least two blind reviewers on different models from `reviewer_pool` and low-risk vectors with one (using a non-worker model when the pool allows, with no cap), enforce `reviewer_minutes` / `wind_down_minutes` / `check_in_minutes`, verify as findings arrive without voting, merge overlaps by fix-equivalence rather than wording, stop per vector over proven blocking bugs only using `astack-review-ledger`'s observable-class saturation check (exact hypergeometric lower/upper bounds at 2 reviewers; Burnham–Overton $M_h$ jackknife + Beta-Binomial $M_h$ interval from 3 on; empirical catch-rate calibration from `scripts/eval.py --calibrate` rather than guessed detection rates on clean sweeps), deepen small-pool risky vectors with executable adversarial checks (**full-spectrum-testing** / **formal-validate**) before escalating, hold landing on non-saturated risky changes for a plain-language human decision, state defects and contradictions plainly without lazy questions, and never leak internal review-ledger status to the user.
- **Researchers (`astack-researcher`):** Spawn the dedicated read-only `astack-researcher` subagent (applying `roles.researcher`, `researcher_minutes`, `wind_down_minutes`, and `check_in_minutes` from settings when set, or `astack-dispatch run --role researcher` when cross-harness) for wide codebase walks (**how-it-works**, **blast-radius**, **rearchitect**) and primary-source external lookups (**research-this**, **rtfm**).
- **Fresh subagents by default:** Dispatch new tasks, fix rounds, and retries to a fresh subagent with consolidated scope (original brief, directives, prior report, and branch/SHA) rather than resuming stale turns.

## Workflow playbooks

Read the matching skill file(s) before starting:

- **Configure timing and per-role models/effort:** `../astack-setup/SKILL.md`
- **Plan and run multi-step work (DAG -> workflow or parallel workers):** plan a reviewed dependency graph with `../dagify/SKILL.md`, automate unattended/recurring graphs with `../workflow-this/SKILL.md`, or dispatch ready DAG tasks to parallel workers with `../astack-lead/SKILL.md` (and sync issues via `../track-it/SKILL.md`)
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
  - Fair cross-system / competitor benchmarks and baselines: `../baseline/SKILL.md`
  - Settle design/config choices by measurement: `../decide-by-data/SKILL.md`
  - Run isolated worktree A/B tests and graft winning parts: `../ab-test/SKILL.md`
  - Step-by-step performance optimization: `../clamber/SKILL.md`
  - Build competing architectures in parallel, graft best ideas, keep winner: `../swarm-hypothesis/SKILL.md`
- **Test, verify, and prove:**
  - Verify claims against the real artifact (not proxies) on the trust ladder with runnable proof: `../prove-it/SKILL.md`
  - Confirm bugs on real user scenarios, narrow root causes (binary search/bisect, live dumps, profiles, built-in/astack/third-party tools, screenshots, OTel-traced HTTP/2/3, Playwright, `<file>_DEBUG_<shorthash>.<type>`), and shrink repros: `../find-it/SKILL.md`
  - Apply disciplined, minimal, behavior-proven bug fixes (desired/expected matrix, state/concurrency rules, system/perf impact, before/after proof): `../fix-it/SKILL.md`
  - Lead-only bugbash: swarm read-only reviewers with `find-it` and peer `challenge` to converge on root cause and fix options, implement via `fix-it`, and verify with `prove-it` + PR proof attachment: `../bugbash/SKILL.md`
  - Full-spectrum acceptance tests across the test diamond: `../full-spectrum-testing/SKILL.md`
  - Build or update a `drive-<app>` live user-flow verification skill: `../test-drive/SKILL.md`
  - Formal verification (TLA+, code verifiers, generated checks): `../formal-validate/SKILL.md`
- **Refactor, review, and ship PRs:**
  - Trace indirect breakage beyond a diff: `../blast-radius/SKILL.md`
  - Trim unnecessary code and complexity: `../simplify-me/SKILL.md`
  - Split monoliths via reviewed POC, `dagify`-batched migration, and `simplify-me`/`yagni` trim: `../modularize/SKILL.md`
  - Find structural friction in high-churn areas and plan restructuring: `../rearchitect/SKILL.md`
  - Adversarial multi-reviewer audit: `../astack-review/SKILL.md` and `../adversarial-review/SKILL.md`
  - Draft, independently audit via a second reviewer agent, and post human-facing PR review comments: `../leave-feedback/SKILL.md`
  - Refute wrong or unproven review points with evidence: `../worrywart/SKILL.md`
  - Resolve every review finding and PR thread: `../address-feedback/SKILL.md`
  - Shepherd a reviewed PR through CI and feedback: `../watch-pr/SKILL.md`
  - Fix unrelated broken tests/builds/CI in a separate PR: `../leave-it-better/SKILL.md`
- **Communicate, document, automate, and wrap up:**
  - Decide what you can, log it, escalate only real human calls: `../decisions-in-plain-words/SKILL.md`
  - Rewrite unclear/jargon-heavy output cleanly: `../wat/SKILL.md`
  - Write or update concrete, verified documentation: `../technical-writing/SKILL.md`
  - Replace repeated commands/polling with scripts and watchers: `../automate-this/SKILL.md`
  - Author/manage async/shell tasks, watchers, durable SQLite checkpoints, and pause/resume (`taskex`): `../taskex/SKILL.md`
  - Author/manage dependency-graph (DAG) wave pipelines with durable checkpoints and workflow/step pause/resume (`orchestral`): `../orchestral/SKILL.md`
  - Author/manage modular DAG workflows and integrations (`werkflow` + `werkflow-modules`): `../werkflow/SKILL.md`
  - Save, instrument, or inspect durable `taskex` / `orchestral` checkpoints: `../checkpoint/SKILL.md`
  - Suspend (pause) active `taskex` runs/schedules or `orchestral` workflows/steps cleanly: `../suspend/SKILL.md`
  - Resume paused runs/workflows/steps or recover crashed/failed runs from checkpoints: `../resume/SKILL.md`
  - Remove temp files, debug logs/captures (`<file>_DEBUG_<shorthash>.<type>`), build artifacts, and leftover processes (post-review and during/after debugging): `../cleanup/SKILL.md`
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
| Secrets, tokens, PII, logging, errors, telemetry, or debug dumps | `../no-leaked-secrets/SKILL.md` |
| Writing, reviewing, or fixing any test or flake | `../tests-assert-behaviour/SKILL.md` |
