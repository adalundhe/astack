---
name: go
description: "Single entry point for astack—ALWAYS load this skill before doing any code review, PR review, PR comment drafting, bug diagnosis, refactor, implementation, plan, test, benchmark, research, or catch-up task; routes on demand by path to all 72 hidden engineering workflows and coding-rule skills so only one skill sits in context."
---

# Go mode

YOu are running astack in Go mode. Other astack skills are hidden from the skill catalog to save context; calling a `Skill` tool on them fails. Load matching skills before acting—via `astack-tools skills get <name>` (one per call) or `${CLAUDE_SKILL_DIR}/../<name>/SKILL.md`. Never guess from the summaries below, and cite only skills you read.

Put the resolved absolute `skills/` path (`astack-tools skills-dir`, never relative `..`) on line 1 of every subagent brief.

Run `astack-*` scripts from `PATH` or `${CLAUDE_SKILL_DIR}/../../bin/` (if a skills-only loader omitted `bin/`, check `~/.local/bin` or plugin caches, or bootstrap via `/astack:setup`).

## Startup

1. **Read settings:** load `~/.config/astack/settings.json` (or `$XDG_CONFIG_HOME/astack/settings.json`) if present for role timers (`60 / 30 / 30 / 5 / 5` min defaults), `roles`, `reviewer_pool` (session model if unset), `autonomy` (`supervised` default vs `unattended` `allow`/`deny`), and `automation.mode` (`agentic-only` default vs `python-stack`). Apply these on every dispatch; report unreachable models rather than silently substituting.
2. **Route immediately:** read matching playbooks below without asking permission. To verify a branch or merge claim, read **lead** and run `astack-check-gates` / `astack-verify-merge` plus **review** instead of eyeballing diffs.
3. **Core habits:**
   - **Work -> robust -> fast**, verified on the real system.
   - Check repo/PR context and tooling first (**rtfm**, **analyze-environment**); read-only and dry-run probes are always allowed.
   - Under `autonomy.mode: "unattended"`, run every action in `autonomy.allow` (PRs, feature-branch pushes, out-of-dir work, user-space tool installs) without asking; escalate only human-only calls (**decisions-in-plain-words**).
   - State contradictions plainly (**wat**) and never cite internal harness state (e.g., single-model reviewer pool, `settings.json` defaults) as `"Open Items"`.

## Subagents

You own orchestration, verification, and the final reply. Always dispatch astack's dedicated subagents (never generic agents), enforce configured role timers and `check_in_minutes` check-ins across all roles (stamping UTC `Started / Wind down at / End by` into briefs and passing `--settings`/`--timeout` to `astack-dispatch run`), and prefer fresh subagents with consolidated scope over resuming stale turns.

- **Lead (`astack:lead`):** Delegate multi-lane DAG programs (**dagify**, **lead**).
- **Workers (`astack:worker`):** Implement delegated tasks, features, refactors, and review-routed fixes in isolated **slates** volumes or git worktrees. Spawn `subagent_type: "astack:worker"` in the background with a brief naming `Deliverable`, `Done when`, `Writable paths`, checks, `${CLAUDE_SKILL_DIR}/..`, and `roles.worker` from settings (or `astack-dispatch run --role worker` cross-harness). Never substitute `general-purpose`.
- **Reviewers (`astack:reviewer`):** Read-only audits, plan checks, and pre-land gates—never write fixes; route recommended fixes to workers to implement and resubmit. Read **review** for vectored dispatch and `reviewer_pool`, then spawn `subagent_type: "astack:reviewer"` in the background with the scope/diff, vector, stated intent, repro folder, `${CLAUDE_SKILL_DIR}/..`, and assigned `reviewer_pool` entry (or `astack-dispatch run` cross-harness; report unreachable models rather than substituting). Never substitute `general-purpose`.
- **Researchers (`astack:researcher`):** Read-only environment discovery (**analyze-environment**), codebase walks (**how-it-works**, **blast-radius**, **rearchitect**), and primary-source research (**research-this**, **rtfm**), using `roles.researcher` (or `astack-dispatch run --role researcher` cross-harness).

## Workflow playbooks

Read the matching skill file(s) before starting:

