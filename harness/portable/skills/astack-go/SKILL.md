---
name: astack-go
description: "Single entry point for astack—ALWAYS load this skill before doing any code review, PR review, PR comment drafting, bug diagnosis, refactor, implementation, plan, test, benchmark, research, or catch-up task; routes on demand by path to all 72 hidden engineering workflows and coding-rule skills so only one skill sits in context."
---

# Go mode

You are running astack in Go mode. Other astack skills are hidden from the skill catalog to save context; calling a `Skill` tool on them fails. Load matching skills before acting—via `astack-tools skills get <name>` (one per call) or `../<name>/SKILL.md`. Never guess from the summaries below, and cite only skills you read.

Put the resolved absolute `skills/` path (`astack-tools skills-dir`, never relative `..`) on line 1 of every subagent brief.

Run `astack-*` scripts from `PATH` or `../../bin/` (if a skills-only loader omitted `bin/`, check `~/.local/bin` or plugin caches, or bootstrap via `/astack-setup`).

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

- **Lead (`astack-lead`):** Delegate multi-lane DAG programs (**dagify**, **lead**).
- **Workers (`astack-worker`):** Implement delegated tasks, features, refactors, and review-routed fixes in isolated **slates** volumes or git worktrees. Spawn a dedicated worker using your host's subagent tool with `agents/astack-worker.md` (or `astack-dispatch run --role worker` cross-harness/CLI-only) with a brief naming the resolved absolute `skills/` path (`astack-tools skills-dir`, never relative `..`), `Deliverable`, `Done when`, `Writable paths`, checks, and `roles.worker` from settings. Never substitute an unconfigured generic agent.
- **Reviewers (`astack-reviewer`):** Read-only audits, plan checks, and pre-land gates—never write fixes; route recommended fixes to workers to implement and resubmit. Read **review** for vectored dispatch and `reviewer_pool`, then dispatch a dedicated reviewer using your host's subagent tool with `agents/astack-reviewer.md` (when supported natively) or `astack-dispatch run --role reviewer` (cross-harness/CLI-only; report unreachable models rather than substituting) with the resolved absolute `skills/` path (`astack-tools skills-dir`, never relative `..`), scope/diff, vector, stated intent, repro folder, and assigned `reviewer_pool` entry. Never substitute an unconfigured generic agent.
- **Researchers (`astack-researcher`):** Read-only environment discovery (**analyze-environment**), codebase walks (**how-it-works**, **blast-radius**, **rearchitect**), and primary-source research (**research-this**, **rtfm**), using `roles.researcher` (or `astack-dispatch run --role researcher` cross-harness).

## Workflow playbooks

Read the matching skill file(s) before starting:

- **Configure timing, models, and autonomy:** `../astack-setup/SKILL.md`
- **Plan and run multi-step work:**
  - Plan a reviewed task dependency graph: `../dagify/SKILL.md`
  - Automate unattended or recurring graphs: `../workflow-this/SKILL.md`
  - Coordinate parallel worker lanes: `../astack-lead/SKILL.md`
  - Sync issues and progress: `../track-it/SKILL.md`
  - Isolate workspaces in RAM-backed copy-on-write VFS volumes (`https://github.com/hyper-light/slates`, fallback: git worktrees): `../slates/SKILL.md`
- **Check status or catch up:**
  - Running workers and lanes: `../astack-status/SKILL.md`
  - Catch up after a break or compaction (decisions, bugs, milestones, research): `../whatsup/SKILL.md`
- **Understand, align, or challenge:**
  - Restate scope, done-when, and assumptions: `../run-it-back/SKILL.md`
  - Challenge hypotheses, repeated fixes, designs, or code: `../challenge/SKILL.md`
  - Check existing docs, code, history, and environment first: `../rtfm/SKILL.md`
  - Discover CLIs, APIs, MCP servers, services, and `TOOLS.md` access paths: `../analyze-environment/SKILL.md`
  - Walk through unfamiliar code with `file:line` citations: `../how-it-works/SKILL.md`
  - Diagram states, transitions, and failure paths: `../show-the-states/SKILL.md`
  - Research inside and outside with quote checks and A–F grading: `../research-this/SKILL.md`
  - Tighten a task brief without growing scope: `../deeper/SKILL.md`
  - Prototype a quick throwaway mockup/demo: `../play-with-me/SKILL.md`
  - Explain unfamiliar concepts clearly: `../talk-to-me/SKILL.md`
  - Work through and publish an architecture decision (`AD-N`): `../create-adc/SKILL.md`
