# astack

A plugin for Claude Code, Cursor, and Codex with a single low-context entry point (`go`), a lead/worker runner for larger multi-step tasks, and 60 hidden on-demand skills for code review, benchmarking, testing, research, debugging, handling PRs, and coding rules.

Long agent sessions tend to go off the rails in predictable ways: the agent wanders into unrelated refactors, stops every few minutes to ask questions the repo or a quick test could answer, claims a fix works without running it, or runs out of context with half-finished work sitting unmerged on a branch. `astack` puts structure around that—while keeping only one skill (`go`) in the model catalog so idle sessions don't burn thousands of tokens listing 60 skills.

Parts of it are adapted from Cursor's [pstack](https://github.com/cursor/plugins/tree/main/pstack) and [mattpocock/skills](https://github.com/mattpocock/skills).

## Install

### Claude Code

```
/plugin marketplace add adalundhe/astack
/plugin install astack@astack
```

Restart Claude Code or run `/reload-plugins`. To update to a newer release later:

```
claude plugin marketplace update astack
claude plugin update astack@astack
```

### Cursor

Open **Customize**, choose **From GitHub Repository**, and enter `adalundhe/astack`.

### Codex

```
codex plugin marketplace add adalundhe/astack
codex plugin add astack@astack
```

Start a new session and run `$astack-go setup`. Codex plugins can't ship agent definitions directly, so setup copies `astack-worker.toml` and `astack-reviewer.toml` into `~/.codex/agents/` (and reminds you to trust the timestamp hook in `/hooks`).

## Getting started with `go`

`/astack:go` (Cursor: `/astack-go`, Codex: `$astack-go`) is the only skill loaded into the model's skill catalog. Every other skill is marked `disable-model-invocation: true` and read on demand by path when `go` routes to it.

- In **Claude Code** and **Cursor**, you can either start with `/astack:go` (`/astack-go`) or call any individual skill directly (`/astack:<name>` / `/<name>`).
- In **Codex**, start through `$astack-go` (e.g. `$astack-go setup`, `$astack-go whatsup`, `$astack-go <your task>`) and it reads the matching hidden skill file by path.

### Optional setup (timing and per-role models)

Defaults are 60-minute worker limit, 5-minute wind-down buffer, 5-minute lead check-in interval, and your active session's model across roles. To customize timing or per-role `model`, `provider`, and `effort`, run:

```
/astack:setup
```

That writes `~/.config/astack/settings.json` (and on Codex, installs `astack-worker.toml` and `astack-reviewer.toml` with any configured `model`, `model_provider`, and `model_reasoning_effort`).

### Running bigger tasks with `lead`

Give `/astack:lead` (or `/astack:go` with a multi-step goal) the outcome, how to verify it, and where merges should go:

```
/astack:lead Make the export pipeline 10x faster at p99 on the 10 GB sample, with byte-identical output,
measured against the current release on the same machine. Merges go to main after lint and tests.
```

What happens when you run it:

- The lead splits the goal into **lanes**, each with one deliverable and a concrete "done when" check (a command and output, a passing scenario, or a commit on the target branch), ordered so things work before anyone starts optimizing.
- Each lane gets its own git worktree, branch, written brief, and a time-boxed `worker` subagent (using `roles.worker` from `settings.json` where supported).
- Program rules (`RULES.md`) and an append-only event log (`LANES.md`, timestamped automatically by a hook) live outside the repo in `~/.cache/astack/<program>/`, so they survive context limits and worker restarts.
- On each check-in, the lead checks actual branch commits and remaining time instead of pinging workers for status updates.
- When a worker finishes or hits its wind-down time, it merges what's green, pushes the rest, and writes a report starting with what failed or didn't get done. The lead verifies every claimed SHA with `astack-verify-merge` instead of taking the worker's word for it, and spawns a fresh worker on the same branch (with the original brief, prior report, and any directives since) if the lane isn't done yet.
- Workers are expected to settle design and implementation questions themselves (via the repo, `research-this`, prototypes, or A/B benchmarks) and log what decided them. You only get interrupted for things an agent can't resolve on its own: credentials or logins, root installs, functionality trade-offs proven unavoidable after `research-this`, or irreversible external actions.