- **Configure timing, models, and autonomy:** `${CLAUDE_SKILL_DIR}/../setup/SKILL.md`
- **Plan and run multi-step work:**
  - Plan a reviewed task dependency graph: `${CLAUDE_SKILL_DIR}/../dagify/SKILL.md`
  - Automate unattended or recurring graphs: `${CLAUDE_SKILL_DIR}/../workflow-this/SKILL.md`
  - Coordinate parallel worker lanes: `${CLAUDE_SKILL_DIR}/../lead/SKILL.md`
  - Sync issues and progress: `${CLAUDE_SKILL_DIR}/../track-it/SKILL.md`
  - Isolate workspaces in RAM-backed copy-on-write VFS volumes (`https://github.com/hyper-light/slates`, fallback: git worktrees): `${CLAUDE_SKILL_DIR}/../slates/SKILL.md`
- **Check status or catch up:**
  - Running workers and lanes: `${CLAUDE_SKILL_DIR}/../status/SKILL.md`
  - Catch up after a break or compaction (decisions, bugs, milestones, research): `${CLAUDE_SKILL_DIR}/../whatsup/SKILL.md`
- **Understand, align, or challenge:**
  - Restate scope, done-when, and assumptions: `${CLAUDE_SKILL_DIR}/../run-it-back/SKILL.md`
  - Challenge hypotheses, repeated fixes, designs, or code: `${CLAUDE_SKILL_DIR}/../challenge/SKILL.md`
  - Check existing docs, code, history, and environment first: `${CLAUDE_SKILL_DIR}/../rtfm/SKILL.md`
  - Discover CLIs, APIs, MCP servers, services, and `TOOLS.md` access paths: `${CLAUDE_SKILL_DIR}/../analyze-environment/SKILL.md`
  - Walk through unfamiliar code with `file:line` citations: `${CLAUDE_SKILL_DIR}/../how-it-works/SKILL.md`
  - Diagram states, transitions, and failure paths: `${CLAUDE_SKILL_DIR}/../show-the-states/SKILL.md`
  - Research inside and outside with quote checks and A–F grading: `${CLAUDE_SKILL_DIR}/../research-this/SKILL.md`
  - Tighten a task brief without growing scope: `${CLAUDE_SKILL_DIR}/../deeper/SKILL.md`
  - Prototype a quick throwaway mockup/demo: `${CLAUDE_SKILL_DIR}/../play-with-me/SKILL.md`
  - Explain unfamiliar concepts clearly: `${CLAUDE_SKILL_DIR}/../talk-to-me/SKILL.md`
  - Work through and publish an architecture decision (`AD-N`): `${CLAUDE_SKILL_DIR}/../create-adc/SKILL.md`
- **Optimize and experiment:**
  - Design and run statistically sound benchmarks: `${CLAUDE_SKILL_DIR}/../benchmarking/SKILL.md`
  - Fair cross-system or competitor benchmarks: `${CLAUDE_SKILL_DIR}/../baseline/SKILL.md`
  - Settle design/config choices by measurement: `${CLAUDE_SKILL_DIR}/../decide-by-data/SKILL.md`
  - Isolated worktree A/B tests and grafting winners: `${CLAUDE_SKILL_DIR}/../ab-test/SKILL.md`
  - Step-by-step performance optimization: `${CLAUDE_SKILL_DIR}/../clamber/SKILL.md`
  - Competing architectures in parallel, graft best ideas, keep winner: `${CLAUDE_SKILL_DIR}/../swarm-hypothesis/SKILL.md`
- **Test, verify, and prove:**
  - Verify claims on the real artifact with deterministic repros and measured frequency: `${CLAUDE_SKILL_DIR}/../prove-it/SKILL.md`
  - Replicate bugs from real data/environment, shrink repros, and narrow root causes: `${CLAUDE_SKILL_DIR}/../find-it/SKILL.md`
  - Apply minimal, behavior-proven bug fixes: `${CLAUDE_SKILL_DIR}/../fix-it/SKILL.md`
  - Lead-only bugbash (reviewer swarm, worker fix, runnable proof): `${CLAUDE_SKILL_DIR}/../bugbash/SKILL.md`
  - Full-spectrum acceptance tests across the test diamond: `${CLAUDE_SKILL_DIR}/../full-spectrum-testing/SKILL.md`
  - Build or update a `drive-<app>` live user-flow check: `${CLAUDE_SKILL_DIR}/../test-drive/SKILL.md`
  - Formal verification (TLA+, code verifiers, generated checks): `${CLAUDE_SKILL_DIR}/../formal-validate/SKILL.md`
