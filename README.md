# astack

A multi-harness agent toolkit for Claude Code, Codex, Cursor / Cursor CLI, Antigravity (`agy`), Pi, Devin, and other Agent Skills hosts with one entry point (`go`) that routes on demand to 71 hidden skills: DAG task planning, automated workflows, checkpoint/suspend/resume, parallel workers, root-cause diagnosis, cross-harness vectored review, σ-grounded benchmarking, graded research, and coding rules.

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
agy plugin install ./harness/antigravity
```

Ships native `plugin.json`, root `hooks.json` (`PostToolUse` lane-log stamper), all 72 skills, `bin/astack-*`, and all four native agents (`astack-lead`, `astack-worker`, `astack-reviewer`, `astack-researcher`). Validate anytime with `agy plugin validate harness/antigravity --strict`.

**Pi, Devin, Cursor CLI (`agent`), and other Agent Skills hosts**

Use the harness-agnostic bundle at `harness/portable/` (zero Claude-specific syntax) and install native agents and CLI links for every detected harness in one step:

```bash
harness/portable/bin/astack-tools install-agents --harness all
harness/portable/bin/astack-tools link-bin
```

## How it works

Start with `/astack:go` (Cursor / Cursor CLI: `/astack-go`, Codex: `$astack-go`, Antigravity / Pi / Devin: `astack-go` from `harness/portable/skills/astack-go/SKILL.md`). Every other skill is hidden from auto-invocation (`disable-model-invocation: true` in Claude Code/Cursor/portable; `agents/openai.yaml` with `allow_implicit_invocation: false` in Codex) and read on demand by path—including when skills reference each other directly.

Optional one-time setup (`/astack:setup`) configures worker timing (default 60/5/5 min), per-role models/effort (`~/.config/astack/settings.json`), and whether to provision an isolated `uv` Python `>=3.11` venv (`astack-tools`) for `taskex`, `orchestral`, and `werkflow` + `werkflow-modules` (declining defaults to pure-agentic workflows).

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

72 skills total (`go` + 71 hidden). Direct invocation uses `/astack:<name>` in Claude Code, `/<name>` in Cursor, and `$<name>` in Codex; `go`, `lead`, `setup`, `status`, and `review` take an `astack-` prefix in Cursor and Codex.

### Entry point, planning, and catch-up

- `go`: single catalog-visible entry point routing to every skill and coding rule by path.
- `dagify`: breaks a goal into a reviewed dependency DAG of small, parallelizable tasks.
- `workflow-this`: turns a `dagify` graph into a resumable automated workflow with explicit task states.
- `lead`: executes a task DAG with parallel time-boxed workers in isolated [Slates](https://github.com/hyper-light/slates) in-memory VFS volumes (preferred when available) or git worktrees, verified merges, and durable logs.
- `slates`: provisions, mounts, snapshots, clones, merges (`green`/`work`/`submit`), lands (human-gated `grant`), and cleans up RAM-backed copy-on-write VFS agent workspaces with [Slates](https://github.com/hyper-light/slates) (preferred over git worktrees when `slates status` succeeds or Slates MCP is attached).
- `setup`: configures timing, per-role model/provider/effort, the approved `reviewer_pool`, the `autonomy` grant (`supervised` vs `unattended` with explicit `allow`/`deny`), CLI `PATH` links, and optional `astack-tools` packages.
- `status`: shows active workers, timers, latest branch commits, open tasks, and waiting questions.
- `whatsup`: catch-up brief and post-break context rebuild (waiting calls, bugs, milestones, experiments, research).
- `track-it`: syncs DAG tasks and progress to GitHub Issues, Jira, Linear, or another tracker.

### Code review and PRs

- `review`: splits a change into risk-classified vectors, gathers PR/issue/discussion/ADR context first, runs time-boxed blind adversarial reviewers from `reviewer_pool` enforcing coding rules and disciplines, saves standalone failing reproductions, counts only proven blocking bugs with fix-equivalence overlap checks, stops on observable-class saturation or empirically calibrated clean sweeps (`astack-review-ledger`), holds risky non-saturated changes for human sign-off, and relays only proven high-signal issues plainly without leaking internal ledger status.
- `adversarial-review`: single-reviewer playbook—research linked context first, enforce coding rules and disciplines, state contradictions plainly with both sides, reproduce before/after, attack edge cases, and prove every finding.
- `leave-feedback`: drafts, independently audits via a second reviewer agent, and posts clear, concise, actionable human-facing PR comments—verifying surrounding PR/issue/doc context was inspected and blocking cryptic SHAs, awkward/stilted/rambling prose, missing actions, or leaked internal thinking before posting.
- `challenge`: peer-to-peer adversarial interrogation of hypotheses, repeated fixes, diagnoses, designs, or code.
- `worrywart`: pushes back on wrong or unproven review points with concrete evidence.
- `blast-radius`: traces indirect breakage outside a diff and runs code to verify safety.
- `watch-pr`: shepherds reviewed PRs/MRs on GitHub, GitLab, and Bitbucket using the shipped good-citizen watchers (`astack-watch-pr`, `astack-watch-github`, `astack-watch-gitlab`, `astack-watch-bitbucket`), dispatching workers with vectored review and `/leave-feedback` audited replies for comments, rebases, CI failures, and 24h reminders.
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
- `bugbash`: lead-only multi-reviewer bug investigation and fix workflow—gathers full bug/linked context, swarms read-only reviewers with `find-it` (shrinking repros first, testing candidate fixes in Slates VFS volumes or throwaway scratch worktrees) and peer `challenge` (with fresh runs, reset timers, and convergence fallback) logging rejected theories (`decided:`), dispatches workers with `fix-it` in isolated Slates VFS volumes/worktrees, passes original bug docs plus rejected theories and failed fix attempts to post-fix reviewers instructed to apply `prove-it` and attach PR proof, and turns fixes, rejected theories, and failed attempts into durable lessons via `make-it-stick`.

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
- `technical-writing`: standard for concise, concrete, code-verified technical docs.
- `wat`: rewrites the last message to lead with the bottom line and cut jargon and meta-commentary.
- `rtfm`: checks your prompt, repo docs/code/history, local environment, and official docs before asking questions.
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
- `make-it-stick`: logs scoped session lessons in `LESSONS.md` and prevents repeats via architecture -> types -> lint -> test -> docs.

## Under the hood

- **Agents:** `lead` (program coordinator & merge/review gatekeeper), `worker` (builds one task within its time limit, reports losses first), `reviewer` (read-only adversarial vectored review), and `researcher` (read-only codebase walks & A–F primary-source research)—shipped as full native agents across Claude Code (`.md`), Codex (`.toml`), Antigravity (`.md` with `subagent`/`mainAgent`), Cursor (`.md` with `is_background`), Devin (`.md`), and Pi (`.md` with `tools`/`readOnly`), and installable via `astack-tools install-agents`.
- **CLI scripts (`bin/`):**
  - `astack-status`: active workers, reviewers, and researchers, their timers/wind-down clocks, latest branch commits, and open questions (`--line` for status bars).
  - `astack-decisions`: query `decided:` entries and verbatim `person:` directives (`--query`, `--settled-by`, `--since`, `--json`).
  - `astack-verify-merge`: verifies a claimed commit is on the target branch, audits strictly `--base <last-verified-target>..<sha>` (or every parent side of a merge commit when `--base` is omitted, never trusting commit messages; fails closed on checker errors; `--strict-gates` blocks without countersign), and can run checks in a clean worktree.
  - `astack-check-gates`: structural tripwire auditing a git range (`<base>..<head>`) or commit for deleted/renamed tests, skips, lint/typecheck suppressions, assertion downgrades, cross-diff test swaps, tautologies, loosened numeric tolerances, and CI/lint/gate config edits.
  - `astack-review-ledger`: evaluates vectored review saturation over proven blocking bugs with fix-equivalence overlap verification, 2-reviewer Chapman + exact hypergeometric lower/upper bounds, 3+-reviewer Burnham–Overton $M_h$ jackknife + Beta-Binomial $M_h$ profile-likelihood bounds (observable-class saturation: "these models stopped finding new bugs", never falsely claiming 95% proof that hard bugs are absent), empirical catch-rate calibration from `scripts/eval.py --calibrate` (no picked 0.5 constant), landing-block gating on non-saturated risky vectors, internal Markdown coverage maps, and `LANES.md` review-count lines.
  - `astack-dispatch`: cross-harness dispatcher and `reviewer_pool` reachability checker supporting Claude (`claude`), Codex (`codex`), Antigravity (`agy`), Cursor CLI (`cursor-agent`/`agent`), Devin (`devin`), Pi (`pi`), Gemini (`gemini`), and custom CLI templates, enforcing pool approval and writing auditable JSON receipts.
  - `astack-watch-pr`, `astack-watch-github`, `astack-watch-gitlab`, `astack-watch-bitbucket`: stdlib-only PR/MR watchers for GitHub (`github.com` + GHES), GitLab (`gitlab.com` + self-hosted with nested subgroups), and Bitbucket (Cloud REST 2.0 + Server/Data Center REST 1.0) with good-citizen rate-limit pacing (`ETag`/`304`, consolidated GraphQL with automatic REST fallback, `Retry-After`/`X-RateLimit-*`/`RateLimit-*`/`X-RateLimit-NearLimit` adaptation, idle backoff, per-PR locks), fork-isolated stacked PR/MR ordering, crash-safe `watch/<PR>.md` handoff markers, `patch-id-check` (`git patch-id` + `git range-diff` rebase verification), `diff-guard` (review-round diff-growth guard), `authorship-check` (takeover credit & `Co-authored-by` preservation), `autonomy`-enforced & `/leave-feedback`-audited `reply` subcommands, and idempotent lead remediation dispatch (`--role lead`, delegating edits to workers while running lead-owned vectored review and reply audits).
  - `astack-statechart`: runs TLC in `-tool` mode with `-dump dot,actionlabels`, single-worker minimum-depth BFS default (`--workers 1`), `--timeout`, and `--no-deadlock` (or parses DOT/trace output offline, rejecting malformed input), follows TLC exit status strictly, preserves multiple broken invariants per state, finds shortest paths via full untruncated state matching, and renders collision-safe Mermaid `stateDiagram-v2` (tested against 40 real `.tla`/`.cfg` specs recorded with TLC 2.19 and re-checked live in CI, plus a 10-spec live BFS differential fuzzer).
  - `astack-stamp` (+ post-edit hook): timestamps new lines appended to `LANES.md`.
  - `astack-tools`: links `astack-*` CLI scripts onto `PATH` (`link-bin`), provisions Python `>=3.11` via `uv` across macOS/Linux/Windows (arm64 & amd64), and manages an isolated venv for `taskex`, `orchestral`, and `werkflow` (`doctor`, `install`, `link-bin`, `python`, `werkflow`, `env`, `path`).
- **Evals & CI:** 21 multi-harness, zero-hint outcome evals under `evals/` (cold-start skill discovery without `/astack:go`, worker wind-down/reports, Go-mode routing & dedicated agent spawning, multi-file planted-bug & decoy review, cross-harness review, context/contradiction/coding-rule review, pre-post PR comment auditing via `leave-feedback`, multi-file gamed-gate rejection, `find-it`/`fix-it` repro-shrinking and explicit-state bug fixing, lead `bugbash` reviewer-swarm convergence + `prove-it` PR evidence, 6 coding rules) with behavioral reproduction verifiers (`verify.py` + `evals/_repro_verify.py` executing saved reproductions against buggy, all-fixed, and leave-one-bug-in copies), `--calibrate` empirical per-model catch-rate measurement, and `--ablation with-without`, runnable on Claude Code, Codex, Antigravity (`agy`), Cursor CLI, Devin, or Pi via `python3 scripts/eval.py --harness <name>`, plus GitHub Actions CI ([.github/workflows/ci.yml](./.github/workflows/ci.yml)).

## Working on astack

Edit source at the root (`skills/`, `agents/`, `bin/`, `evals/`, `packaging/`), rebuild `harness/`, run tests, and commit both:

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
