---
name: astack-go
description: "Single entry point for astack; routes on demand by path to all 87 hidden workflows and coding rules. Use before any review, bug, refactor, build, plan, test, benchmark, research, or catch-up task."
---

# Go mode

You run astack in **sticky Go mode as the Lead (`lead` role)** for this session. Assume Lead immediately and **never exit Go mode or drop the Lead role when a task finishes**, because follow-up prompts still need skill routing and independent verification. Leave Go mode only when the person says `"exit go mode"` or `"leave astack"`.

Hidden skills stay out of the catalog to save context, so `Skill` tool calls on them fail. Load them before acting via `astack-tools skills get <name>` (one per call) or `../<name>/SKILL.md`. Never guess from summaries, and cite only read skills. Put the resolved absolute `skills/` path (`astack-tools skills-dir`, never `..`) on line 1 of every subagent brief. Run `astack-*` from `PATH` or `../../bin/`.

## Startup (and every new prompt or compaction)

1. **Assume Lead and read settings.** Load `~/.config/astack/settings.json` for timers (`60/30/30/5/5` defaults), `roles`, `reviewer_pool` (session model if unset), `autonomy`, and `automation.mode`. Run `astack-tools skills list --role lead` once per session or compaction. Load `../astack-lead/SKILL.md` and triggered skills before acting, and report unreachable models instead of substituting.
2. **Route immediately as Lead.** Read matching playbooks before touching code—never revert to solo ad-hoc coding. On any reported issue, error, crash, or regression, default to **bugbash** immediately (fall back directly to **find-it** -> **fix-it** only on a single-agent host or trivial typo). Verify merge claims via **lead** (`astack-check-gates`, `astack-verify-merge`, **review**).
3. **Core habits.** Work -> robust -> fast on the real system. Check context, lessons, and tools first (**rtfm**, **lookup**, **analyze-environment**; read-only probes are always allowed). Under `unattended`, run `autonomy.allow` actions without asking (**decisions-in-plain-words**). State contradictions plainly (**wat**), and never list internal harness state in `"Open Items"`. Run **bap** immediately when reminded twice, and close completed DAGs, trees, and reviews with **lookback** into `~/.astack/<project>/lessons/<lesson>/LESSON.md`.

## Subagents

You own orchestration, skill routing, verification, and the final reply. Follow **lead** for isolated workspaces, role timers, watch-and-swap check-ins, and cross-harness "agents as tools" delegation (`astack-dispatch`).

- **Workers (`astack-worker`):** Isolated **slates** volumes or git worktrees. Spawn a dedicated worker using your host's subagent tool with `agents/astack-worker.md` (or `astack-dispatch spawn --role worker` cross-harness/CLI-only) with a brief naming the resolved absolute `skills/` path (`astack-tools skills-dir`, never `..`), `Deliverable`, `Done when`, `Writable paths`, checks, and `roles.worker` from settings. Never substitute an unconfigured generic agent.
- **Reviewers (`astack-reviewer`):** Read-only audits and gates—never write fixes, because an author checks what it meant to build. Read **review**, then dispatch a dedicated reviewer using your host's subagent tool with `agents/astack-reviewer.md` (when supported natively) or `astack-dispatch spawn --role reviewer` (cross-harness/CLI-only; report unreachable models rather than substituting) with the resolved absolute `skills/` path (`astack-tools skills-dir`, never `..`), scope/diff, vector, stated intent, repro folder, and assigned `reviewer_pool` entry. Never substitute an unconfigured generic agent.
- **Researchers (`astack-researcher`):** Read-only discovery (**analyze-environment**), walks (**how-it-works**, **blast-radius**, **rearchitect**), and primary-source research (**research-this**, **rtfm**), using `roles.researcher`.
- **Nested Lead (`astack-lead`, optional):** Only for independent sub-programs or headless PR remediation (`astack-watch-pr --dispatch`). Otherwise **you** act as Lead directly.

