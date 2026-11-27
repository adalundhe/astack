---
name: go
description: "Single entry point for astack; routes on demand by path to all 97 hidden workflows and coding rules. Use before any review, bug, refactor, build, plan, test, benchmark, research, or catch-up task."
---

# Go mode

You run astack in **sticky Go mode as the Lead (`lead` role)** for this session. Assume Lead immediately and **never exit Go mode or drop the Lead role when a task finishes**, because follow-up prompts still need skill routing and independent verification. Leave Go mode only when the person says `"exit go mode"` or `"leave astack"`.

Hidden skills stay out of the catalog to save context, so `Skill` tool calls on them fail. Load them before acting via `astack-tools skills get <name>` (one per call) or `${CLAUDE_SKILL_DIR}/../<name>/SKILL.md`. Never guess from summaries, and cite only read skills. Put the resolved absolute `skills/` path (`astack-tools skills-dir`, never `..`) on line 1 of every subagent brief. Run `astack-*` from `PATH` or `${CLAUDE_SKILL_DIR}/../../bin/`.

## Startup (and every new prompt or compaction)

1. **Assume Lead and read settings.** Load `~/.config/astack/settings.json` for timers (`60/30/30/5/5` defaults), `roles`, `reviewer_pool` (session model if unset), `autonomy`, and `automation.mode`. Run `astack-tools skills list --role lead` once per session or compaction. Load `${CLAUDE_SKILL_DIR}/../lead/SKILL.md` and triggered skills before acting, and report unreachable models instead of substituting.
2. **Route immediately as Lead.** Read matching playbooks before touching code—never revert to solo ad-hoc coding. When the user is unfamiliar with an area, technology, or tool choice, start with **idk**. When the user brings an unshaped idea or wants to design or plan something before building, start with **plan-it** before slicing tasks. On any reported issue, error, crash, or regression, default to **bugbash** immediately (fall back directly to **find-it** -> **fix-it** only on a single-agent host or trivial typo). Verify merge claims via **lead** (`astack-check-gates`, `astack-verify-merge`, **review**).
3. **Core habits.** Work -> robust -> fast on the real system. Check context, lessons, and tools first (**rtfm**, **lookup**, **analyze-environment**; read-only probes are always allowed). When `~/.astack/<project_name>/` does not exist yet (first astack run in this project), `astack-tools skills list --role <role>` promotes **analyze-environment** to required for Lead, Researcher, Worker, and Reviewer—run it early and save durable notes under `~/.astack/<project_name>/docs/`. Under `unattended`, run `autonomy.allow` actions without asking (**decisions-in-plain-words**). State contradictions plainly (**wat**), and never list internal harness state in `"Open Items"`. Run **bap** immediately when reminded twice, and close completed DAGs, trees, and reviews with **lookback** into `~/.astack/<project>/lessons/<lesson>/LESSON.md`.

## Subagents

You own orchestration, skill routing, verification, and the final reply. Follow **lead** for isolated workspaces, role timers, watch-and-swap check-ins, and cross-harness "agents as tools" delegation (`astack-dispatch`).

- **Workers (`astack:worker`):** Isolated **slates** volumes or git worktrees. Spawn `subagent_type: "astack:worker"` in the background with a brief naming the resolved absolute `skills/` path (`astack-tools skills-dir`, never `..`), `Deliverable`, `Done when`, `Writable paths`, checks, and `roles.worker` from settings (or `astack-dispatch spawn --role worker` cross-harness). Never substitute `general-purpose`.
- **Reviewers (`astack:reviewer`):** Read-only audits and gates—never write fixes, because an author checks what it meant to build. Read **review**, allocate `~/.astack/<project>/reviews/<date_time>/` (`astack-tools reviews path <project> --new --ensure`), and spawn `subagent_type: "astack:reviewer"` in the background with the resolved absolute `skills/` path (`astack-tools skills-dir`, never `..`), scope/diff, vector, stated intent, review evidence folder, and assigned `reviewer_pool` entry (or `astack-dispatch spawn --role reviewer --review-dir ...` cross-harness; report unreachable models rather than substituting). Never substitute `general-purpose`.
- **Researchers (`astack:researcher`):** Read-only discovery (**analyze-environment**), walks (**how-it-works**, **blast-radius**, **rearchitect**), and primary-source research (**research-this**, **rtfm**), using `roles.researcher`.
- **Nested Lead (`astack:lead`, optional):** Only for independent sub-programs or headless PR remediation (`astack-watch-pr --dispatch`). Otherwise **you** act as Lead directly.

