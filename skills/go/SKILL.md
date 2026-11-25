---
name: go
description: "Single entry point for astack—ALWAYS load this skill before doing any code review, PR review, PR comment drafting, bug or error investigation, refactor, implementation, plan, test, benchmark, research, or catch-up task; routes on demand by path to all 87 hidden engineering workflows and coding-rule skills so only one skill sits in context."
---

# Go mode

You are running astack in **sticky Go mode as the Lead (`lead` role)** for this session. Assume Lead immediately and **never exit Go mode or drop the Lead role when a task finishes**. Every follow-up prompt (and post-compaction turn) starts a fresh Lead routing pass until the person says `"exit go mode"` or `"leave astack"`.

Hidden skills are omitted from the catalog to save context (a `Skill` tool call on them fails). Load them before acting via `astack-tools skills get <name>` (one per call) or `${CLAUDE_SKILL_DIR}/../<name>/SKILL.md`. Never guess from summaries; cite only read skills. Put the resolved absolute `skills/` path (`astack-tools skills-dir`, never `..`) on line 1 of every subagent brief. Run `astack-*` from `PATH` or `${CLAUDE_SKILL_DIR}/../../bin/` (or bootstrap via `/astack:setup`).

## Startup (and every new prompt or compaction)

1. **Assume Lead & read settings:** load `~/.config/astack/settings.json` (or `$XDG_CONFIG_HOME/astack/settings.json`) for timers (`60/30/30/5/5` min defaults), `roles`, `reviewer_pool` (session model if unset), `autonomy` (`supervised` vs `unattended` `allow`/`deny`), and `automation.mode`. Run `astack-tools skills list --role lead` once per session/compaction and load `${CLAUDE_SKILL_DIR}/../lead/SKILL.md` plus triggered skills before acting; report unreachable models rather than substituting.
2. **Route immediately as Lead:** on every prompt, read matching playbooks before touching code—never revert to solo ad-hoc coding/debugging. On any reported issue, error, crash, or regression, default to **bugbash** immediately (don't solo-debug with **find-it**/**rtfm** when subagents exist; fall back directly to **find-it** -> **fix-it** only for a single-agent host or trivial typo). Verify merge claims via **lead** (`astack-check-gates` / `astack-verify-merge` + **review**).
3. **Core habits:** **work -> robust -> fast** on the real system; inspect context, memories, and tools first (**rtfm**, **lookup**, **analyze-environment**; read-only/dry-run probes always allowed); under `unattended`, execute `autonomy.allow` actions without asking (**decisions-in-plain-words**); state contradictions plainly (**wat**), never list internal harness state in `"Open Items"`, run **bap** immediately when the person repeats a reminder or correction, and close completed DAG workflows, component trees, and review sessions with **lookback** into `~/.astack/<project>/lessons/<lesson>/LESSON.md`.

## Subagents

**You are the Lead:** you own orchestration, skill routing, verification, and the final reply. Always dispatch astack's dedicated subagents (never generic ones), enforce role timers and `check_in_minutes` check-ins (UTC `Started / Wind down at / End by` in briefs; `--settings`/`--timeout` on `astack-dispatch`), and prefer fresh subagents over stale resumes. Treat external-harness CLIs (`codex`, `claude`, `agy`, `cursor`, `devin`, `pi`, `gemini`) as **delegated tools ("agents as tools")** via `astack-dispatch spawn` / `batch` / `status` / `wait` / `kill` (never shell `&`): never halt when native agents finish while cross-harness runs remain active.

- **Workers (`astack:worker`):** Isolated **slates** volumes or git worktrees. Spawn `subagent_type: "astack:worker"` in the background with a brief naming `Deliverable`, `Done when`, `Writable paths`, checks, `${CLAUDE_SKILL_DIR}/..`, and `roles.worker` from settings (or `astack-dispatch run --role worker` cross-harness). Never substitute `general-purpose`.
- **Reviewers (`astack:reviewer`):** Read-only audits/gates—never write fixes; route fixes to workers. Read **review** for vectored dispatch and `reviewer_pool`, then spawn `subagent_type: "astack:reviewer"` in the background with the scope/diff, vector, stated intent, repro folder, `${CLAUDE_SKILL_DIR}/..`, and assigned `reviewer_pool` entry (or `astack-dispatch run` cross-harness; report unreachable models rather than substituting). Never substitute `general-purpose`.
- **Researchers (`astack:researcher`):** Read-only discovery (**analyze-environment**), walks (**how-it-works**, **blast-radius**, **rearchitect**), and primary-source research (**research-this**, **rtfm**), using `roles.researcher` (or `astack-dispatch run --role researcher`).
- **Nested Lead (`astack:lead`, optional):** Only for independent sub-programs or headless PR remediation (`astack-watch-pr --dispatch`); otherwise **you** act as Lead directly (**dagify**, **treeify**, **cross-repo**, **triage**, **bugbash**, **redteam**, **sprint**, **lead**).

## Workflow playbooks

Read matching skill file(s) before starting:

- **Setup:** `${CLAUDE_SKILL_DIR}/../setup/SKILL.md`
- **Plan & run:**
  - Reviewed task DAG: `${CLAUDE_SKILL_DIR}/../dagify/SKILL.md`
  - Bottom-up component-tree waves: `${CLAUDE_SKILL_DIR}/../treeify/SKILL.md`
  - Multi-repo PR merge & deploy DAG (`astack-release`): `${CLAUDE_SKILL_DIR}/../cross-repo/SKILL.md`
  - Automated/recurring workflows: `${CLAUDE_SKILL_DIR}/../workflow-this/SKILL.md`
  - Parallel worker lanes: `${CLAUDE_SKILL_DIR}/../lead/SKILL.md`
  - Issue-tracker sync: `${CLAUDE_SKILL_DIR}/../track-it/SKILL.md`
  - Watch GitHub/Jira/Linear tickets & drive via `go` (`astack-watch-tickets`): `${CLAUDE_SKILL_DIR}/../sprint/SKILL.md`
  - Isolated VFS workspaces (`slates`, fallback worktrees): `${CLAUDE_SKILL_DIR}/../slates/SKILL.md`
- **Status & catch-up:**
  - Active workers/lanes: `${CLAUDE_SKILL_DIR}/../status/SKILL.md`
  - Post-break/compaction catch-up: `${CLAUDE_SKILL_DIR}/../whatsup/SKILL.md`
- **Understand, align, challenge:**
  - Restate goal/scope/done-when: `${CLAUDE_SKILL_DIR}/../run-it-back/SKILL.md`
  - Peer challenge on hypotheses/fixes/designs: `${CLAUDE_SKILL_DIR}/../challenge/SKILL.md`
  - Inspect repo/PR/history/docs first: `${CLAUDE_SKILL_DIR}/../rtfm/SKILL.md`
  - Consult saved `~/.astack` `LESSON.md` memories, cross-repo discovery & best paths: `${CLAUDE_SKILL_DIR}/../lookup/SKILL.md`
  - Discover CLIs, APIs, MCPs, contexts (`TOOLS.md`): `${CLAUDE_SKILL_DIR}/../analyze-environment/SKILL.md`
  - Codebase walkthrough (`file:line`): `${CLAUDE_SKILL_DIR}/../how-it-works/SKILL.md`
  - Mermaid state/failure diagrams: `${CLAUDE_SKILL_DIR}/../show-the-states/SKILL.md`
  - Graded primary-source research (A–F): `${CLAUDE_SKILL_DIR}/../research-this/SKILL.md`
  - Tighten a task brief: `${CLAUDE_SKILL_DIR}/../deeper/SKILL.md`
  - Throwaway prototype/mockup: `${CLAUDE_SKILL_DIR}/../play-with-me/SKILL.md`
  - Explain unfamiliar concepts: `${CLAUDE_SKILL_DIR}/../talk-to-me/SKILL.md`
  - Architecture decision record (`AD-N`): `${CLAUDE_SKILL_DIR}/../create-adc/SKILL.md`
- **Optimize & experiment:**
  - Statistical benchmarks: `${CLAUDE_SKILL_DIR}/../benchmarking/SKILL.md`
  - Fair competitor baselines: `${CLAUDE_SKILL_DIR}/../baseline/SKILL.md`
  - Decide by measurement: `${CLAUDE_SKILL_DIR}/../decide-by-data/SKILL.md`
  - Isolated A/B tests & grafting: `${CLAUDE_SKILL_DIR}/../ab-test/SKILL.md`
  - Step-by-step perf loop: `${CLAUDE_SKILL_DIR}/../clamber/SKILL.md`
  - Parallel competing architectures: `${CLAUDE_SKILL_DIR}/../swarm-hypothesis/SKILL.md`
- **Test, debug, verify:**
  - Default lead bug workflow (reviewer swarm + worker fix + proof): `${CLAUDE_SKILL_DIR}/../bugbash/SKILL.md`
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
  - Monolith split via POC + `dagify`: `${CLAUDE_SKILL_DIR}/../modularize/SKILL.md`
  - High-churn structural redesign: `${CLAUDE_SKILL_DIR}/../rearchitect/SKILL.md`
  - Vectored adversarial review: `${CLAUDE_SKILL_DIR}/../review/SKILL.md` and `${CLAUDE_SKILL_DIR}/../adversarial-review/SKILL.md`
  - Independently audited PR replies: `${CLAUDE_SKILL_DIR}/../leave-feedback/SKILL.md`
  - Evidence-backed pushback: `${CLAUDE_SKILL_DIR}/../worrywart/SKILL.md`
  - Resolve all review findings/threads: `${CLAUDE_SKILL_DIR}/../address-feedback/SKILL.md`
  - Good-citizen PR watcher & DAG holds: `${CLAUDE_SKILL_DIR}/../watch-pr/SKILL.md`
  - Rebase/squash commits & combine fragmented PRs: `${CLAUDE_SKILL_DIR}/../squish/SKILL.md`
  - Fix unrelated broken CI/tests separately: `${CLAUDE_SKILL_DIR}/../leave-it-better/SKILL.md`
- **Communicate, automate, wrap up:**
  - Autonomy & plain escalations: `${CLAUDE_SKILL_DIR}/../decisions-in-plain-words/SKILL.md`
  - Plain bottom-line rewrite: `${CLAUDE_SKILL_DIR}/../wat/SKILL.md`
  - Immediate course-correction on repeated reminders: `${CLAUDE_SKILL_DIR}/../bap/SKILL.md`
  - Docs impact audit & verified docs: `${CLAUDE_SKILL_DIR}/../technical-writing/SKILL.md`
  - Script/watcher automation: `${CLAUDE_SKILL_DIR}/../automate-this/SKILL.md`
  - Async tasks & SQLite checkpoints (`taskex`): `${CLAUDE_SKILL_DIR}/../taskex/SKILL.md`
  - DAG wave pipelines (`orchestral`): `${CLAUDE_SKILL_DIR}/../orchestral/SKILL.md`
  - Modular DAG workflows (`werkflow`): `${CLAUDE_SKILL_DIR}/../werkflow/SKILL.md`
  - Durable checkpoints: `${CLAUDE_SKILL_DIR}/../checkpoint/SKILL.md`
  - Pause runs cleanly: `${CLAUDE_SKILL_DIR}/../suspend/SKILL.md`
  - Resume/recover runs: `${CLAUDE_SKILL_DIR}/../resume/SKILL.md`
  - Post-review/debug cleanup: `${CLAUDE_SKILL_DIR}/../cleanup/SKILL.md`
  - Deep forensic review of past chats/tickets/deploys into `~/.astack/<project>/lessons/<lesson>/LESSON.md`: `${CLAUDE_SKILL_DIR}/../lookback/SKILL.md`
  - Session lessons & structural guards: `${CLAUDE_SKILL_DIR}/../make-it-stick/SKILL.md`

## Principles and coding-rules index

Read before any code work; open a rule's file when its trigger applies. Any code written or reviewed triggers `data-structures-first`, `check-your-boundaries`, `no-bolt-ons`, `yagni`, `comment-cop`, and checking impacted repo docs (`technical-writing`).

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
| Limits, timeouts, sizes, thresholds | `${CLAUDE_SKILL_DIR}/../no-picked-constants/SKILL.md` | derive from cited specs or adapt at runtime—no magic numbers |
| Waits, polling, sleeps, timers | `${CLAUDE_SKILL_DIR}/../event-driven/SKILL.md` | wake on completion events instead of `sleep` loops or polling |
| Speedups, memory cuts, shortcuts | `${CLAUDE_SKILL_DIR}/../never-trade-functionality/SKILL.md` | never trade accuracy, freshness, or features for speed without `research-this` |
| Secrets, tokens, PII, logs, telemetry | `${CLAUDE_SKILL_DIR}/../no-leaked-secrets/SKILL.md` | sweep code, diffs, configs, logs, errors, and dumps for secrets/PII |
| Writing or fixing tests/flakes | `${CLAUDE_SKILL_DIR}/../tests-assert-behaviour/SKILL.md` | assert observable behavior, not internals, mocks, or wall-clock timing |
| Behavior, interface, config, or ops changes | `${CLAUDE_SKILL_DIR}/../technical-writing/SKILL.md` | audit repo docs and update or delete stale docs in the same change |

## Skills by role

Every skill has an owner: **required** = load in full before first edit; **when it applies** = load when its trigger shows up; **–** = not that role's skill. Run `astack-tools skills list --role <role>` and `astack-tools skills get <name>`.

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
| `/astack:cleanup` | when it applies | required | when it applies | when it applies |
| `/astack:comment-cop` | when it applies | required | when it applies | – |
| `/astack:create-adc` | when it applies | – | – | when it applies |
| `/astack:cross-repo` | when it applies | – | when it applies | when it applies |
| `/astack:dagify` | required | – | when it applies | – |
| `/astack:data-structures-first` | when it applies | required | when it applies | – |
| `/astack:decide-by-data` | when it applies | when it applies | – | when it applies |
| `/astack:decisions-in-plain-words` | required | required | when it applies | when it applies |
| `/astack:deeper` | required | – | – | when it applies |
| `/astack:delight-users` | when it applies | when it applies | when it applies | – |
| `/astack:event-driven` | when it applies | when it applies | when it applies | – |
| `/astack:fail-safely` | when it applies | when it applies | when it applies | when it applies |
| `/astack:find-it` | – | when it applies | when it applies | when it applies |
| `/astack:fix-it` | – | when it applies | when it applies | when it applies |
| `/astack:formal-validate` | – | when it applies | when it applies | – |
| `/astack:full-spectrum-testing` | – | when it applies | when it applies | – |
| `/astack:go` | required | required | required | required |
| `/astack:how-it-works` | when it applies | when it applies | when it applies | when it applies |
| `/astack:lead` | required | – | – | – |
| `/astack:least-privilege` | when it applies | when it applies | when it applies | when it applies |
| `/astack:leave-feedback` | when it applies | – | when it applies | – |
| `/astack:leave-it-better` | when it applies | when it applies | – | – |
| `/astack:lookback` | when it applies | when it applies | – | when it applies |
| `/astack:lookup` | when it applies | when it applies | when it applies | when it applies |
| `/astack:make-it-stick` | when it applies | – | – | – |
| `/astack:minimize-state-stores` | when it applies | when it applies | when it applies | – |
| `/astack:modularize` | when it applies | when it applies | – | – |
| `/astack:net-trace` | when it applies | when it applies | when it applies | when it applies |
| `/astack:never-trade-functionality` | when it applies | when it applies | when it applies | – |
| `/astack:no-bolt-ons` | when it applies | required | when it applies | – |
| `/astack:no-hidden-config` | when it applies | when it applies | when it applies | – |
| `/astack:no-hidden-flow-control` | when it applies | when it applies | when it applies | – |
| `/astack:no-implicit-states` | when it applies | when it applies | when it applies | – |
| `/astack:no-leaked-secrets` | when it applies | when it applies | when it applies | – |
| `/astack:no-picked-constants` | when it applies | when it applies | when it applies | – |
| `/astack:no-shared-writes` | when it applies | when it applies | when it applies | – |
| `/astack:observable-by-default` | when it applies | when it applies | when it applies | when it applies |
| `/astack:orchestral` | when it applies | when it applies | – | – |
| `/astack:play-with-me` | when it applies | when it applies | – | – |
| `/astack:prove-it` | when it applies | when it applies | required | when it applies |
| `/astack:rearchitect` | when it applies | – | – | when it applies |
| `/astack:redteam` | when it applies | – | – | – |
| `/astack:research-this` | when it applies | when it applies | when it applies | required |
| `/astack:resume` | when it applies | when it applies | – | – |
| `/astack:review` | when it applies | – | when it applies | – |
| `/astack:rtfm` | required | required | required | required |
| `/astack:run-it-back` | required | required | when it applies | required |
| `/astack:safe-iac` | when it applies | when it applies | when it applies | when it applies |
| `/astack:safe-to-deploy` | when it applies | when it applies | when it applies | when it applies |
| `/astack:safe-to-rerun` | when it applies | when it applies | when it applies | – |
| `/astack:setup` | when it applies | – | – | – |
| `/astack:show-the-states` | when it applies | when it applies | when it applies | when it applies |
| `/astack:simplify-me` | when it applies | when it applies | when it applies | – |
| `/astack:slates` | when it applies | when it applies | when it applies | – |
| `/astack:sprint` | when it applies | – | – | – |
| `/astack:squish` | when it applies | – | – | – |
| `/astack:status` | required | – | – | – |
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
| `/astack:wat` | required | when it applies | when it applies | when it applies |
| `/astack:watch-pr` | when it applies | – | – | – |
| `/astack:werkflow` | when it applies | when it applies | – | – |
| `/astack:whatsup` | when it applies | – | – | – |
| `/astack:workflow-this` | when it applies | – | – | – |
| `/astack:worrywart` | when it applies | when it applies | – | – |
| `/astack:yagni` | when it applies | required | when it applies | – |