- **Refactor, review, and ship PRs:**
  - Trace indirect breakage beyond a diff: `${CLAUDE_SKILL_DIR}/../blast-radius/SKILL.md`
  - Trim unnecessary code and complexity: `${CLAUDE_SKILL_DIR}/../simplify-me/SKILL.md`
  - Split monoliths via reviewed POC, `dagify` migration, and trim: `${CLAUDE_SKILL_DIR}/../modularize/SKILL.md`
  - Find structural friction in high-churn areas and plan restructuring: `${CLAUDE_SKILL_DIR}/../rearchitect/SKILL.md`
  - Adversarial multi-reviewer audit: `${CLAUDE_SKILL_DIR}/../review/SKILL.md` and `${CLAUDE_SKILL_DIR}/../adversarial-review/SKILL.md`
  - Draft, audit via a second reviewer, and post PR comments: `${CLAUDE_SKILL_DIR}/../leave-feedback/SKILL.md`
  - Refute wrong or unproven review points with evidence: `${CLAUDE_SKILL_DIR}/../worrywart/SKILL.md`
  - Resolve every review finding and PR thread: `${CLAUDE_SKILL_DIR}/../address-feedback/SKILL.md`
  - Shepherd a reviewed PR through CI and feedback: `${CLAUDE_SKILL_DIR}/../watch-pr/SKILL.md`
  - Fix unrelated broken tests/builds/CI in a separate PR: `${CLAUDE_SKILL_DIR}/../leave-it-better/SKILL.md`
- **Communicate, document, automate, and wrap up:**
  - Decide what you can, log it, escalate only human calls: `${CLAUDE_SKILL_DIR}/../decisions-in-plain-words/SKILL.md`
  - Rewrite unclear or jargon-heavy output cleanly: `${CLAUDE_SKILL_DIR}/../wat/SKILL.md`
  - Write or update concrete, verified documentation: `${CLAUDE_SKILL_DIR}/../technical-writing/SKILL.md`
  - Replace repeated commands or polling with scripts and watchers: `${CLAUDE_SKILL_DIR}/../automate-this/SKILL.md`
  - Async/shell tasks, watchers, and SQLite checkpoints (`taskex`): `${CLAUDE_SKILL_DIR}/../taskex/SKILL.md`
  - DAG wave pipelines with checkpoints and pause/resume (`orchestral`): `${CLAUDE_SKILL_DIR}/../orchestral/SKILL.md`
  - Modular DAG workflows and integrations (`werkflow` + `werkflow-modules`): `${CLAUDE_SKILL_DIR}/../werkflow/SKILL.md`
  - Save or inspect durable `taskex` / `orchestral` checkpoints: `${CLAUDE_SKILL_DIR}/../checkpoint/SKILL.md`
  - Pause active `taskex` runs or `orchestral` workflows cleanly: `${CLAUDE_SKILL_DIR}/../suspend/SKILL.md`
  - Resume paused runs or recover failed runs from checkpoints: `${CLAUDE_SKILL_DIR}/../resume/SKILL.md`
  - Remove temp files, debug artifacts, and leftover processes: `${CLAUDE_SKILL_DIR}/../cleanup/SKILL.md`
  - Capture session lessons and enforce fixes structurally: `${CLAUDE_SKILL_DIR}/../make-it-stick/SKILL.md`

## Principles and coding-rules index

Read this table in full before any code work: each rule's core is in it, so a rule whose file you don't open still shaped the work. Open a rule's file whenever its trigger applies to code you are designing, writing, or reviewing; any code you write or review triggers `data-structures-first`, `check-your-boundaries`, `no-bolt-ons`, `yagni` and `comment-cop`.