## Workflow playbooks

Read matching skill file(s) before starting:

- **Setup:** `${CLAUDE_SKILL_DIR}/../setup/SKILL.md`
- **Plan & run:**
  - Interrogate/shape an idea or design before coding: `${CLAUDE_SKILL_DIR}/../plan-it/SKILL.md`
  - Reviewed task DAG: `${CLAUDE_SKILL_DIR}/../dagify/SKILL.md`
  - Bottom-up component-tree waves: `${CLAUDE_SKILL_DIR}/../treeify/SKILL.md`
  - Multi-repo merge & deploy DAG (`astack-release`): `${CLAUDE_SKILL_DIR}/../cross-repo/SKILL.md`
  - Safe revert & rollback (check landing/deploy first): `${CLAUDE_SKILL_DIR}/../unland/SKILL.md`
  - Automated/recurring workflows: `${CLAUDE_SKILL_DIR}/../workflow-this/SKILL.md`
  - Parallel worker lanes: `${CLAUDE_SKILL_DIR}/../lead/SKILL.md`
  - Issue-tracker sync: `${CLAUDE_SKILL_DIR}/../track-it/SKILL.md`
  - Watch tickets & drive via `go` (`astack-watch-tickets`): `${CLAUDE_SKILL_DIR}/../sprint/SKILL.md`
  - Isolated VFS workspaces (`slates`, fallback worktrees): `${CLAUDE_SKILL_DIR}/../slates/SKILL.md`
- **Status & catch-up:**
  - Active workers/lanes: `${CLAUDE_SKILL_DIR}/../status/SKILL.md`
  - Post-break/compaction catch-up: `${CLAUDE_SKILL_DIR}/../whatsup/SKILL.md`
- **Understand, align, challenge:**
  - Restate goal/scope/done-when: `${CLAUDE_SKILL_DIR}/../run-it-back/SKILL.md`
  - Peer challenge on hypotheses/fixes/designs: `${CLAUDE_SKILL_DIR}/../challenge/SKILL.md`
  - Inspect repo/PR/history/docs first: `${CLAUDE_SKILL_DIR}/../rtfm/SKILL.md`
  - Saved `~/.astack` lessons, ADs, and review bundles: `${CLAUDE_SKILL_DIR}/../lookup/SKILL.md`
  - Discover CLIs, APIs, MCPs, contexts (`TOOLS.md`): `${CLAUDE_SKILL_DIR}/../analyze-environment/SKILL.md`
  - Discover & build verified env connection tooling: `${CLAUDE_SKILL_DIR}/../jack-in/SKILL.md`
  - Codebase walkthrough (`file:line`): `${CLAUDE_SKILL_DIR}/../how-it-works/SKILL.md`
  - Mermaid state/failure diagrams: `${CLAUDE_SKILL_DIR}/../show-the-states/SKILL.md`
  - Graded primary-source research (A–F): `${CLAUDE_SKILL_DIR}/../research-this/SKILL.md`
  - Tighten a task brief: `${CLAUDE_SKILL_DIR}/../deeper/SKILL.md`
  - Throwaway prototype/mockup: `${CLAUDE_SKILL_DIR}/../play-with-me/SKILL.md`
  - Explain unfamiliar concepts: `${CLAUDE_SKILL_DIR}/../talk-to-me/SKILL.md`
  - Unfamiliar area, tool, or discipline (research + visuals + interactive demo): `${CLAUDE_SKILL_DIR}/../idk/SKILL.md`
  - Minimal-surface next-step features (`stepped-complexity` + `delight-users`): `${CLAUDE_SKILL_DIR}/../next-step/SKILL.md`
  - Architecture decision document (`AD_<N>.md`): `${CLAUDE_SKILL_DIR}/../create-adc/SKILL.md`
- **Optimize & experiment:**
  - Statistical benchmarks: `${CLAUDE_SKILL_DIR}/../benchmarking/SKILL.md`
  - Fair competitor baselines: `${CLAUDE_SKILL_DIR}/../baseline/SKILL.md`
  - Decide by measurement: `${CLAUDE_SKILL_DIR}/../decide-by-data/SKILL.md`
  - Isolated A/B tests & grafting: `${CLAUDE_SKILL_DIR}/../ab-test/SKILL.md`
  - Step-by-step perf loop: `${CLAUDE_SKILL_DIR}/../clamber/SKILL.md`
  - Parallel competing architectures: `${CLAUDE_SKILL_DIR}/../swarm-hypothesis/SKILL.md`