Check active workers anytime with `/astack:status` (or `astack-status --line` for a status bar), get a full engineering catch-up or rebuild context after a break with `/astack:whatsup`, and query past decisions with `astack-decisions`.

## Skills

All 61 skills below (`go` + 60 hidden skills read on demand). In Cursor and Codex, `go`, `lead`, `setup`, `status`, and `review` take an `astack-` prefix (`/astack-go`, `$astack-go`, etc.).

### Entry point, orchestration, and catch-up

- `go`: single catalog-visible entry point that routes to every other astack skill and coding rule on demand by path.
- `lead`: runs a multi-lane program, managing git worktrees, time-boxed workers, check-ins, merge verification, and the lane log.
- `setup`: saves timing settings and per-role `provider`, `model`, and `effort` to `~/.config/astack/settings.json` (and installs the worker and reviewer agents on Codex).
- `status`: shows active workers, remaining time, latest commits per branch, lane states, and unanswered questions.
- `whatsup`: single-pane-of-glass catch-up and context rebuild after a break or compaction—waiting decisions, bugs/regressions, features/fixes/milestones landed, hypotheses/experiments/research proved or disproved, and active work.
- `dagify`: breaks a larger task into a dependency graph of smaller tasks with acceptance criteria and tests, ordered so independent tasks can run in parallel without editing the same files.
- `workflow-this`: turns a `dagify` task graph into a resumable script or pipeline with explicit task states.
- `track-it`: creates and updates issues for lanes in your tracker (GitHub Issues, Jira, Linear, etc.).

### Code review and PRs

- `review`: spawns `reviewer` subagents in separate worktrees to attack a branch or PR across user flows, concurrency/failure edge cases, and all 15 coding rules; reruns every finding to drop false positives and reports confirmed blockers first.
- `adversarial-review`: the single-reviewer playbook: reproduce the bug before the change, verify the fix, try to break edge cases in the real environment, and report only reproducible issues.
- `challenge`: peer-to-peer, role-agnostic adversarial interrogation of hypotheses, repeated fixes, diagnoses, designs, or implementations until every load-bearing assumption is proven or conceded.
- `worrywart`: pushes back on a review comment (human or agent) with concrete evidence when it's wrong, unreproducible, already handled elsewhere, or not worth the complexity.
- `blast-radius`: traces what a change could break outside its diff (callers, shared state, indirect assumptions) and runs code to verify it's safe.
- `watch-pr`: opens a PR after review, monitors CI and comments in the background instead of polling manually, fixes failures, replies to threads, pings you if it sits open for 24h, and hands off cleanly at the time limit.
- `address-feedback`: works through every review finding or PR comment (blockers first) by fixing it, answering it, or disproving it, replying directly on each thread.
- `leave-it-better`: fixes unrelated broken tests, builds, or CI checks you trip over at their root cause in a separate PR instead of working around them.

### Benchmarking and experiments

- `benchmarking`: writes and runs benchmarks against user-visible metrics across normal load, overload, contention, and injected faults, measuring baseline noise first.
- `ab-test`: compares competing designs, implementations, or configs in isolated worktrees with alternating rounds, grafts winning ideas from losers into the winner, and deletes the rest.
- `decide-by-data`: settles design or config trade-offs with measurements instead of guessing or debating.
- `fair-benchmarks`: checklist for competitor benchmarks: same machine and client, stock/shipped settings on each side, errors counted, alternating runs.
- `clamber`: iterative optimization loop: baseline a metric, change one thing at a time, commit gains, revert regressions.
- `explore-the-limits`: researches prior art, builds competing implementations in parallel worktrees, benchmarks them, grafts the best parts of losing attempts into the winner, and deletes the rest.

### Testing and verification

