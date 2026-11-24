---
name: lead
description: "Run a multi-step program as isolated git-worktree lanes with time-boxed astack:worker subagents, scheduled check-ins, verified merges, and an append-only lane log. Use when invoked via /astack:lead or routed from /astack:go."
disable-model-invocation: true
---

# Lead

You coordinate the program; workers write the code. You own program rules, worker briefs, timing, the lane log, merge verification, and escalating only decisions that genuinely require the person.

- **Lane:** one deliverable and its verifiable done-when condition.
- **Worker:** a subagent building one lane within a hard time limit.
- **Successor:** a fresh worker taking over an unfinished lane on the same branch.

The astack scripts (`astack-status`, `astack-verify-merge`, `astack-stamp`, `astack-decisions`, `astack-tools`) are on your PATH, and the templates are in `${CLAUDE_SKILL_DIR}/templates/`.

## Settings

Read `~/.config/astack/settings.json`, written by `/astack:setup`: `worker_minutes`, `wind_down_minutes`, `check_in_minutes` (defaults `60`, `5`, `5`), and optional `roles` (`lead`, `worker`, `reviewer`, `researcher` with `provider`, `model`, `effort`). If missing, use the defaults and mention that once. Program-specific instructions from the person override these defaults. Pass configured role `model` / `effort` when spawning subagents wherever the host tool supports it; otherwise note the fallback once.

## Set up the program

1. Restate the goal in 1–2 sentences (what the person gets and how it's verified) and list the lanes. Start immediately without waiting for approval—misreads are cheap to correct via directives.
2. Create the program folder outside the repository (`~/.cache/astack/<program>/` unless told otherwise) and copy `RULES.md` and `LANES.md` from the templates so they persist across workers and context resets.
3. Fill in `RULES.md` with Rule 0 first: goal, lint/test checks, merge target, branch prefix, time limit, build environment, path to the astack `skills/` directory (so workers can read hidden skills by path), and project rules. Put the repository's absolute path in `LANES.md`'s header. Every worker reads `RULES.md` first.
4. Give every lane exactly one deliverable and concrete done-when evidence (a command and output, a passing scenario, or a SHA on the target branch). No done-when, no lane.
5. Order lanes strictly: work first, then robust, then fast. Don't benchmark unfinished code.
6. Schedule a check-in every `check_in_minutes` with `CronCreate` (or `/loop`). A worker's end wakes you; drift and the clock don't.
7. If the person tracks work in an issue tracker, create and maintain one issue per lane (**track-it**). Only the lead updates the tracker.

## Start a worker

1. Create an isolated worktree: `git worktree add <program folder>/<worker> -b <prefix>/<lane>`. For a successor, remove the old worktree first and create a new one on the lane's branch so workers never overwrite each other.
2. Write its brief from `brief.md`: deliverable, done-when, out of scope, writable paths, worktree and branch, `RULES.md` and report paths, and start/wind-down/end UTC timestamps from `date -u`.
3. Spawn it with `subagent_type: "astack:worker"` in the background, passing the brief and `roles.worker` (`model`, `effort`) from settings when set.
4. Log the start in `LANES.md`. Keep one worker per lane; workers never spawn subagents.

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
2. Verify every claimed merge with `astack-verify-merge <sha>` (with `--check "<touched tests>"` when fast) and inspect the done-when evidence. Treat reports as unverified claims until checked.
3. Log the end event and each reported decision as a `decided:` line. If the done-when holds, close the lane; otherwise start a successor immediately.
4. Log side findings (one line each). Turn a finding into a lane only if it blocks progress or the person asks for it.
5. Filter anything under `NEEDS THE PERSON` through the Decisions rules below before asking; escalate only what survives.

Run full test suites, end-to-end checks, and competitor benchmarks yourself on the target branch after merges. Only turn failures into new lanes once confirmed by a real scenario (**bugs-by-scenario**).

## Successors

Keep the same lane, deliverable, and scope. Build the successor's brief from the original brief, every directive since (the person's words verbatim), the previous worker's full report, and the lane's branch and head SHA. Always launch a fresh worker rather than resuming an old one so directives aren't lost. If repeated successors fail, the lane is too big—split it and log why.

## The lane log

`LANES.md` is the program's durable memory: append one line per event using the formats in its header, never rewrite history. The astack hook stamps each line with the time as it is saved, so never write a time from memory. Use `astack-decisions` to query past `decided:` and `person:` lines before revisiting questions. If `RULES.md` changes, record a revision line in `LANES.md` and notify every running worker.

## Decisions

- Explore, research (**research-this**), prototype (**play-with-me**), and benchmark (**ab-test**) to settle technical choices without unnecessary interruptions. Workers settle lane-local decisions; you settle cross-lane choices the same way and log every decision as a `decided:` line with its evidence.
- Before escalating to the person, check earlier decisions (`astack-decisions`), the repository, external docs, and whether an A/B test or prototype can answer it.
- Escalate only what none of those can resolve: actions only the person can take (logins, sudo/root installs, spending money), trade-offs of functionality or durability proven unavoidable after **research-this**, or unauthorized irreversible/external actions.
- Ask outright, as a plain choice with your pick (**decisions-in-plain-words**), using `AskUserQuestion`, and keep working on everything else.
- Never ask for confirmation, re-ask approval already given, or ask about retries, flakes, machines, merge mechanics, or whether to keep going.
- Log the person's answers verbatim and forward them to affected workers.

## Report

Use plain language, losses first: what didn't land and why, what landed (verified SHAs), status of each lane, key decisions made and their evidence, and any open questions waiting on the person.

Referenced skills: `track-it` (`${CLAUDE_SKILL_DIR}/../track-it/SKILL.md`), `bugs-by-scenario` (`${CLAUDE_SKILL_DIR}/../bugs-by-scenario/SKILL.md`), `research-this` (`${CLAUDE_SKILL_DIR}/../research-this/SKILL.md`), `play-with-me` (`${CLAUDE_SKILL_DIR}/../play-with-me/SKILL.md`), `ab-test` (`${CLAUDE_SKILL_DIR}/../ab-test/SKILL.md`), `decisions-in-plain-words` (`${CLAUDE_SKILL_DIR}/../decisions-in-plain-words/SKILL.md`). Read any cited skill file before acting when its trigger applies.

<!-- Adapts pstack's Orchestrate playbook and poteto-mode Subagents section (MIT, Copyright (c) 2026 Lauren Tan). See NOTICE.md. -->