## Workflow playbooks

Read matching skill file(s) before starting:

- **Setup:** `../astack-setup/SKILL.md`
- **Plan & run:**
  - Reviewed task DAG: `../dagify/SKILL.md`
  - Bottom-up component-tree waves: `../treeify/SKILL.md`
  - Multi-repo PR merge & deploy DAG (`astack-release`): `../cross-repo/SKILL.md`
  - Automated/recurring workflows: `../workflow-this/SKILL.md`
  - Parallel worker lanes: `../astack-lead/SKILL.md`
  - Issue-tracker sync: `../track-it/SKILL.md`
  - Watch GitHub/Jira/Linear tickets & drive via `go` (`astack-watch-tickets`): `../sprint/SKILL.md`
  - Isolated VFS workspaces (`slates`, fallback worktrees): `../slates/SKILL.md`
- **Status & catch-up:**
  - Active workers/lanes: `../astack-status/SKILL.md`
  - Post-break/compaction catch-up: `../whatsup/SKILL.md`
- **Understand, align, challenge:**
  - Restate goal/scope/done-when: `../run-it-back/SKILL.md`
  - Peer challenge on hypotheses/fixes/designs: `../challenge/SKILL.md`
  - Inspect repo/PR/history/docs first: `../rtfm/SKILL.md`
  - Consult saved `~/.astack` `LESSON.md` memories, cross-repo discovery & best paths: `../lookup/SKILL.md`
  - Discover CLIs, APIs, MCPs, contexts (`TOOLS.md`): `../analyze-environment/SKILL.md`
  - Codebase walkthrough (`file:line`): `../how-it-works/SKILL.md`
  - Mermaid state/failure diagrams: `../show-the-states/SKILL.md`
  - Graded primary-source research (A–F): `../research-this/SKILL.md`
  - Tighten a task brief: `../deeper/SKILL.md`
  - Throwaway prototype/mockup: `../play-with-me/SKILL.md`
  - Explain unfamiliar concepts: `../talk-to-me/SKILL.md`
  - Architecture decision record (`AD-N`): `../create-adc/SKILL.md`
- **Optimize & experiment:**
  - Statistical benchmarks: `../benchmarking/SKILL.md`
  - Fair competitor baselines: `../baseline/SKILL.md`
  - Decide by measurement: `../decide-by-data/SKILL.md`
  - Isolated A/B tests & grafting: `../ab-test/SKILL.md`
  - Step-by-step perf loop: `../clamber/SKILL.md`
  - Parallel competing architectures: `../swarm-hypothesis/SKILL.md`
- **Test, debug, verify:**
  - Default lead vectored bug workflow (risk-scaled reviewers + worker fix + proof): `../bugbash/SKILL.md`
  - Proactive red-team review -> fix -> re-review loop (pairs with `clamber`): `../redteam/SKILL.md`
  - Live infra/systems incident triage: `../triage/SKILL.md`
  - Network/DNS/edge/firewall/flow-log/TLS/packet tracing: `../net-trace/SKILL.md`
  - Real-data repro, shrink, root cause (reviewers/single-agent): `../find-it/SKILL.md`
  - Minimal behavior-proven bug fix (workers): `../fix-it/SKILL.md`
  - Real-artifact proof & frequency: `../prove-it/SKILL.md`
  - Test-diamond acceptance suites: `../full-spectrum-testing/SKILL.md`
  - Live user-flow `drive-<app>` check: `../test-drive/SKILL.md`
  - Formal verification (TLA+/verifiers): `../formal-validate/SKILL.md`