- **Optimize and experiment:**
  - Design and run statistically sound benchmarks: `../benchmarking/SKILL.md`
  - Fair cross-system or competitor benchmarks: `../baseline/SKILL.md`
  - Settle design/config choices by measurement: `../decide-by-data/SKILL.md`
  - Isolated worktree A/B tests and grafting winners: `../ab-test/SKILL.md`
  - Step-by-step performance optimization: `../clamber/SKILL.md`
  - Competing architectures in parallel, graft best ideas, keep winner: `../swarm-hypothesis/SKILL.md`
- **Test, verify, and prove:**
  - Verify claims on the real artifact with deterministic repros and measured frequency: `../prove-it/SKILL.md`
  - Replicate bugs from real data/environment, shrink repros, and narrow root causes: `../find-it/SKILL.md`
  - Apply minimal, behavior-proven bug fixes: `../fix-it/SKILL.md`
  - Lead-only bugbash (reviewer swarm, worker fix, runnable proof): `../bugbash/SKILL.md`
  - Full-spectrum acceptance tests across the test diamond: `../full-spectrum-testing/SKILL.md`
  - Build or update a `drive-<app>` live user-flow check: `../test-drive/SKILL.md`
  - Formal verification (TLA+, code verifiers, generated checks): `../formal-validate/SKILL.md`
- **Refactor, review, and ship PRs:**
  - Trace indirect breakage beyond a diff: `../blast-radius/SKILL.md`
  - Trim unnecessary code and complexity: `../simplify-me/SKILL.md`
  - Split monoliths via reviewed POC, `dagify` migration, and trim: `../modularize/SKILL.md`
  - Find structural friction in high-churn areas and plan restructuring: `../rearchitect/SKILL.md`
  - Adversarial multi-reviewer audit: `../astack-review/SKILL.md` and `../adversarial-review/SKILL.md`
  - Draft, audit via a second reviewer, and post PR comments: `../leave-feedback/SKILL.md`
  - Refute wrong or unproven review points with evidence: `../worrywart/SKILL.md`
  - Resolve every review finding and PR thread: `../address-feedback/SKILL.md`
  - Shepherd a reviewed PR through CI and feedback: `../watch-pr/SKILL.md`
  - Fix unrelated broken tests/builds/CI in a separate PR: `../leave-it-better/SKILL.md`
- **Communicate, document, automate, and wrap up:**
  - Decide what you can, log it, escalate only human calls: `../decisions-in-plain-words/SKILL.md`
  - Rewrite unclear or jargon-heavy output cleanly: `../wat/SKILL.md`
  - Write or update concrete, verified documentation: `../technical-writing/SKILL.md`
  - Replace repeated commands or polling with scripts and watchers: `../automate-this/SKILL.md`
  - Async/shell tasks, watchers, and SQLite checkpoints (`taskex`): `../taskex/SKILL.md`
  - DAG wave pipelines with checkpoints and pause/resume (`orchestral`): `../orchestral/SKILL.md`
  - Modular DAG workflows and integrations (`werkflow` + `werkflow-modules`): `../werkflow/SKILL.md`
  - Save or inspect durable `taskex` / `orchestral` checkpoints: `../checkpoint/SKILL.md`
  - Pause active `taskex` runs or `orchestral` workflows cleanly: `../suspend/SKILL.md`
  - Resume paused runs or recover failed runs from checkpoints: `../resume/SKILL.md`
  - Remove temp files, debug artifacts, and leftover processes: `../cleanup/SKILL.md`
  - Capture session lessons and enforce fixes structurally: `../make-it-stick/SKILL.md`

## Principles and coding-rules index

Read this table in full before any code work: each rule's core is in it, so a rule whose file you don't open still shaped the work. Open a rule's file whenever its trigger applies to code you are designing, writing, or reviewing; any code you write or review triggers `data-structures-first`, `check-your-boundaries`, `no-bolt-ons`, `yagni` and `comment-cop`.