- `prove-it`: verifies results against the real build or artifact instead of mocks or proxies, and gives you a command to rerun the check yourself.
- `test-drive`: creates and maintains a project-local `drive-<app>` skill that launches the real app (browser, PTY/CLI, or HTTP), exercises user flows, and saves screenshots or transcripts as proof.
- `every-case`: sets up and maintains formal verification (TLA+, code verifiers, or generated inputs) for concurrency, state machines, protocols, or parsers, and replays counterexamples against the real code.
- `tests-assert-behaviour`: keeps tests checking user-visible behavior instead of internal implementation details, mocks, or timing assumptions.
- `full-spectrum-testing`: writes tests beyond the happy path: integration and end-to-end coverage, failure modes, edge cases, races, fuzzing, and injected faults.
- `bugs-by-scenario`: reproduces a failing test or suspected bug in a realistic user scenario (and checks whether `main` already fails) before spending time fixing it.

### Refactoring and cleanup

- `simplify-me`: trims down code you just wrote or are reviewing without losing correctness, edge-case handling, or speed.
- `modularize`: splits an overgrown file, function, or package into smaller single-purpose modules behind narrow interfaces, matching the codebase's style.
- `rearchitect`: identifies structural friction in high-churn areas, ranks restructurings with before-and-after diagrams, and executes the top pick via `dagify`.
- `deeper`: rewrites a task brief before starting so the agent works from primary sources, domain tools, and external specs or reference suites instead of taking shortcuts, without expanding scope.
- `cleanup`: removes temporary files, build artifacts, caches, test data, and processes created by your work without touching anything else or still needed.

### Coding rules

All 15 rules below are indexed in `go` and read by path whenever their trigger fires (and checked by `review`):

- `data-structures-first`: design data representations, invariants, ownership, and access patterns before writing algorithms or control flow.
- `no-implicit-states`: use explicit state enums/types and centralized transitions instead of scattered boolean flags.
- `no-hidden-flow-control`: handle specific errors where they occur or return typed error values; avoid broad `try/catch` blocks and swallowed exceptions.
- `no-hidden-config`: read settings and env vars in one place, document defaults and valid values, test each value, and use real feature flags instead of hidden toggles.
- `minimize-state-stores`: keep one source of truth for each piece of data; only add caches or copies when measurements justify them.
- `check-your-boundaries`: parse and validate untrusted input (requests, CLI args, config, files, DB rows) once at the edge into typed values, then trust those types inside.
- `no-shared-writes`: give concurrent workers or threads their own state and merge on read before introducing locks.
- `safe-to-rerun`: make commands, migrations, jobs, and retries idempotent (atomic writes/renames, safe recovery from partial runs) so rerunning or crashing halfway still ends right.
- `no-bolt-ons`: fold new requirements into the existing design instead of adding special-case flags, `_v2` copies, or wrapper patches.
- `yagni`: migrate callers and delete old code paths together; don't keep shims, deprecated aliases, or dead flags unless asked.
- `comment-cop`: cut comments that just restate the code; keep only what code can't show (API contracts, external constraints, legal headers, issue links).
- `delight-users`: check work from the consumer's side (end user, API caller, or operator) for missing loading/empty/error states, unhelpful errors, awkward APIs, and bad defaults.
- `no-picked-constants`: replace hardcoded arbitrary timeouts, batch sizes, and limits with values derived from system/protocol bounds or adapted at runtime.
- `event-driven`: wait on completion events or signals instead of `sleep` loops, fixed timers, or polling.
- `never-trade-functionality`: block speed or memory optimizations that quietly drop features, return stale or approximate results, or weaken guarantees, requiring `research-this` before accepting any trade-off.

### Understanding, specs, docs, and communication