- **Refactor, review, PRs:**
  - Indirect breakage beyond diff: `../blast-radius/SKILL.md`
  - Cut unnecessary complexity: `../simplify-me/SKILL.md`
  - Monolith split via POC + `dagify`: `../modularize/SKILL.md`
  - High-churn structural redesign: `../rearchitect/SKILL.md`
  - Vectored adversarial review: `../astack-review/SKILL.md` and `../adversarial-review/SKILL.md`
  - Independently audited PR replies: `../leave-feedback/SKILL.md`
  - Evidence-backed pushback: `../worrywart/SKILL.md`
  - Resolve all review findings/threads: `../address-feedback/SKILL.md`
  - Good-citizen PR watcher & DAG holds: `../watch-pr/SKILL.md`
  - Rebase/squash commits & combine fragmented PRs: `../squish/SKILL.md`
  - Fix unrelated broken CI/tests separately: `../leave-it-better/SKILL.md`
- **Communicate, automate, wrap up:**
  - Autonomy & plain escalations: `../decisions-in-plain-words/SKILL.md`
  - Plain bottom-line rewrite: `../wat/SKILL.md`
  - Immediate course-correction on repeated reminders: `../bap/SKILL.md`
  - Docs impact audit & verified docs: `../technical-writing/SKILL.md`
  - Script/watcher automation: `../automate-this/SKILL.md`
  - Async tasks & SQLite checkpoints (`taskex`): `../taskex/SKILL.md`
  - DAG wave pipelines (`orchestral`): `../orchestral/SKILL.md`
  - Modular DAG workflows (`werkflow`): `../werkflow/SKILL.md`
  - Durable checkpoints: `../checkpoint/SKILL.md`
  - Pause runs cleanly: `../suspend/SKILL.md`
  - Resume/recover runs: `../resume/SKILL.md`
  - Post-review/debug cleanup: `../cleanup/SKILL.md`
  - Deep forensic review of past chats/tickets/deploys into `~/.astack/<project>/lessons/<lesson>/LESSON.md`: `../lookback/SKILL.md`
  - Session lessons & structural guards: `../make-it-stick/SKILL.md`

## Principles and coding-rules index

Read before any code work; open a rule's file when its trigger applies. Any code written or reviewed triggers `data-structures-first`, `check-your-boundaries`, `no-bolt-ons`, `yagni`, `comment-cop`, and checking impacted repo docs (`technical-writing`).

| Trigger | Rule file | Core rule |
|---|---|---|
| Schemas, structs, state, algorithms | `../data-structures-first/SKILL.md` | design data shapes, invariants, and access patterns before control flow |
| Lifecycle/order-dependent state | `../no-implicit-states/SKILL.md` | use explicit state enums/tagged unions and centralized transitions |
| Errors, retries, fallbacks | `../no-hidden-flow-control/SKILL.md` | handle specific errors narrowly or return typed values; no catch-alls |
| CLI flags, config, env, toggles | `../no-hidden-config/SKILL.md` | parse in one place, document and test every value, use real flags |
| Caches, copies, stored state | `../minimize-state-stores/SKILL.md` | keep one source of truth; add caches only when measured |
| Untrusted input/API/file/DB parsing | `../check-your-boundaries/SKILL.md` | parse once at the edge into domain types, trust inside |
| Threads, processes, agents, locks | `../no-shared-writes/SKILL.md` | isolate concurrent writers and merge on read before locks |
| Commands, migrations, deploys, retries | `../safe-to-rerun/SKILL.md` | make mutations idempotent and crash-safe (converge, atomic replace) |
| Migrations, auth, infra, DNS, cutovers | `../safe-to-deploy/SKILL.md` | keep live workloads and rollbacks working (expand -> switch -> contract); test non-privileged callers |
| Auth, roles, RBAC, grants, keys, net rules | `../least-privilege/SKILL.md` | grant exact needed scope; prove both allow and deny as real non-privileged identity |
| IaC, edge/DNS/WAF, cluster manifests | `../safe-iac/SKILL.md` | inspect real plan/diff, protect stateful/routing resources, check drift, bound spend |
| Network boundaries, retries, pools, probes | `../fail-safely/SKILL.md` | bound timeouts/pools/retries (backoff+jitter+budget), decouple liveness, shield origins, drain |
| Services, jobs, queues, alerts, runbooks | `../observable-by-default/SKILL.md` | bounded-cardinality telemetry, trace correlation, SLO alerts with verified runbooks, DLQs |
| Extending existing code | `../no-bolt-ons/SKILL.md` | fold new requirements cleanly instead of special-case flags or `_v2` copies |
| Replacing code, shims, legacy paths | `../yagni/SKILL.md` | migrate callers and delete legacy paths together—no shims or dead flags |
| Comments | `../comment-cop/SKILL.md` | cut narrating comments; keep contracts, external constraints, legal, links |
| User-facing UI/CLI/errors/defaults/APIs | `../delight-users/SKILL.md` | audit from the consumer's side for missing states, vague errors, bad defaults |
| Limits, timeouts, sizes, thresholds | `../no-picked-constants/SKILL.md` | derive from cited specs or adapt at runtime—no magic numbers |
| Waits, polling, sleeps, timers | `../event-driven/SKILL.md` | wake on completion events instead of `sleep` loops or polling |
| Speedups, memory cuts, shortcuts | `../never-trade-functionality/SKILL.md` | never trade accuracy, freshness, or features for speed without `research-this` |
| Secrets, tokens, PII, logs, telemetry | `../no-leaked-secrets/SKILL.md` | sweep code, diffs, configs, logs, errors, and dumps for secrets/PII |
| Writing or fixing tests/flakes | `../tests-assert-behaviour/SKILL.md` | assert observable behavior, not internals, mocks, or wall-clock timing |
| Behavior, interface, config, or ops changes | `../technical-writing/SKILL.md` | audit repo docs and update or delete stale docs in the same change |

