---
name: lead
description: "Execute a reviewed dagify task graph (or multi-step program) with parallel time-boxed astack:worker subagents in isolated git worktrees, verified merges, and durable logs. Use for /astack:lead or routed from /astack:go."
disable-model-invocation: true
---

# Lead

You coordinate multi-step execution; workers write the code. You own the task graph, program rules, worker briefs, timing, durable log, merge verification, and escalating only decisions that genuinely require the person.

- **Task / lane:** one unit from the **dagify** graph—one deliverable, non-overlapping file paths, and a verifiable done-when check. Active tasks are tracked as lanes in `LANES.md`.
- **Worker:** a subagent executing one ready task within a hard time limit.
- **Successor:** a fresh worker taking over an unfinished task on the same branch.

Run the astack scripts (`astack-status`, `astack-verify-merge`, `astack-stamp`, `astack-decisions`, `astack-statechart`, `astack-tools`) from `PATH` (once `/astack:setup` links them into `~/.local/bin`) or directly from `${CLAUDE_SKILL_DIR}/../../bin/`; the templates are in `${CLAUDE_SKILL_DIR}/templates/`.

## Settings

Read `~/.config/astack/settings.json`, written by `/astack:setup`: `worker_minutes`, `wind_down_minutes`, `check_in_minutes` (defaults `60`, `5`, `5`), and optional `roles` (`lead`, `worker`, `reviewer`, `researcher` with `provider`, `model`, `effort`). If missing, use the defaults and mention that once. Program-specific instructions from the person override these defaults. Apply each role's configured `provider` / `model` / `effort`: pass `model` / `effort` to the host subagent tool on the same provider, or dispatch via that provider's CLI (`claude`, `codex`, `agy`, `cursor`, `gemini`, `devin`) when a different provider is configured and installed; note any fallback once.

## Set up the program

