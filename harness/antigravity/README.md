# astack

A multi-harness agent toolkit for Claude Code, Codex, Cursor / Cursor CLI, Antigravity (`agy`), Pi, Devin, and other Agent Skills hosts with one entry point (`go`) that routes on demand to 87 hidden skills: DAG and component-tree planning, multi-repo infra/app choreography, automated workflows, ticket-queue watching and autonomous sprint execution, checkpoint/suspend/resume, parallel workers, live infra triage and network tracing, root-cause diagnosis, proactive red-team hardening loops, cross-harness vectored review, σ-grounded benchmarking, graded research, and coding/infra rules.

Only `go` stays in the model catalog, so idle sessions cost one skill's worth of context instead of thousands of tokens. Adapted in part from [pstack](https://github.com/cursor/plugins/tree/main/pstack) and [mattpocock/skills](https://github.com/mattpocock/skills).

## Install

**Claude Code**

```
/plugin marketplace add adalundhe/astack
/plugin install astack@astack
```

Restart or run `/reload-plugins`. Update later with `claude plugin marketplace update astack` and `claude plugin update astack@astack`.

**Cursor:** open **Customize**, choose **From GitHub Repository**, and enter `adalundhe/astack`.

**Codex**

```
codex plugin marketplace add adalundhe/astack
codex plugin add astack@astack
```

Start a new session and run `$astack-go setup` (installs `astack-worker.toml` plus one `astack-reviewer-<slug>.toml` per Codex-routable model in `reviewer_pool` into `~/.codex/agents/`, and enables the timestamp hook).

**Antigravity (`agy`)**

```
agy plugin install https://github.com/adalundhe/astack
# Or from a local clone (or inside agy TUI: /plugin install ~/Projects/astack):
agy plugin install ~/Projects/astack
# Or install the pre-built Antigravity bundle directly:
agy plugin install ./harness/antigravity
```

Ships native `.antigravity-plugin/plugin.json` (and `harness/antigravity/plugin.json`), root `hooks.json` (`PostToolUse` lane-log stamper + `PreInvocation` sticky Go mode), all 88 skills, `bin/astack-*`, and all four native agents (`astack-lead`, `astack-worker`, `astack-reviewer`, `astack-researcher`). Validate anytime with `agy plugin validate . --strict` or `agy plugin validate harness/antigravity --strict`.

**Pi, Devin, Cursor CLI (`agent`), and other Agent Skills hosts**

Use the harness-agnostic bundle at `harness/portable/` (zero Claude-specific syntax) and install native agents and CLI links for every detected harness in one step:

```bash
harness/portable/bin/astack-tools install-agents --harness all
harness/portable/bin/astack-tools link-bin
```

## How it works

Start with `/astack:go` (Cursor / Cursor CLI: `/astack-go`, Codex: `$astack-go`, Antigravity / Pi / Devin: `astack-go` from `harness/portable/skills/astack-go/SKILL.md`). Running `go` puts the main session agent directly into the **Lead** role in **sticky Go mode** for the entire session—backed by per-session lifecycle hooks (`astack-go-hook` / `astack-go-mode`) that re-inject the Lead + Go mode reminder on every follow-up prompt and post-compaction/resume in Claude Code, Codex, and Antigravity, and on `sessionStart` in Cursor (where `beforeSubmitPrompt` only supports `{"continue": true}` and tracks session state)—so finishing a task never drops back to un-orchestrated behavior; say `"exit go mode"` or `"leave astack"` to leave it. Every other skill is hidden from auto-invocation (`disable-model-invocation: true` in Claude Code/Cursor/portable; `agents/openai.yaml` with `allow_implicit_invocation: false` in Codex) and read on demand by path—including when skills reference each other directly.

Optional one-time setup (`/astack:setup`) configures per-role timers (default `60/30/30/5/5` min for worker, reviewer, researcher, wind-down, and check-in), per-role models/effort (`~/.config/astack/settings.json`), and whether to provision an isolated `uv` Python `>=3.11` venv (`astack-tools`) for `taskex`, `orchestral`, and `werkflow` + `werkflow-modules` (declining defaults to pure-agentic workflows).

### Bigger tasks: DAGs, workflows, and parallel workers

```
/astack:go Make the export pipeline 10x faster at p99 on the 10 GB sample with byte-identical output,
measured against the current release on the same machine. Merges go to main after lint and tests.
```