| Trigger | Rule file | Core rule |
|---|---|---|
| Designing schemas, structs, state, or algorithms | `../data-structures-first/SKILL.md` | design data representations, invariants, and access patterns before control flow |
| Behavior depends on prior state or lifecycle flags | `../no-implicit-states/SKILL.md` | use explicit state enums/tagged unions and centralized transitions instead of boolean flags |
| Error handling, retries, exceptions, or fallbacks | `../no-hidden-flow-control/SKILL.md` | handle specific errors narrowly or return typed values; no catch-alls or swallowed errors |
| CLI flags, config files, env vars, or feature toggles | `../no-hidden-config/SKILL.md` | parse settings in one place, document and test every value, use real feature flags |
| Caches, copies, denormalization, or long-lived state | `../minimize-state-stores/SKILL.md` | keep one source of truth; add caches or copies only when measurements justify them |
| Parsing requests, CLI args, files, DB rows, or API replies | `../check-your-boundaries/SKILL.md` | parse untrusted input once at the edge into domain types, then trust them inside |
| Concurrent threads, processes, agents, or locks | `../no-shared-writes/SKILL.md` | give concurrent writers isolated state and merge on read before reaching for locks |
| Commands, migrations, deploy steps, jobs, or retries | `../safe-to-rerun/SKILL.md` | make state-changing operations idempotent and crash-safe (converge from state, atomic write-then-rename) |
| Adding a new requirement to existing code | `../no-bolt-ons/SKILL.md` | fold new requirements cleanly into the design instead of special-case flags or `_v2` copies |
| Replacing code, shims, legacy paths, or dead flags | `../yagni/SKILL.md` | migrate callers and delete legacy paths together—no shims, deprecated aliases, or dead flags |
| Writing, reviewing, or cleaning up comments | `../comment-cop/SKILL.md` | cut narrating comments; keep only API contracts, external constraints, legal headers, and links |
| User-facing UI, CLI, errors, defaults, or public APIs | `../delight-users/SKILL.md` | audit from the consumer's side for missing states, vague errors, awkward APIs, and bad defaults |
| Limits, timeouts, batch/pool sizes, or thresholds | `../no-picked-constants/SKILL.md` | derive limits/timeouts from cited specs or adapt them at runtime—never pick magic numbers |
| Waiting, polling loops, sleeps, timers, or CI checks | `../event-driven/SKILL.md` | wake on completion events instead of `sleep` loops, fixed timers, or polling |
| Speedups, memory cuts, or approximate/deferred variants | `../never-trade-functionality/SKILL.md` | never trade accuracy, freshness, or features for speed; run `research-this` before accepting any limit |
| Secrets, tokens, PII, logging, errors, telemetry, or debug dumps | `../no-leaked-secrets/SKILL.md` | sweeps code, diffs, configs, logs, errors, telemetry, tests, and debug artifacts for leaked secrets, credentials, unneeded PII, or excessive logging |
| Writing, reviewing, or fixing any test or flake | `../tests-assert-behaviour/SKILL.md` | keeps tests checking observable behavior rather than internals, mocks, or wall-clock timing |

## Skills by role

Every skill has at least one owner, and a skill may have several. In the table, **required** means that role loads the skill in full before its first edit, every time. **when it applies** means that role loads it the moment its situation shows up in the work (a bug fix, a timeout, a migration, a test), and follows it. **–** means it isn't that role's skill. Run `astack-tools skills list --role <role>` to see yours, and `astack-tools skills get <name>` to load one. A brief's skills are the role's required ones plus every one that applies to the task.