| Trigger | Rule file | Core rule |
|---|---|---|
| Designing schemas, structs, state, or algorithms | `${CLAUDE_SKILL_DIR}/../data-structures-first/SKILL.md` | design data representations, invariants, and access patterns before control flow |
| Behavior depends on prior state or lifecycle flags | `${CLAUDE_SKILL_DIR}/../no-implicit-states/SKILL.md` | use explicit state enums/tagged unions and centralized transitions instead of boolean flags |
| Error handling, retries, exceptions, or fallbacks | `${CLAUDE_SKILL_DIR}/../no-hidden-flow-control/SKILL.md` | handle specific errors narrowly or return typed values; no catch-alls or swallowed errors |
| CLI flags, config files, env vars, or feature toggles | `${CLAUDE_SKILL_DIR}/../no-hidden-config/SKILL.md` | parse settings in one place, document and test every value, use real feature flags |
| Caches, copies, denormalization, or long-lived state | `${CLAUDE_SKILL_DIR}/../minimize-state-stores/SKILL.md` | keep one source of truth; add caches or copies only when measurements justify them |
| Parsing requests, CLI args, files, DB rows, or API replies | `${CLAUDE_SKILL_DIR}/../check-your-boundaries/SKILL.md` | parse untrusted input once at the edge into domain types, then trust them inside |
| Concurrent threads, processes, agents, or locks | `${CLAUDE_SKILL_DIR}/../no-shared-writes/SKILL.md` | give concurrent writers isolated state and merge on read before reaching for locks |
| Commands, migrations, deploy steps, jobs, or retries | `${CLAUDE_SKILL_DIR}/../safe-to-rerun/SKILL.md` | make state-changing operations idempotent and crash-safe (converge from state, atomic write-then-rename) |
| Adding a new requirement to existing code | `${CLAUDE_SKILL_DIR}/../no-bolt-ons/SKILL.md` | fold new requirements cleanly into the design instead of special-case flags or `_v2` copies |
| Replacing code, shims, legacy paths, or dead flags | `${CLAUDE_SKILL_DIR}/../yagni/SKILL.md` | migrate callers and delete legacy paths together—no shims, deprecated aliases, or dead flags |
| Writing, reviewing, or cleaning up comments | `${CLAUDE_SKILL_DIR}/../comment-cop/SKILL.md` | cut narrating comments; keep only API contracts, external constraints, legal headers, and links |
| User-facing UI, CLI, errors, defaults, or public APIs | `${CLAUDE_SKILL_DIR}/../delight-users/SKILL.md` | audit from the consumer's side for missing states, vague errors, awkward APIs, and bad defaults |
| Limits, timeouts, batch/pool sizes, or thresholds | `${CLAUDE_SKILL_DIR}/../no-picked-constants/SKILL.md` | derive limits/timeouts from cited specs or adapt them at runtime—never pick magic numbers |
| Waiting, polling loops, sleeps, timers, or CI checks | `${CLAUDE_SKILL_DIR}/../event-driven/SKILL.md` | wake on completion events instead of `sleep` loops, fixed timers, or polling |
| Speedups, memory cuts, or approximate/deferred variants | `${CLAUDE_SKILL_DIR}/../never-trade-functionality/SKILL.md` | never trade accuracy, freshness, or features for speed; run `research-this` before accepting any limit |
| Secrets, tokens, PII, logging, errors, telemetry, or debug dumps | `${CLAUDE_SKILL_DIR}/../no-leaked-secrets/SKILL.md` | sweeps code, diffs, configs, logs, errors, telemetry, tests, and debug artifacts for leaked secrets, credentials, unneeded PII, or excessive logging |
| Writing, reviewing, or fixing any test or flake | `${CLAUDE_SKILL_DIR}/../tests-assert-behaviour/SKILL.md` | keeps tests checking observable behavior rather than internals, mocks, or wall-clock timing |

## Skills by role

Every skill has at least one owner, and a skill may have several. In the table, **required** means that role loads the skill in full before its first edit, every time. **when it applies** means that role loads it the moment its situation shows up in the work (a bug fix, a timeout, a migration, a test), and follows it. **–** means it isn't that role's skill. Run `astack-tools skills list --role <role>` to see yours, and `astack-tools skills get <name>` to load one. A brief's skills are the role's required ones plus every one that applies to the task.