- `how-it-works`: read-only walkthrough of an unfamiliar part of the repo with file/line citations, marking each claim as actually run vs. read.
- `show-the-states`: diagrams a system's state transitions, triggers, failure paths, and observed frequencies when data exists.
- `run-it-back`: restates your request, scope, exclusions, and assumptions as short checkable lines before writing code.
- `play-with-me`: builds a small throwaway mockup, script, or demo so you can try an idea before implementing it for real.
- `talk-to-me`: explains an unfamiliar concept or design with proper domain terms, a diagram, a worked example, and a short analogy.
- `technical-writing`: standard for clear, concrete, verified technical docs (READMEs, guides, API refs, ADs, runbooks) with runnable examples and zero fluff.
- `wat`: rewrites the agent's last message to lead with the bottom line and strip out jargon, internal state, and meta-commentary.
- `rtfm`: makes the agent check your message, repo docs, code, git history, and local environment before asking you a question or saying it lacks context.
- `research-this`: investigates a question across internal sources (code, logs, docs) and external sources (specs, papers, official docs), verifies quotes against citations, and grades each finding A–F (integrating with `kiln` when available).
- `decisions-in-plain-words`: makes the agent resolve what it can itself, log why, and only escalate decisions that actually need a human, formatted as a direct choice with a recommendation.
- `create-adc`: works through an architecture decision with you one question at a time (backed by research, scenarios, and a cost ledger) and writes it up as the project's next `AD_<N>.md`.

### Automation and session notes

- `automate-this`: replaces repeated manual commands, polling, or noisy searches with scripts or watchers so bulk output stays out of context.
- `make-it-stick`: reviews a session transcript, logs scoped lessons in `LESSONS.md`, and makes recurring mistakes impossible using a strict fix ladder (architecture -> types -> lint/hook -> test -> docs last).

## Agents, scripts, evals, and CI

- **Subagents:** `worker` executes a single lane within its time limit and reports failures/gaps first; `reviewer` tries to break a change in its real environment without modifying product code.
- **Scripts and hook:** `astack-status` prints worker timers, last commits, lane states, and open questions (`--line` for a status bar); `astack-decisions` queries `decided:` entries and verbatim `person:` directives from `LANES.md` (`--query`, `--settled-by`, `--since`, `--json`); `astack-verify-merge` confirms a claimed commit is on the target branch and can run a check command in a clean detached worktree; `astack-stamp` (wired to a post-edit hook) timestamps new lines appended to `LANES.md`.
- **Templates:** `RULES.md`, `LANES.md`, `brief.md`, and `report.md` under `skills/lead/templates/`.
- **Companion automation libraries:** `automate-this` and `workflow-this` integrate with [taskex](https://github.com/adalundhe/taskex) (lightweight async Python/shell tasks), [orchestral](https://github.com/adalundhe/orchestral) (async task-graph orchestration), and [werkflow](https://github.com/adalundhe/werkflow) + [werkflow-modules](https://github.com/adalundhe/werkflow-modules) (sophisticated scripted workflows).
- **Evals:** 9 Claude Code eval cases under `evals/` covering worker wind-down/losses-first reports, Go-mode hidden-rule routing, and 6 core coding rules (`no-implicit-states`, `no-hidden-flow-control`, `check-your-boundaries`, `no-picked-constants`, `never-trade-functionality`, `safe-to-rerun`).
- **CI:** GitHub Actions ([.github/workflows/ci.yml](./.github/workflows/ci.yml)) runs `python3 scripts/build.py --check` and the full `unittest` suite on every push to `main` and pull request.

## Working on astack

Edit source files at the repository root (`skills/`, `agents/`, `bin/`, `evals/`, and per-tool configs in `packaging/`), then regenerate the three packages under `harness/` and run the test suite:

```bash
python3 scripts/build.py
python3 -m unittest discover -s tests
```

Commit both the source and `harness/` changes; CI and the tests fail if `harness/` is out of sync, if a skill isn't indexed in `go` or `README.md`, or if any non-`go` skill leaks into the model catalog.

To run the Claude Code evals (requires a Claude Code login and uses your plan):

```bash
claude plugin eval harness/claude-code --trust-plugin --scaffold --ablation none
```

## License

MIT ([LICENSE](./LICENSE)). Parts of astack adapt ideas and skills from Lauren Tan's [pstack](https://github.com/cursor/plugins/tree/main/pstack) and [mattpocock/skills](https://github.com/mattpocock/skills); see [NOTICE.md](./NOTICE.md) for the file-by-file breakdown and licenses.