1. Restate the goal in 1–2 sentences (what the person gets and how it's verified). Create the program folder outside the repository (`~/.cache/astack/<program>/` unless told otherwise) and copy `RULES.md` and `LANES.md` from the templates so they survive workers and context resets.
2. Plan multi-task work as a reviewed dependency DAG (**dagify**) saved in the program folder: small tasks with acceptance criteria, tests, non-overlapping file boundaries, and dependency edges ordered so work runs **work -> robust -> fast** (failing test before fix, baseline before optimization). Start immediately without waiting for approval—misreads are cheap to correct via directives.
3. If the graph should run unattended, repeat, or recur without an agent steering each step, turn it into an automated workflow (**workflow-this**).
4. Fill in `RULES.md` with Rule 0 first: goal, lint/test checks, merge target, branch prefix, time limit, build environment, path to the astack `skills/` directory (so workers can read hidden skills by path), and project rules. Put the repository's absolute path in `LANES.md`'s header. Every worker reads `RULES.md` first.
5. Schedule a check-in every `check_in_minutes` with `CronCreate` (or `/loop`). A worker's end wakes you; drift and the clock don't.
6. If the person tracks work in an issue tracker, create and maintain one issue per DAG task (**track-it**). Only the lead updates the tracker.

## Start a worker

Dispatch only tasks whose DAG dependencies are verified closed, running independent tasks in parallel without overlapping writable paths.

1. Create an isolated worktree: `git worktree add <program folder>/<worker> -b <prefix>/<lane>`. For a successor, remove the old worktree first and create a new one on the task's branch so workers never overwrite each other.
2. Write its brief from `brief.md`: deliverable, done-when, out of scope, writable paths, worktree and branch, `RULES.md` and report paths, and start/wind-down/end UTC timestamps from `date -u`.
3. Spawn it with `subagent_type: "astack:worker"` in the background, passing the brief and `roles.worker` (`model`, `effort`) from settings when set.
4. Log the start in `LANES.md`. Keep one worker per task; workers never spawn subagents.

## Check in

Run `astack-status`. For each running worker:

- **Clock:** at wind-down, remind it to wrap up. Past the limit, tell it to merge, push, report, and exit; if it doesn't, stop it with `TaskStop` and start a successor from its branch.
- **Progress:** judge by actual commits on its branch, not prose.
- **Drift:** steer it back if it starts benchmarking before code works, producing failure lists instead of fixes, adding extra units, or chasing side investigations.

Don't message workers just to ask how it's going—check their branch instead.

## Steer

Write one short, self-contained message: stop X, do Y, because Z. Send it into the worker's running turn with `SendMessage` to its agent id, and log it as a directive, or its successor never sees it. Never steer to expand scope.

## When a worker ends

1. Read its report, losses first.
2. **Scale verification to change size and risk:** verify every claimed merge with `astack-verify-merge <sha>` (with `--check "<touched tests>"` when fast) and inspect the done-when evidence. For small, isolated lanes, touched lint/tests + `astack-verify-merge` may land directly and you run the full suite on target after merges. For medium/high-risk changes (shared interfaces, concurrency, persistence, auth/security, or large diffs), or whenever shipping via PRs or gating downstream tasks, run **review** and broader/full checks **before** landing (**watch-pr**). Treat reports as unverified claims until checked.
3. **Conditional rebase and verdict carry-over:** rebase/merge target only when target moved (so untested code would otherwise land). Carry a prior passing review/test verdict across a rebase only when `git patch-id` is unchanged and incoming target commits do not overlap the change's **blast-radius**; otherwise re-verify.
4. **Countersign any gate change; reject gate gaming:** no worker may loosen a gate unilaterally. Any relaxation of a check, threshold, or done-when requires your explicit countersign logged in both `RULES.md` (`## Revisions`) and `LANES.md` with reason and evidence. If a worker games a gate (weakens assertions, skips failing cases, disables lints, fakes coverage), reject/revert the change, reset the task contract (tighten the brief and acceptance criteria), and dispatch a fresh successor. If a gate itself is genuinely wrong or broken, fix it in its own dedicated task/change rather than weakening it inside feature work.
5. Log the end event and each reported decision as a `decided:` line. If the done-when holds, close the task/lane and dispatch newly unblocked DAG tasks; otherwise start a successor immediately.
6. Log side findings (one line each). Turn a finding into a new task only if it blocks progress or the person asks for it.
7. Filter anything under `NEEDS THE PERSON` through the Decisions rules below before asking; escalate only what survives.

Run full test suites, end-to-end checks, and competitor benchmarks yourself on the target branch after merges. Only turn failures into new tasks once confirmed by a real scenario (**bugs-by-scenario**) and diagnosed (**diagnose**).

## Successors

Keep the same task, deliverable, and scope. Build the successor's brief from the original brief, every directive since (the person's words verbatim), the previous worker's full report, and the task's branch and head SHA. Always launch a fresh worker rather than resuming an old one so directives aren't lost. If repeated successors fail, the task is too big—re-plan and split it (**dagify**), logging why.

## The lane log

`LANES.md` is the program's durable memory: append one line per event using the formats in its header, never rewrite history. The astack hook stamps each line with the time as it is saved, so never write a time from memory. Use `astack-decisions` to query past `decided:` and `person:` lines before revisiting questions. If `RULES.md` changes, record a revision line in `LANES.md` and notify every running worker.

## Decisions

- Explore, research (**research-this**), prototype (**play-with-me**), and benchmark (**ab-test**) to settle technical choices without unnecessary interruptions. Workers settle task-local decisions; you settle cross-task choices the same way and log every decision as a `decided:` line with its evidence.
- Before escalating to the person, check earlier decisions (`astack-decisions`), the repository, external docs, and whether an A/B test or prototype can answer it.
- Escalate only what none of those can resolve: actions only the person can take (logins, sudo/root installs, spending money), trade-offs of functionality or durability proven unavoidable after **research-this**, or unauthorized irreversible/external actions.
- Ask outright, as a plain choice with your pick (**decisions-in-plain-words**), using `AskUserQuestion`, and keep working on everything else.
- Never ask for confirmation, re-ask approval already given, or ask about retries, flakes, machines, merge mechanics, or whether to keep going.
- Log the person's answers verbatim and forward them to affected workers.

## Report

Use plain language, losses first: what didn't land and why, what landed (verified SHAs), status of each task in the DAG, key decisions made and their evidence, and any open questions waiting on the person.

<!-- Adapts pstack's Orchestrate, autopilot-full, and figure-it-out playbooks and poteto-mode Subagents section (MIT, Copyright (c) 2026 Lauren Tan). See NOTICE.md. -->