1. **Plan a reviewed DAG (`dagify`):** break the goal into small tasks with acceptance criteria, tests, non-overlapping file paths, and dependency edges, reviewed before coding starts.
2. **Execute it:**
   - **Automated workflow (`workflow-this`):** turn the graph into a resumable script or CI workflow (`taskex`, `orchestral`, `werkflow`, or CI) with explicit task states.
   - **Parallel workers (`lead`):** dispatch ready DAG tasks to time-boxed `worker` subagents in separate git worktrees, check actual branch commits on a schedule, verify merges with `astack-verify-merge` (or gate via `review` and `watch-pr`), and hand unfinished work to fresh successors via `~/.cache/astack/<program>/`.
3. **Catch up without babysitting:** workers settle technical choices on their own and log why (`astack-decisions`). Run `/astack:status` for active timers/commits, or `/astack:whatsup` for a full brief of what landed, what broke, what experiments/research proved, and what needs your call.

## Skills

88 skills total (`go` + 87 hidden). Direct invocation uses `/astack:<name>` in Claude Code, `/<name>` in Cursor, and `$<name>` in Codex; `go`, `lead`, `setup`, `status`, and `review` take an `astack-` prefix in Cursor and Codex.

### Entry point, planning, and catch-up

- `go`: single catalog-visible entry point that places the main session agent in the **Lead** role in sticky Go mode across turns/compaction and routes to every hidden skill and coding rule by path.
- `dagify`: breaks a goal into a reviewed dependency DAG of small, parallelizable tasks.
- `treeify`: decomposes work into a reviewed component tree down to the smallest testable, verifiable, documentable units and builds, vectored-reviews, and merges bottom-up in waves with escalating testing, review rigor, and documentation.
- `cross-repo`: coordinates multi-repo infra, edge, and app programs from one program folder using `astack-release` (`release.json` + rendered `RELEASE.md` Mermaid graph), immutable upstream output handoffs, `astack-watch-pr` PR sync, expand-switch-contract deploy gates, and reverse-order rollback runbooks.
- `workflow-this`: turns a `dagify` graph into a resumable automated workflow with explicit task states.
- `lead`: executes a task DAG with parallel time-boxed workers in isolated [Slates](https://github.com/hyper-light/slates) in-memory VFS volumes (preferred when available) or git worktrees, verified merges, and durable logs.
- `slates`: provisions, mounts, snapshots, clones, merges (`green`/`work`/`submit`), lands (human-gated `grant`), and cleans up RAM-backed copy-on-write VFS agent workspaces with [Slates](https://github.com/hyper-light/slates) (preferred over git worktrees when `slates status` succeeds or Slates MCP is attached).
- `setup`: configures timing, per-role model/provider/effort, the approved `reviewer_pool`, the `autonomy` grant (`supervised` vs `unattended` with explicit `allow`/`deny`), cross-platform `~/.astack` home initialization (Windows/macOS/Linux), CLI `PATH` links, and optional `astack-tools` packages.
- `status`: shows active workers, timers, latest branch commits, open tasks, and waiting questions.
- `whatsup`: catch-up brief and post-break context rebuild (waiting calls, bugs, milestones, experiments, research).
- `track-it`: syncs DAG tasks and progress to GitHub Issues, Jira, Linear, or another tracker.
- `sprint`: watches GitHub Issues, Jira, or Linear using `astack-watch-tickets` for tickets matching natural-language filter conditions (rate-limit-safe, crash-resumable, security-fenced), ingests matched work, drives each ticket end-to-end via `/astack:go` through vectored `review`, `watch-pr`, authorized merge (only when `merge_pr` is permitted or opted in), and closing `lookback`.

### Code review and PRs

- `review`: splits a change into risk-classified vectors, gathers PR/issue/discussion/ADR context first, runs time-boxed blind adversarial reviewers from `reviewer_pool` enforcing coding rules and disciplines, saves standalone failing reproductions, counts only proven blocking bugs with fix-equivalence overlap checks, stops on observable-class saturation or empirically calibrated clean sweeps (`astack-review-ledger`), holds risky non-saturated changes for human sign-off, and relays only proven high-signal issues plainly without leaking internal ledger status.
- `adversarial-review`: single-reviewer playbook—research linked context first, enforce coding rules and disciplines, state contradictions plainly with both sides, reproduce before/after, attack edge cases, and prove every finding.
- `leave-feedback`: drafts, independently audits via a second reviewer agent, and posts clear, concise, actionable human-facing PR comments—verifying surrounding PR/issue/doc context was inspected and blocking cryptic SHAs, awkward/stilted/rambling prose, missing actions, or leaked internal thinking before posting.
- `challenge`: peer-to-peer adversarial interrogation of hypotheses, repeated fixes, diagnoses, designs, or code.
- `worrywart`: pushes back on wrong or unproven review points with concrete evidence.
- `blast-radius`: traces indirect breakage outside a diff and runs code to verify safety.
- `watch-pr`: shepherds reviewed PRs/MRs on GitHub, GitLab, and Bitbucket using the shipped good-citizen watchers (`astack-watch-pr`, `astack-watch-github`, `astack-watch-gitlab`, `astack-watch-bitbucket`), dispatching workers with vectored review and `/leave-feedback` audited replies for comments, rebases, CI failures, and 24h reminders.
- `squish`: lead-only post-workflow consolidation pass—examines commits and generated PRs at the end of a DAG workflow, component tree, red-team loop, or sprint ticket, determines whether they should be rebased, squashed, or combined to avoid fragmented/noisy PRs, and executes the consolidation safely while verifying tree equivalence, `authorship-check`, `astack-check-gates`, and deploy-ordering boundaries.
- `address-feedback`: resolves every review finding or PR thread (fix, answer, or refute), blockers first.
- `leave-it-better`: fixes unrelated broken tests, builds, or CI in a separate PR instead of working around them.

### Benchmarking and experiments

- `benchmarking`: measures user-visible metrics across load/fault spectra with baseline noise and a statistical bar.
- `ab-test`: benchmarks variants in isolated worktrees with alternating rounds, grafting winning ideas before deleting losers.
- `decide-by-data`: settles design or config trade-offs with measurements instead of debate.
- `baseline`: keeps competitor benchmarks and baselines fair (same driver/platform, release tuning, error checks, alternating runs).
- `clamber`: iterative optimization loop—baseline everything, change one thing at a time, commit gains, revert regressions.
- `swarm-hypothesis`: builds competing implementations in parallel Slates VFS volumes (preferred) or worktrees, benchmarks them, grafts best parts, keeps the winner.

### Testing and verification

- `prove-it`: verifies claims on the real build (not proxies) with deterministic reproduction, empirically measured occurrence frequency (logs/traces/telemetry/monitoring/usage analytics), runnable proof, and a trust ladder.
- `test-drive`: builds and maintains a `drive-<app>` skill that exercises real user flows and captures evidence.
- `formal-validate`: sets up and maintains formal verification (TLA+, code verifiers, property checks) for critical invariants.
- `tests-assert-behaviour`: keeps tests checking observable behavior rather than internals, mocks, or wall-clock timing.
- `full-spectrum-testing`: writes acceptance tests across unit/integration/E2E layers including failures, races, fuzzing, and faults.
- `find-it`: replicates bugs from provided or correlated real data (logs, traces, metrics, monitoring, usage analytics) and full failure-environment conditions (OS/arch, memory/CPU/disk, network, correlated services) across the end-to-end path, collects runtime evidence (`<file>_DEBUG_<shorthash>.<type>`, built-in -> astack -> third-party tools), shrinks repros before diagnosing, narrows root causes (bisect, live dumps, profile pairs), and cleans debug artifacts once fixed.
- `fix-it`: applies disciplined, minimal, behavior-proven bug fixes using the desired/expected behavior matrix, strict state/concurrency/scope/system-impact rules, tests hardened against lead review, and before/after proof.
- `bugbash`: lead-only default vectored bug workflow—assembles the bug dossier, scales read-only reviewers by risk (1 reviewer for isolated low-risk bugs; >=2 blind reviewers split across complementary reproduction vectors for risky/ambiguous bugs) using `find-it` (shrinking repros first; never editing code) and peer `challenge`, routes converged fixes to workers (`fix-it`) in isolated workspaces, verifies via post-fix `review` (`prove-it` + PR proof), and closes with `lookback` + `make-it-stick`.
- `redteam`: lead-only proactive adversarial audit-fix-rereview loop for an existing codebase—starts with vectored `review` waves that actively attempt to break, disrupt, and limit-test the live system (local dev builds, approved hosted dev/staging, or live harnesses), returns proven findings, dispatches workers to fix them (via `dagify` or `treeify` when complex), pairs freely with `clamber` when performance is part of the goal, re-reviews via vectored `review`, repeats until user-specified stopping conditions are met or vectored review returns no issues, and closes with `lookback` + `make-it-stick`.
- `triage`: structured live-infrastructure and multi-layer systems debugging across any cloud, edge, cluster, serverless, or host platform—verifies target context, preserves volatile state before restarts, correlates recent changes/audit logs, isolates layers read-only, separates reversible mitigation from root cause, and hands confirmed bugs to `bugbash`.
- `net-trace`: packet-to-cloud/edge network diagnostics across DNS, edge/CDN/WAF, routing, bidirectional firewall/network policies, flow logs, TLS/SSL/mTLS handshakes, sockets/`conntrack`, and secret-safe packet captures.

### Refactoring and cleanup

- `simplify-me`: cuts unnecessary code and complexity without losing correctness, edge cases, or speed.
- `modularize`: splits monoliths via a smallest-behavior proof of concept, `dagify`-batched parallel migration, and `simplify-me`/`yagni` trim—validated with vectored review at each stage.
- `rearchitect`: finds high-churn structural friction, ranks restructurings with diagrams, and plans the top pick via `dagify`.
- `deeper`: tightens a task brief to primary sources, domain tools, and external proof without adding scope.
- `cleanup`: removes temp files, `<file>_DEBUG_<shorthash>.<type>` debug captures/logs, build artifacts, caches, test data, and leftover processes post-review and during/after debugging.

### Coding rules

Indexed in `go` and checked by `review`:

- `data-structures-first`: design data representations, invariants, and access patterns before control flow.
- `no-implicit-states`: use explicit state enums/tagged unions and centralized transitions instead of boolean flags.
- `no-hidden-flow-control`: handle specific errors narrowly or return typed values; no catch-alls or swallowed errors.
- `no-hidden-config`: parse settings in one place, document and test every value, use real feature flags.
- `minimize-state-stores`: keep one source of truth; add caches or copies only when measurements justify them.
- `check-your-boundaries`: parse untrusted input once at the edge into domain types, then trust them inside.
- `no-shared-writes`: give concurrent writers isolated state and merge on read before reaching for locks.
- `safe-to-rerun`: make state-changing operations idempotent and crash-safe (converge from state, atomic write-then-rename).
- `safe-to-deploy`: keep live workloads and rollbacks working across every deploy step (expand -> switch -> contract) and test pre-change non-privileged callers against post-migration state.
- `least-privilege`: scope identities, tokens, roles, RBAC, DB grants, encryption keys, and network rules to exact needed actions/resources/conditions and prove both allow and deny as the real non-privileged identity.
- `safe-iac`: inspect real plans/diffs against live state before applying, protect stateful and routing/DNS resources from surprise destroys, check live drift, pin immutable versions/digests, and bound quotas and spend.
- `fail-safely`: bound timeouts, queues, pools, and retries (backoff + jitter + budget), decouple liveness probes from downstreams, shield origins, and drain gracefully across failure domains.
- `observable-by-default`: make services, scheduled jobs, workers, queues, and infra operable with bounded-cardinality telemetry, trace correlation, symptom/SLO alerts, dead-letter visibility, and code-verified runbooks.
- `no-bolt-ons`: fold new requirements cleanly into the design instead of special-case flags or `_v2` copies.
- `yagni`: migrate callers and delete legacy paths together—no shims, deprecated aliases, or dead flags.
- `comment-cop`: cut narrating comments; keep only API contracts, external constraints, legal headers, and links.
- `delight-users`: audit from the consumer's side for missing states, vague errors, awkward APIs, and bad defaults.
- `no-picked-constants`: derive limits/timeouts from cited specs or adapt them at runtime—never pick magic numbers.
- `event-driven`: wake on completion events instead of `sleep` loops, fixed timers, or polling.
- `never-trade-functionality`: never trade accuracy, freshness, or features for speed; run `research-this` before accepting any limit.
- `no-leaked-secrets`: sweeps code, diffs, configs, logs, errors, telemetry, tests, and debug artifacts for leaked secrets, credentials, unneeded PII, or excessive logging.

### Understanding, specs, docs, and communication

- `how-it-works`: read-only codebase walkthrough with `file:line` citations, marking claims as run vs. read.
- `show-the-states`: diagrams states, triggers, failure paths, and observed probabilities in Mermaid (backed by `astack-statechart` for TLC models and DOT graphs).
- `run-it-back`: restates goal, scope, exclusions, and assumptions in short checkable lines before coding.
- `play-with-me`: builds a quick throwaway mockup, script, or demo proactively so you can try an idea first.
- `talk-to-me`: explains unfamiliar concepts with domain terms, a diagram, a worked example, and an analogy.
- `technical-writing`: analyzes documentation impact on every change (updating or removing stale repo docs in the same change) and sets the standard for concise, concrete, code-verified technical docs.
- `wat`: rewrites the last message to lead with the bottom line and cut jargon and meta-commentary.
- `bap`: immediate mid-session course correction when the person has to repeat a reminder or correction—drops apologies, audits why it slipped, repairs live state/workers, and locks in a structural guard (`make-it-stick`).
- `rtfm`: checks your prompt, saved memories (`lookup`), repo docs/code/history, local environment, and official docs before asking questions (escalating to `lookback` when deep history isn't captured yet).
- `lookup`: consults structured `~/.astack/<project_name>/lessons/<lesson_name>/LESSON.md` memories, past decisions, and environment catalogs—verifying them against current code/state—to determine the best path, avoid dead ends, discover relevant repos on cross-repo work, or familiarize an agent with a project/environment.
- `lookback`: deeply inspects past chats, actions, tool calls, results, tickets, bugs, failures, and deployments (and closes finished DAG workflows, component trees, and review sessions) to distill structured `~/.astack/<project_name>/lessons/<lesson_name>/LESSON.md` documents with YAML frontmatter and consistent sections (multiple focused lessons per project).
- `analyze-environment`: discovers local/external CLIs, APIs, MCP servers, services, and env-var names, runs safe read-only/dry-run and auth-status probes, installs missing user-space tooling under `unattended`, publishes a shared `TOOLS.md` catalog for all agents, and isolates only human-only auth steps.
- `research-this`: investigates internal + external sources, checks quotes in place, and grades findings A–F (`kiln`-compatible).
- `decisions-in-plain-words`: resolves what it can, logs why, and escalates only real human calls with a recommendation.
- `create-adc`: works through an architecture decision one evidenced exchange at a time and publishes `AD_<N>.md`.

### Automation and session notes

- `automate-this`: replaces repeated commands, polling, and noisy output with scripts, watchers, or subagents.
- `taskex`: async/sync Python and shell tasks, watchers, recurring jobs, durable SQLite checkpointing, and live/restart pause-resume ([taskex](https://github.com/adalundhe/taskex)).
- `orchestral`: dependency-graph (DAG) wave and staged concurrent Python/shell pipelines with cycle checks, branch-aware skipping, wave streaming, live workflow/step pause-resume, and SQLite crash recovery ([orchestral](https://github.com/adalundhe/orchestral)).
- `werkflow`: modular DAG workflows with [werkflow](https://github.com/adalundhe/werkflow) and all 15 [werkflow-modules](https://github.com/adalundhe/werkflow-modules) packages.
- `checkpoint`: instruments, saves, inspects, and verifies durable SQLite/store checkpoints for `taskex` and `orchestral` runs.
- `suspend`: cleanly pauses running `taskex` callables/subprocesses/schedules or `orchestral` workflows/steps without losing progress.
- `resume`: unpauses suspended runs/workflows/steps in place or recovers failed/crashed `taskex` and `orchestral` runs from checkpoints.
- `make-it-stick`: captures scoped lessons in `~/.astack/<project>/lessons/<lesson>/LESSON.md` via `lookback` and prevents repeats via architecture -> types -> lint -> test -> docs last.

## Under the hood

- **Agents:** `lead` (program coordinator & merge/review gatekeeper), `worker` (builds one task within its time limit, reports losses first), `reviewer` (read-only adversarial vectored review), and `researcher` (read-only codebase walks & A–F primary-source research)—shipped as full native agents across Claude Code (`.md`), Codex (`.toml`), Antigravity (`.md` with `subagent`/`mainAgent`), Cursor (`.md` with `is_background`), Devin (`.md`), and Pi (`.md` with `tools`/`readOnly`), and installable via `astack-tools install-agents`.
- **CLI scripts (`bin/`):**
  - `astack-status`: active workers, reviewers, and researchers, their timers/wind-down clocks, latest branch commits, and open questions (`--line` for status bars).
  - `astack-decisions`: query `decided:` entries and verbatim `person:` directives (`--query`, `--settled-by`, `--since`, `--json`).
  - `astack-verify-merge`: verifies a claimed commit is on the target branch, audits strictly `--base <last-verified-target>..<sha>` (or every parent side of a merge commit when `--base` is omitted, never trusting commit messages; fails closed on checker errors; `--strict-gates` blocks without countersign), and can run checks in a clean worktree.
  - `astack-check-gates`: structural tripwire auditing a git range (`<base>..<head>`) or commit for deleted/renamed tests, skips, lint/typecheck suppressions, assertion downgrades, cross-diff test swaps, tautologies, loosened numeric tolerances, and CI/lint/gate config edits.
  - `astack-review-ledger`: evaluates vectored review saturation over proven blocking bugs with fix-equivalence overlap verification, 2-reviewer Chapman + exact hypergeometric lower/upper bounds, 3+-reviewer Burnham–Overton $M_h$ jackknife + Beta-Binomial $M_h$ profile-likelihood bounds (observable-class saturation: "these models stopped finding new bugs", never falsely claiming 95% proof that hard bugs are absent), empirical catch-rate calibration from `scripts/eval.py --calibrate` (no picked 0.5 constant), landing-block gating on non-saturated risky vectors, internal Markdown coverage maps, and `LANES.md` review-count lines.
  - `astack-dispatch`: cross-harness "agents as tools" dispatcher, supervised run registry, wave barrier, and `reviewer_pool` reachability checker (`harnesses`, `check-pool`, `run`, `spawn`, `batch`, `status`, `wait`, `kill`) supporting Claude (`claude`), Codex (`codex`), Antigravity (`agy`), Cursor CLI (`cursor-agent`/`agent`), Devin (`devin`), Pi (`pi`), Gemini (`gemini`), and custom CLI templates, enforcing pool approval, tracking live cross-harness PIDs/timeouts (surfaced by `astack-status` and guarded by the `Stop` hook so hosts never halt prematurely while external agents are live), and writing auditable JSON receipts.
  - `astack-watch-pr`, `astack-watch-github`, `astack-watch-gitlab`, `astack-watch-bitbucket`: stdlib-only PR/MR watchers for GitHub (`github.com` + GHES), GitLab (`gitlab.com` + self-hosted with nested subgroups), and Bitbucket (Cloud REST 2.0 + Server/Data Center REST 1.0) with good-citizen rate-limit pacing (`ETag`/`304`, consolidated GraphQL with automatic REST fallback, `Retry-After`/`X-RateLimit-*`/`RateLimit-*`/`X-RateLimit-NearLimit` adaptation, idle backoff, per-PR locks), fork-isolated stacked PR/MR ordering, **hold & external-guard gating** (`PRState.HELD` / exit `6` via forge `do-not-merge`/`hold` labels, `--hold`, `--gate-cmd`, and `--release-file`/`--release-step` DAG gates with forge auto-merge warnings), crash-safe `watch/<PR>.md` handoff markers, `patch-id-check` (`git patch-id` + `git range-diff` rebase verification), `diff-guard` (review-round diff-growth guard), `authorship-check` (takeover credit & `Co-authored-by` preservation), `autonomy`-enforced & `/leave-feedback`-audited `reply` subcommands, and idempotent lead remediation dispatch (`--role lead`, delegating edits to workers while running lead-owned vectored review and reply audits).
  - `astack-watch-tickets` (backed by the modular stdlib package `lib/astack_tickets/`): good-citizen ticket watcher and ingester for GitHub Issues (GraphQL API by default for its generous 5,000 pts/hr quota with automatic REST `ETag`/`304` fallback + `@me` resolution), Jira (Cloud v3 `/search/jql` + Server/DC v2 fallback + ADF text extraction), and Linear (GraphQL `IssueFilter` JSON or shorthand with both request and complexity rate-limit tracking), featuring exclusive watch locks, durable atomic `state.json` deduplication, security-fenced untrusted ticket briefs, `merge_pr` autonomy gating, and optional headless lead dispatch (`auth-check`, `query`, `watch`, `ingest`, `status`, `mark`).
  - `astack-release`: stdlib-only multi-repo and multi-step PR merge & deploy train manager (`init`, `load`, `add-step`, `set-pr`, `status`, `ready`, `sync`, `start`, `verify`, `complete`, `fail`, `rollback-plan`, `mark-rolled-back`, `render`) with DAG cycle/ancestor-output validation, atomic persistence, `astack-watch-pr` live PR syncing, `{{step.key}}` cross-repo output interpolation, secret-leak refusal, `settings.json` `autonomy` human gates, reverse-topological rollback planning, and rendered Mermaid `flowchart LR` release runbooks.
  - `astack-statechart`: runs TLC in `-tool` mode with `-dump dot,actionlabels`, single-worker minimum-depth BFS default (`--workers 1`), `--timeout`, and `--no-deadlock` (or parses DOT/trace output offline, rejecting malformed input), follows TLC exit status strictly, preserves multiple broken invariants per state, finds shortest paths via full untruncated state matching, and renders collision-safe Mermaid `stateDiagram-v2` (tested against 40 real `.tla`/`.cfg` specs recorded with TLC 2.19 and re-checked live in CI, plus a 10-spec live BFS differential fuzzer).
  - `astack-stamp` (+ post-edit hook): timestamps new lines appended to `LANES.md`.
  - `astack-go-mode` (+ `astack-go-hook` lifecycle hooks): keeps Go mode (in the Lead role) sticky per session (`status`, `on`, `off`, `lessons`, `--hook`) without leaking into unrelated sessions or spawned subagents, AND automatically recalls matching active `~/.astack/<project>/lessons/*/LESSON.md` entries (including `related_projects` matches) on `SessionStart` / `PreInvocation` / compaction with zero extra tool calls across Claude Code, Codex, Antigravity, and Cursor.
  - `astack-tools`: initializes `~/.astack` with cross-platform permissions (`init-home`), resolves/lists per-project lessons (`lessons path|list`), puts launchers for the `astack-*` CLI scripts onto `PATH` (`link-bin`; each runs the newest installed astack), provisions Python `>=3.11` via `uv` across macOS/Linux/Windows (arm64 & amd64), and manages an isolated venv for `taskex`, `orchestral`, and `werkflow` (`doctor`, `init-home`, `lessons`, `install`, `link-bin`, `python`, `werkflow`, `env`, `path`).
- **Evals & CI:** 25 multi-harness, zero-hint outcome evals under `evals/` (cold-start skill discovery without `/astack:go`, worker wind-down/reports, Go-mode routing & dedicated agent spawning, multi-file planted-bug & decoy review, cross-harness review, context/contradiction/coding-rule review, pre-post PR comment auditing via `leave-feedback`, multi-file gamed-gate rejection, `find-it`/`fix-it` repro-shrinking and explicit-state bug fixing, lead `bugbash` reviewer-swarm convergence + `prove-it` PR evidence, `redteam` break-and-harden loop, `squish` branch consolidation + authorship credit, `lookback`/`lookup` lesson persistence + stale audit, `sprint` security-fenced ticket ingestion + `merge_pr` stop gate, and 6 coding rules) with behavioral reproduction verifiers (`verify.py` + `evals/_repro_verify.py`), `--calibrate` empirical per-model catch-rate measurement, `--ablation with-without`, runnable on Claude Code, Codex, Antigravity (`agy`), Cursor CLI, Devin, or Pi via `python3 scripts/eval.py --harness <name>`, plus GitHub Actions unit CI ([.github/workflows/ci.yml](./.github/workflows/ci.yml)) and diff-selected live ablation eval CI ([.github/workflows/evals.yml](./.github/workflows/evals.yml)).

## Working on astack

Edit source at the root (`skills/`, `agents/`, `bin/`, `lib/`, `evals/`, `packaging/`), rebuild `harness/`, run tests, and commit both:

```bash
python3 scripts/build.py
python3 -m unittest discover -s tests
```

Run evals on any installed harness (`claude`, `codex`, `agy`, `cursor`, `devin`, `pi`):

```bash
python3 scripts/eval.py --harness codex --case "vectored-review-*"
python3 scripts/eval.py --harness agy --case "vectored-review-*"
python3 scripts/eval.py --harness claude --case "vectored-review-*"
# Or directly with Claude Code's built-in plugin evaluator:
claude plugin eval harness/claude-code --trust-plugin --scaffold --ablation none
```

## License

MIT ([LICENSE](./LICENSE)). File-by-file attributions for [pstack](https://github.com/cursor/plugins/tree/main/pstack) and [mattpocock/skills](https://github.com/mattpocock/skills) are in [NOTICE.md](./NOTICE.md).