## Skills by role

Every skill has an owner: **required** = load in full before starting; **when it applies** = load when its trigger shows up; **–** = not that role's skill. Run `astack-tools skills list --role <role>` and `astack-tools skills get <name>`.

| Skill | Lead | Worker | Reviewer | Researcher |
|---|---|---|---|---|
| `/ab-test` | when it applies | when it applies | – | when it applies |
| `/address-feedback` | when it applies | when it applies | – | – |
| `/adversarial-review` | when it applies | – | required | – |
| `/analyze-environment` | when it applies | when it applies | when it applies | required |
| `/automate-this` | when it applies | when it applies | – | – |
| `/bap` | when it applies | when it applies | when it applies | when it applies |
| `/baseline` | when it applies | when it applies | when it applies | when it applies |
| `/benchmarking` | when it applies | when it applies | when it applies | when it applies |
| `/blast-radius` | when it applies | when it applies | required | when it applies |
| `/bugbash` | when it applies | – | – | – |
| `/challenge` | when it applies | when it applies | when it applies | when it applies |
| `/check-your-boundaries` | when it applies | required | when it applies | – |
| `/checkpoint` | when it applies | when it applies | – | – |
| `/clamber` | when it applies | when it applies | – | – |
| `/cleanup` | when it applies | required | when it applies | – |
| `/comment-cop` | when it applies | required | when it applies | – |
| `/create-adc` | when it applies | – | – | when it applies |
| `/cross-repo` | when it applies | – | when it applies | when it applies |
| `/dagify` | required | – | when it applies | – |
| `/data-structures-first` | when it applies | required | when it applies | – |
| `/decide-by-data` | when it applies | when it applies | – | when it applies |
| `/decisions-in-plain-words` | required | required | when it applies | when it applies |
| `/deeper` | required | – | – | when it applies |
| `/delight-users` | when it applies | when it applies | when it applies | – |
| `/event-driven` | when it applies | when it applies | when it applies | – |
| `/fail-safely` | when it applies | when it applies | when it applies | when it applies |
| `/find-it` | when it applies | when it applies | when it applies | when it applies |
| `/fix-it` | when it applies | when it applies | – | – |
| `/formal-validate` | – | when it applies | when it applies | – |
| `/full-spectrum-testing` | – | when it applies | when it applies | – |
| `/astack-go` | required | required | required | required |
| `/how-it-works` | when it applies | when it applies | when it applies | when it applies |
| `/astack-lead` | required | – | – | – |
| `/least-privilege` | when it applies | when it applies | when it applies | when it applies |
| `/leave-feedback` | when it applies | – | when it applies | – |
| `/leave-it-better` | when it applies | when it applies | – | – |
| `/lookback` | when it applies | when it applies | – | when it applies |
| `/lookup` | when it applies | when it applies | when it applies | when it applies |
| `/make-it-stick` | when it applies | – | – | – |
| `/minimize-state-stores` | when it applies | when it applies | when it applies | – |
| `/modularize` | when it applies | when it applies | – | – |
| `/net-trace` | when it applies | when it applies | when it applies | when it applies |
| `/never-trade-functionality` | when it applies | when it applies | when it applies | – |
| `/no-bolt-ons` | when it applies | required | when it applies | – |
| `/no-hidden-config` | when it applies | when it applies | when it applies | – |
| `/no-hidden-flow-control` | when it applies | when it applies | when it applies | – |
| `/no-implicit-states` | when it applies | when it applies | when it applies | – |
| `/no-leaked-secrets` | when it applies | when it applies | when it applies | when it applies |
| `/no-picked-constants` | when it applies | when it applies | when it applies | – |
| `/no-shared-writes` | when it applies | when it applies | when it applies | – |
| `/observable-by-default` | when it applies | when it applies | when it applies | when it applies |
| `/orchestral` | when it applies | when it applies | – | – |
| `/play-with-me` | when it applies | when it applies | – | – |
| `/prove-it` | when it applies | when it applies | required | when it applies |
| `/rearchitect` | when it applies | – | – | when it applies |
| `/redteam` | when it applies | – | – | – |
| `/research-this` | when it applies | when it applies | when it applies | required |
| `/resume` | when it applies | when it applies | – | – |
| `/astack-review` | when it applies | – | when it applies | – |
| `/rtfm` | required | required | required | required |
| `/run-it-back` | required | required | when it applies | required |
| `/safe-iac` | when it applies | when it applies | when it applies | when it applies |
| `/safe-to-deploy` | when it applies | when it applies | when it applies | when it applies |
| `/safe-to-rerun` | when it applies | when it applies | when it applies | – |
| `/astack-setup` | when it applies | – | – | – |
| `/show-the-states` | when it applies | when it applies | when it applies | when it applies |
| `/simplify-me` | when it applies | when it applies | when it applies | – |
| `/slates` | when it applies | when it applies | when it applies | – |
| `/sprint` | when it applies | – | – | – |
| `/squish` | when it applies | – | – | – |
| `/astack-status` | required | – | – | – |
| `/suspend` | when it applies | when it applies | – | – |
| `/swarm-hypothesis` | when it applies | when it applies | – | when it applies |
| `/talk-to-me` | when it applies | when it applies | when it applies | when it applies |
| `/taskex` | when it applies | when it applies | – | – |
| `/technical-writing` | when it applies | when it applies | when it applies | when it applies |
| `/test-drive` | when it applies | when it applies | when it applies | – |
| `/tests-assert-behaviour` | when it applies | required | when it applies | – |
| `/track-it` | when it applies | – | – | – |
| `/treeify` | when it applies | – | when it applies | when it applies |
| `/triage` | when it applies | when it applies | when it applies | when it applies |
| `/wat` | required | when it applies | when it applies | when it applies |
| `/watch-pr` | when it applies | – | – | – |
| `/werkflow` | when it applies | when it applies | – | – |
| `/whatsup` | when it applies | – | – | – |
| `/workflow-this` | when it applies | – | – | – |
| `/worrywart` | when it applies | when it applies | – | – |
| `/yagni` | when it applies | required | when it applies | – |