| Skill | Lead | Worker | Reviewer | Researcher |
|---|---|---|---|---|
| `/ab-test` | when it applies | when it applies | – | when it applies |
| `/address-feedback` | when it applies | when it applies | – | – |
| `/adversarial-review` | when it applies | – | required | – |
| `/analyze-environment` | when it applies | when it applies | when it applies | required |
| `/automate-this` | when it applies | when it applies | – | – |
| `/baseline` | when it applies | when it applies | when it applies | when it applies |
| `/benchmarking` | when it applies | when it applies | when it applies | when it applies |
| `/blast-radius` | when it applies | when it applies | required | when it applies |
| `/bugbash` | when it applies | – | – | – |
| `/challenge` | when it applies | when it applies | when it applies | when it applies |
| `/check-your-boundaries` | when it applies | required | when it applies | – |
| `/checkpoint` | when it applies | when it applies | – | – |
| `/clamber` | when it applies | when it applies | – | – |
| `/cleanup` | when it applies | required | when it applies | when it applies |
| `/comment-cop` | when it applies | required | when it applies | – |
| `/create-adc` | when it applies | – | – | when it applies |
| `/dagify` | required | – | when it applies | – |
| `/data-structures-first` | when it applies | required | when it applies | – |
| `/decide-by-data` | when it applies | when it applies | – | when it applies |
| `/decisions-in-plain-words` | required | required | when it applies | when it applies |
| `/deeper` | required | – | – | when it applies |
| `/delight-users` | when it applies | when it applies | when it applies | – |
| `/event-driven` | when it applies | when it applies | when it applies | – |
| `/find-it` | when it applies | when it applies | when it applies | when it applies |
| `/fix-it` | when it applies | when it applies | when it applies | – |
| `/formal-validate` | – | when it applies | when it applies | – |
| `/full-spectrum-testing` | – | when it applies | when it applies | – |
| `/astack-go` | required | required | required | required |
| `/how-it-works` | when it applies | when it applies | when it applies | when it applies |
| `/astack-lead` | required | – | – | – |
| `/leave-feedback` | when it applies | – | when it applies | – |
| `/leave-it-better` | when it applies | when it applies | – | – |
| `/make-it-stick` | when it applies | – | – | – |
| `/minimize-state-stores` | when it applies | when it applies | when it applies | – |
| `/modularize` | when it applies | when it applies | – | – |
| `/never-trade-functionality` | when it applies | when it applies | when it applies | – |
| `/no-bolt-ons` | when it applies | required | when it applies | – |
| `/no-hidden-config` | when it applies | when it applies | when it applies | – |
| `/no-hidden-flow-control` | when it applies | when it applies | when it applies | – |
| `/no-implicit-states` | when it applies | when it applies | when it applies | – |
| `/no-leaked-secrets` | when it applies | when it applies | when it applies | – |
| `/no-picked-constants` | when it applies | when it applies | when it applies | – |
| `/no-shared-writes` | when it applies | when it applies | when it applies | – |
| `/orchestral` | when it applies | when it applies | – | – |
| `/play-with-me` | when it applies | when it applies | – | – |
| `/prove-it` | when it applies | when it applies | required | when it applies |
| `/rearchitect` | when it applies | – | – | when it applies |
| `/research-this` | when it applies | when it applies | when it applies | required |
| `/resume` | when it applies | when it applies | – | – |
| `/astack-review` | when it applies | – | when it applies | – |
| `/rtfm` | required | required | required | required |
| `/run-it-back` | required | required | when it applies | required |
| `/safe-to-rerun` | when it applies | when it applies | when it applies | – |
| `/astack-setup` | when it applies | – | – | – |
| `/show-the-states` | when it applies | when it applies | when it applies | when it applies |
| `/simplify-me` | when it applies | when it applies | when it applies | – |
| `/slates` | when it applies | when it applies | when it applies | – |
| `/astack-status` | required | – | – | – |
| `/suspend` | when it applies | when it applies | – | – |
| `/swarm-hypothesis` | when it applies | when it applies | – | when it applies |
| `/talk-to-me` | when it applies | when it applies | when it applies | when it applies |
| `/taskex` | when it applies | when it applies | – | – |
| `/technical-writing` | when it applies | when it applies | when it applies | when it applies |
| `/test-drive` | when it applies | when it applies | when it applies | – |
| `/tests-assert-behaviour` | when it applies | required | when it applies | – |
| `/track-it` | when it applies | – | – | – |
| `/wat` | required | when it applies | when it applies | when it applies |
| `/watch-pr` | when it applies | – | – | – |
| `/werkflow` | when it applies | when it applies | – | – |
| `/whatsup` | when it applies | – | – | – |
| `/workflow-this` | when it applies | – | – | – |
| `/worrywart` | when it applies | when it applies | – | – |
| `/yagni` | when it applies | required | when it applies | – |