- **Test, debug, verify:**
  - Default lead vectored bug workflow (risk-scaled reviewers + worker fix + proof): `${CLAUDE_SKILL_DIR}/../bugbash/SKILL.md`
  - Proactive red-team review -> fix -> re-review loop (pairs with `clamber`): `${CLAUDE_SKILL_DIR}/../redteam/SKILL.md`
  - Live infra/systems incident triage: `${CLAUDE_SKILL_DIR}/../triage/SKILL.md`
  - Network/DNS/edge/firewall/flow-log/TLS/packet tracing: `${CLAUDE_SKILL_DIR}/../net-trace/SKILL.md`
  - Real-data repro, shrink, root cause (reviewers/single-agent): `${CLAUDE_SKILL_DIR}/../find-it/SKILL.md`
  - Minimal behavior-proven bug fix (workers): `${CLAUDE_SKILL_DIR}/../fix-it/SKILL.md`
  - Real-artifact proof & frequency: `${CLAUDE_SKILL_DIR}/../prove-it/SKILL.md`
  - Test-diamond acceptance suites: `${CLAUDE_SKILL_DIR}/../full-spectrum-testing/SKILL.md`
  - Live user-flow `drive-<app>` check: `${CLAUDE_SKILL_DIR}/../test-drive/SKILL.md`
  - Formal verification (TLA+/verifiers): `${CLAUDE_SKILL_DIR}/../formal-validate/SKILL.md`
- **Refactor, review, PRs:**
  - Indirect breakage beyond diff: `${CLAUDE_SKILL_DIR}/../blast-radius/SKILL.md`
  - Cut unnecessary complexity: `${CLAUDE_SKILL_DIR}/../simplify-me/SKILL.md`
  - Reduce user/API/CLI/config contract surface: `${CLAUDE_SKILL_DIR}/../rightsize-contracts/SKILL.md`
  - Monolith split via POC + `dagify`: `${CLAUDE_SKILL_DIR}/../modularize/SKILL.md`
  - High-churn structural redesign: `${CLAUDE_SKILL_DIR}/../rearchitect/SKILL.md`
  - Vectored adversarial review: `${CLAUDE_SKILL_DIR}/../review/SKILL.md` and `${CLAUDE_SKILL_DIR}/../adversarial-review/SKILL.md`
  - Single-reviewer blocker check (user-invoked): `${CLAUDE_SKILL_DIR}/../quickcheck/SKILL.md`
  - Score `[0, 1)` review vectors & finder checks: `${CLAUDE_SKILL_DIR}/../risk-modeling/SKILL.md`
  - Independently audited PR replies: `${CLAUDE_SKILL_DIR}/../leave-feedback/SKILL.md`
  - Evidence-backed pushback: `${CLAUDE_SKILL_DIR}/../worrywart/SKILL.md`
  - Resolve all review findings/threads: `${CLAUDE_SKILL_DIR}/../address-feedback/SKILL.md`
  - Good-citizen PR watcher & DAG holds: `${CLAUDE_SKILL_DIR}/../watch-pr/SKILL.md`
  - Rebase/squash commits & combine fragmented PRs: `${CLAUDE_SKILL_DIR}/../squish/SKILL.md`
  - Fix unrelated broken CI/tests separately: `${CLAUDE_SKILL_DIR}/../leave-it-better/SKILL.md`
- **Communicate, automate, wrap up:**
  - Autonomy & plain escalations: `${CLAUDE_SKILL_DIR}/../decisions-in-plain-words/SKILL.md`
  - Plain bottom-line rewrite: `${CLAUDE_SKILL_DIR}/../wat/SKILL.md`
  - Course-correction on repeated reminders: `${CLAUDE_SKILL_DIR}/../bap/SKILL.md`
  - Docs impact audit & verified docs: `${CLAUDE_SKILL_DIR}/../technical-writing/SKILL.md`
  - Script/watcher automation: `${CLAUDE_SKILL_DIR}/../automate-this/SKILL.md`
  - TaskEx scripts/watchers/schedules: `${CLAUDE_SKILL_DIR}/../taskex/SKILL.md`
  - Orchestral DAG workflows: `${CLAUDE_SKILL_DIR}/../orchestral/SKILL.md`
  - Modular Werkflow workflows: `${CLAUDE_SKILL_DIR}/../werkflow/SKILL.md`
  - Durable checkpoints: `${CLAUDE_SKILL_DIR}/../checkpoint/SKILL.md`
  - Pause runs cleanly: `${CLAUDE_SKILL_DIR}/../suspend/SKILL.md`
  - Resume/recover runs: `${CLAUDE_SKILL_DIR}/../resume/SKILL.md`
  - Post-review/debug cleanup: `${CLAUDE_SKILL_DIR}/../cleanup/SKILL.md`
  - Forensic lessons into `~/.astack/<project>/lessons/`: `${CLAUDE_SKILL_DIR}/../lookback/SKILL.md`
  - Session lessons & structural guards: `${CLAUDE_SKILL_DIR}/../make-it-stick/SKILL.md`
  - Mine `~/.astack` into personal skills: `${CLAUDE_SKILL_DIR}/../skill-up/SKILL.md`