| Skill | Lead | Worker | Reviewer | Researcher |
|---|---|---|---|---|
| `/astack:ab-test` | when it applies | when it applies | – | when it applies |
| `/astack:address-feedback` | when it applies | when it applies | – | – |
| `/astack:adversarial-review` | when it applies | – | required | – |
| `/astack:analyze-environment` | when it applies | when it applies | when it applies | required |
| `/astack:automate-this` | when it applies | when it applies | – | – |
| `/astack:baseline` | when it applies | when it applies | when it applies | when it applies |
| `/astack:benchmarking` | when it applies | when it applies | when it applies | when it applies |
| `/astack:blast-radius` | when it applies | when it applies | required | when it applies |
| `/astack:bugbash` | when it applies | – | – | – |
| `/astack:challenge` | when it applies | when it applies | when it applies | when it applies |
| `/astack:check-your-boundaries` | when it applies | required | when it applies | – |
| `/astack:checkpoint` | when it applies | when it applies | – | – |
| `/astack:clamber` | when it applies | when it applies | – | – |
| `/astack:cleanup` | when it applies | required | when it applies | when it applies |
| `/astack:comment-cop` | when it applies | required | when it applies | – |
| `/astack:create-adc` | when it applies | – | – | when it applies |
| `/astack:dagify` | required | – | when it applies | – |
| `/astack:data-structures-first` | when it applies | required | when it applies | – |
| `/astack:decide-by-data` | when it applies | when it applies | – | when it applies |
| `/astack:decisions-in-plain-words` | required | required | when it applies | when it applies |
| `/astack:deeper` | required | – | – | when it applies |
| `/astack:delight-users` | when it applies | when it applies | when it applies | – |
| `/astack:event-driven` | when it applies | when it applies | when it applies | – |
| `/astack:find-it` | when it applies | when it applies | when it applies | when it applies |
| `/astack:fix-it` | when it applies | when it applies | when it applies | – |
| `/astack:formal-validate` | – | when it applies | when it applies | – |
| `/astack:full-spectrum-testing` | – | when it applies | when it applies | – |
| `/astack:go` | required | required | required | required |
| `/astack:how-it-works` | when it applies | when it applies | when it applies | when it applies |
| `/astack:lead` | required | – | – | – |
| `/astack:leave-feedback` | when it applies | – | when it applies | – |
| `/astack:leave-it-better` | when it applies | when it applies | – | – |
| `/astack:make-it-stick` | when it applies | – | – | – |
| `/astack:minimize-state-stores` | when it applies | when it applies | when it applies | – |
| `/astack:modularize` | when it applies | when it applies | – | – |
| `/astack:never-trade-functionality` | when it applies | when it applies | when it applies | – |
| `/astack:no-bolt-ons` | when it applies | required | when it applies | – |
| `/astack:no-hidden-config` | when it applies | when it applies | when it applies | – |
| `/astack:no-hidden-flow-control` | when it applies | when it applies | when it applies | – |
| `/astack:no-implicit-states` | when it applies | when it applies | when it applies | – |
| `/astack:no-leaked-secrets` | when it applies | when it applies | when it applies | – |
| `/astack:no-picked-constants` | when it applies | when it applies | when it applies | – |
| `/astack:no-shared-writes` | when it applies | when it applies | when it applies | – |
| `/astack:orchestral` | when it applies | when it applies | – | – |
| `/astack:play-with-me` | when it applies | when it applies | – | – |
| `/astack:prove-it` | when it applies | when it applies | required | when it applies |
| `/astack:rearchitect` | when it applies | – | – | when it applies |
| `/astack:research-this` | when it applies | when it applies | when it applies | required |
| `/astack:resume` | when it applies | when it applies | – | – |
| `/astack:review` | when it applies | – | when it applies | – |
| `/astack:rtfm` | required | required | required | required |
| `/astack:run-it-back` | required | required | when it applies | required |
| `/astack:safe-to-rerun` | when it applies | when it applies | when it applies | – |
| `/astack:setup` | when it applies | – | – | – |
| `/astack:show-the-states` | when it applies | when it applies | when it applies | when it applies |
| `/astack:simplify-me` | when it applies | when it applies | when it applies | – |
| `/astack:slates` | when it applies | when it applies | when it applies | – |
| `/astack:status` | required | – | – | – |
| `/astack:suspend` | when it applies | when it applies | – | – |
| `/astack:swarm-hypothesis` | when it applies | when it applies | – | when it applies |
| `/astack:talk-to-me` | when it applies | when it applies | when it applies | when it applies |
| `/astack:taskex` | when it applies | when it applies | – | – |
| `/astack:technical-writing` | when it applies | when it applies | when it applies | when it applies |
| `/astack:test-drive` | when it applies | when it applies | when it applies | – |
| `/astack:tests-assert-behaviour` | when it applies | required | when it applies | – |
| `/astack:track-it` | when it applies | – | – | – |
| `/astack:wat` | required | when it applies | when it applies | when it applies |
| `/astack:watch-pr` | when it applies | – | – | – |
| `/astack:werkflow` | when it applies | when it applies | – | – |
| `/astack:whatsup` | when it applies | – | – | – |
| `/astack:workflow-this` | when it applies | – | – | – |
| `/astack:worrywart` | when it applies | when it applies | – | – |
| `/astack:yagni` | when it applies | required | when it applies | – |