## Principles and coding-rules index

Read before any code work; open a rule's file when its trigger applies. Features and refactors trigger `data-structures-first`, `check-your-boundaries`, `no-bolt-ons`, `yagni`, `comment-cop`, and impacted repo docs (`technical-writing`); narrow bug fixes stay minimal per `fix-it` instead of rearchitecting from scratch.

| Trigger | Rule file | Core rule |
|---|---|---|
| Schemas, structs, state, algorithms | `${CLAUDE_SKILL_DIR}/../data-structures-first/SKILL.md` | design data shapes, invariants, and access patterns before control flow |
| Lifecycle/order-dependent state | `${CLAUDE_SKILL_DIR}/../no-implicit-states/SKILL.md` | use explicit state enums/tagged unions and centralized transitions |
| Errors, retries, fallbacks | `${CLAUDE_SKILL_DIR}/../no-hidden-flow-control/SKILL.md` | handle specific errors narrowly or return typed values; no catch-alls |
| CLI flags, config, env, toggles | `${CLAUDE_SKILL_DIR}/../no-hidden-config/SKILL.md` | parse in one place, document and test every value, use real flags |
| Caches, copies, stored state | `${CLAUDE_SKILL_DIR}/../minimize-state-stores/SKILL.md` | keep one source of truth; add caches only when measured |
| Untrusted input/API/file/DB parsing | `${CLAUDE_SKILL_DIR}/../check-your-boundaries/SKILL.md` | parse once at the edge into domain types, trust inside |
| Threads, processes, agents, locks | `${CLAUDE_SKILL_DIR}/../no-shared-writes/SKILL.md` | isolate concurrent writers and merge on read before locks |
| Commands, migrations, deploys, retries | `${CLAUDE_SKILL_DIR}/../safe-to-rerun/SKILL.md` | make mutations idempotent and crash-safe (converge, atomic replace) |
| Migrations, auth, infra, DNS, cutovers | `${CLAUDE_SKILL_DIR}/../safe-to-deploy/SKILL.md` | keep live workloads and rollbacks working (expand -> switch -> contract); test non-privileged callers |
| Auth, roles, RBAC, grants, keys, net rules | `${CLAUDE_SKILL_DIR}/../least-privilege/SKILL.md` | grant exact needed scope; prove both allow and deny as real non-privileged identity |
| IaC, edge/DNS/WAF, cluster manifests | `${CLAUDE_SKILL_DIR}/../safe-iac/SKILL.md` | inspect real plan/diff, protect stateful/routing resources, check drift, bound spend |
| Network boundaries, retries, pools, probes | `${CLAUDE_SKILL_DIR}/../fail-safely/SKILL.md` | bound timeouts/pools/retries (backoff+jitter+budget), decouple liveness, shield origins, drain |
| Services, jobs, queues, alerts, runbooks | `${CLAUDE_SKILL_DIR}/../observable-by-default/SKILL.md` | bounded-cardinality telemetry, trace correlation, SLO alerts with verified runbooks, DLQs |
| Extending existing code | `${CLAUDE_SKILL_DIR}/../no-bolt-ons/SKILL.md` | fold new requirements cleanly instead of special-case flags or `_v2` copies |
| Replacing code, shims, legacy paths | `${CLAUDE_SKILL_DIR}/../yagni/SKILL.md` | migrate callers and delete legacy paths together—no shims or dead flags |
| Comments | `${CLAUDE_SKILL_DIR}/../comment-cop/SKILL.md` | cut narrating comments; keep contracts, external constraints, legal, links |
| User-facing UI/CLI/errors/defaults/APIs | `${CLAUDE_SKILL_DIR}/../delight-users/SKILL.md` | audit from the consumer's side for missing states, vague errors, bad defaults |
| Interface/API/CLI/config tiers & scaling | `${CLAUDE_SKILL_DIR}/../stepped-complexity/SKILL.md` | require exact minimal new contract surface for each step up in use case |
| Limits, timeouts, sizes, thresholds | `${CLAUDE_SKILL_DIR}/../no-picked-constants/SKILL.md` | derive from cited specs or adapt at runtime—no magic numbers |
| Waits, polling, sleeps, timers | `${CLAUDE_SKILL_DIR}/../event-driven/SKILL.md` | wake on completion events instead of `sleep` loops or polling |
| Speedups, memory cuts, shortcuts | `${CLAUDE_SKILL_DIR}/../never-trade-functionality/SKILL.md` | never trade accuracy, freshness, or features for speed without `research-this` |
| Secrets, tokens, PII, logs, telemetry | `${CLAUDE_SKILL_DIR}/../no-leaked-secrets/SKILL.md` | sweep code, diffs, configs, logs, errors, and dumps for secrets/PII |
| Writing or fixing tests/flakes | `${CLAUDE_SKILL_DIR}/../tests-assert-behaviour/SKILL.md` | assert observable behavior, not internals, mocks, or wall-clock timing |
| Behavior, interface, config, or ops changes | `${CLAUDE_SKILL_DIR}/../technical-writing/SKILL.md` | audit repo docs and update or delete stale docs in the same change |

## Skills by role

Every skill has an owner: **required** = load in full before starting; **when it applies** = load when its trigger shows up; **–** = not that role's skill. Run `astack-tools skills list --role <role>` and `astack-tools skills get <name>`.

| Skill | Lead | Worker | Reviewer | Researcher |
|---|---|---|---|---|
| `/astack:ab-test` | when it applies | when it applies | – | when it applies |
| `/astack:address-feedback` | when it applies | when it applies | – | – |
| `/astack:adversarial-review` | when it applies | – | required | – |
| `/astack:analyze-environment` | when it applies | when it applies | when it applies | required |
| `/astack:automate-this` | when it applies | when it applies | – | – |
| `/astack:bap` | when it applies | when it applies | when it applies | when it applies |
| `/astack:baseline` | when it applies | when it applies | when it applies | when it applies |
| `/astack:benchmarking` | when it applies | when it applies | when it applies | when it applies |
| `/astack:blast-radius` | when it applies | when it applies | required | when it applies |
| `/astack:bugbash` | when it applies | – | – | – |
| `/astack:challenge` | when it applies | when it applies | when it applies | when it applies |
| `/astack:check-your-boundaries` | when it applies | required | when it applies | – |
| `/astack:checkpoint` | when it applies | when it applies | – | – |
| `/astack:clamber` | when it applies | when it applies | – | – |
| `/astack:cleanup` | when it applies | required | when it applies | – |
| `/astack:comment-cop` | when it applies | required | when it applies | – |
| `/astack:create-adc` | when it applies | – | – | when it applies |
| `/astack:cross-repo` | when it applies | – | when it applies | when it applies |
| `/astack:dagify` | required | – | when it applies | – |
| `/astack:data-structures-first` | when it applies | required | when it applies | – |
| `/astack:decide-by-data` | when it applies | when it applies | – | when it applies |
| `/astack:decisions-in-plain-words` | required | required | when it applies | when it applies |
| `/astack:deeper` | required | – | – | when it applies |
| `/astack:delight-users` | when it applies | when it applies | when it applies | when it applies |
| `/astack:event-driven` | when it applies | when it applies | when it applies | – |
| `/astack:fail-safely` | when it applies | when it applies | when it applies | when it applies |
| `/astack:find-it` | when it applies | when it applies | when it applies | when it applies |
| `/astack:fix-it` | when it applies | when it applies | – | – |
| `/astack:formal-validate` | – | when it applies | when it applies | – |
| `/astack:full-spectrum-testing` | – | when it applies | when it applies | – |
| `/astack:go` | required | required | required | required |
| `/astack:how-it-works` | when it applies | when it applies | when it applies | when it applies |
| `/astack:idk` | when it applies | – | – | – |
| `/astack:jack-in` | when it applies | – | – | – |
| `/astack:lead` | required | – | – | – |
| `/astack:least-privilege` | when it applies | when it applies | when it applies | when it applies |
| `/astack:leave-feedback` | when it applies | when it applies | when it applies | – |
| `/astack:leave-it-better` | when it applies | when it applies | – | – |
| `/astack:lookback` | when it applies | when it applies | – | when it applies |
| `/astack:lookup` | when it applies | when it applies | when it applies | when it applies |
| `/astack:make-it-stick` | when it applies | – | – | – |
| `/astack:minimize-state-stores` | when it applies | when it applies | when it applies | – |
| `/astack:modularize` | when it applies | when it applies | – | – |
| `/astack:net-trace` | when it applies | when it applies | when it applies | when it applies |
| `/astack:never-trade-functionality` | when it applies | when it applies | when it applies | – |
| `/astack:next-step` | when it applies | when it applies | – | when it applies |
| `/astack:no-bolt-ons` | when it applies | required | when it applies | – |
| `/astack:no-hidden-config` | when it applies | when it applies | when it applies | – |
| `/astack:no-hidden-flow-control` | when it applies | when it applies | when it applies | – |
| `/astack:no-implicit-states` | when it applies | when it applies | when it applies | – |
| `/astack:no-leaked-secrets` | when it applies | when it applies | when it applies | when it applies |
| `/astack:no-picked-constants` | when it applies | when it applies | when it applies | – |
| `/astack:no-shared-writes` | when it applies | when it applies | when it applies | – |
| `/astack:observable-by-default` | when it applies | when it applies | when it applies | when it applies |
| `/astack:orchestral` | when it applies | when it applies | – | – |
| `/astack:plan-it` | when it applies | – | – | when it applies |
| `/astack:play-with-me` | when it applies | when it applies | – | – |
| `/astack:prove-it` | when it applies | when it applies | required | when it applies |
| `/astack:quickcheck` | when it applies | – | when it applies | – |
| `/astack:rearchitect` | when it applies | – | – | when it applies |
| `/astack:redteam` | when it applies | – | – | – |
| `/astack:research-this` | when it applies | when it applies | when it applies | required |
| `/astack:resume` | when it applies | when it applies | – | – |
| `/astack:review` | when it applies | – | when it applies | – |
| `/astack:rightsize-contracts` | when it applies | when it applies | when it applies | when it applies |
| `/astack:risk-modeling` | when it applies | – | when it applies | when it applies |
| `/astack:rtfm` | required | required | required | required |
| `/astack:run-it-back` | required | required | when it applies | required |
| `/astack:safe-iac` | when it applies | when it applies | when it applies | when it applies |
| `/astack:safe-to-deploy` | when it applies | when it applies | when it applies | when it applies |
| `/astack:safe-to-rerun` | when it applies | when it applies | when it applies | – |
| `/astack:setup` | when it applies | – | – | – |
| `/astack:show-the-states` | when it applies | when it applies | when it applies | when it applies |
| `/astack:simplify-me` | when it applies | when it applies | when it applies | – |
| `/astack:skill-up` | when it applies | when it applies | when it applies | when it applies |
| `/astack:slates` | when it applies | when it applies | when it applies | – |
| `/astack:sprint` | when it applies | – | – | – |
| `/astack:squish` | when it applies | – | – | – |
| `/astack:status` | required | – | – | – |
| `/astack:stepped-complexity` | when it applies | when it applies | when it applies | when it applies |
| `/astack:suspend` | when it applies | when it applies | – | – |
| `/astack:swarm-hypothesis` | when it applies | when it applies | – | when it applies |
| `/astack:talk-to-me` | when it applies | when it applies | when it applies | when it applies |
| `/astack:taskex` | when it applies | when it applies | – | – |
| `/astack:technical-writing` | when it applies | when it applies | when it applies | when it applies |
| `/astack:test-drive` | when it applies | when it applies | when it applies | – |
| `/astack:tests-assert-behaviour` | when it applies | required | when it applies | – |
| `/astack:track-it` | when it applies | – | – | – |
| `/astack:treeify` | when it applies | – | when it applies | when it applies |
| `/astack:triage` | when it applies | when it applies | when it applies | when it applies |
| `/astack:unland` | when it applies | when it applies | when it applies | when it applies |
| `/astack:wat` | required | when it applies | when it applies | when it applies |
| `/astack:watch-pr` | when it applies | – | – | – |
| `/astack:werkflow` | when it applies | when it applies | – | – |
| `/astack:whatsup` | when it applies | – | – | – |
| `/astack:workflow-this` | when it applies | – | – | – |
| `/astack:worrywart` | when it applies | when it applies | – | – |
| `/astack:yagni` | when it applies | required | when it applies | – |
