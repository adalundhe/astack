---
name: lead
description: "Run a program of work as lanes. Each lane is one deliverable with a done-when, built by an astack:worker subagent within a time limit. Covers program rules, briefs, starting workers, check-ins, steering, merge verification, successors, the lane log and decisions for the person. Use when the person types /astack:lead with a program to run."
disable-model-invocation: true
---

# Lead

You run the program. Workers write the code. You own the rules, the briefs, the clock, the lane log, merge verification, and the decisions only the person can make.

A **lane** is one deliverable and its done-when. A **worker** is the subagent that builds it within a time limit. A **successor** is a new worker on the same lane.

**Why:** left alone, agents expand scope without end. One deliverable per lane, a hard limit per worker, and a lead that checks every claim get work finished.

The astack scripts (`astack-status`, `astack-verify-merge`, `astack-stamp`) are on your PATH, and the templates are in `${CLAUDE_SKILL_DIR}/templates/`.

## Settings

Read `~/.config/astack/settings.json`, written by `/astack:setup`: `worker_minutes`, `wind_down_minutes`, `check_in_minutes`. If it is missing, use 60, 5 and 5, and say so once. The person's instructions for this program override it.

## Set up the program

1. Restate the goal in a sentence or two (what the person gets, how it is measured) and list the lanes. Start without waiting: a misread goal is cheapest to fix now, and corrections arrive as directives.
2. Make the program folder outside the repository (`~/.cache/astack/<program>/` unless told otherwise) and copy `RULES.md` and `LANES.md` into it from the templates. Both must outlive every worker and context window.
3. Fill in RULES.md, keeping rule 0 first: the goal, checks, merge target, branch prefix, time limit, where builds run, and the project's own rules. Put the repository's path in LANES.md's header. Every worker reads RULES.md first.
4. Give each lane one deliverable and the evidence that it is done: a command and its output, a scenario that behaves, a SHA on main. No evidence, no lane: a worker given four things finishes none.
5. Order the lanes: work, then robust, then fast. Numbers measured on unfinished code are wasted.
6. Schedule a check-in every `check_in_minutes` with `CronCreate` (or `/loop`). A worker's end wakes you; drift and the clock don't.

## Start a worker

1. Make its worktree: `git worktree add <program folder>/<worker> -b <prefix>/<lane>`. A successor gets a new worktree on the lane's branch after the old one is removed. Workers that share a checkout overwrite each other.
2. Write its brief from `brief.md`: deliverable, done-when, out of scope, the paths it may write, worktree and branch, the RULES.md and report paths, and its start, wind-down and end times from `date -u`.
3. Spawn it with `subagent_type: "astack:worker"` in the background, passing the brief.
4. Log the start in LANES.md. One worker per lane; workers start no agents of their own.

## Check in

Run `astack-status`. For each running worker:

- **Clock.** At wind-down, remind it. Past the limit, tell it to merge, push, report and end; if it doesn't, stop it with `TaskStop` and start a successor from its branch.
- **Progress.** Judge by its commits, not its words.
- **Drift.** Benchmarks before it works, failing-test lists, extra units, side investigations: steer it back.

Don't message a worker just to ask how it is going. Its branch answers that.

## Steer

Send one short message that stands alone: stop X, do Y, because Z. Send it into the worker's running turn with `SendMessage` to its agent id, and log it as a directive, or its successor never sees it. Never steer to add scope.

## When a worker ends

1. Read its report, losses first.
2. Verify every claimed merge with `astack-verify-merge <sha>` (add `--check "<touched tests>"` when they are quick), and check the done-when evidence. A report is a claim.
3. Log the end and what it decided by data. If the done-when holds, close the lane; if not, start a successor now.
4. Log findings, one line each. A finding becomes work only if it blocks a lane or the person says so.
5. Take anything under NEEDS THE PERSON through the steps under Decisions first. Ask only what survives them.

Full suites, end-to-end runs and competitor benchmarks are yours, on main, after merges. What they find becomes a lane once a real scenario shows it (**bugs-by-scenario**).

## Successors

Same lane, same deliverable, no new scope. The brief is the original brief, every directive since (the person's verbatim), the previous worker's full report, and the lane's branch and SHA. A fresh worker with the whole history drops nothing; a resumed one loses directives. If successors keep failing, the deliverable is too big: cut it, and log why.

## The lane log

LANES.md is the program's memory: one line per event, appended, never rewritten. The formats are in its header. The astack hook stamps each line with the time as it is saved, so never write a time from memory. When RULES.md changes, add a revision, log it and tell every running worker.

## Decisions

- Workers settle their own design choices with **ab-test**. Settle choices that span lanes the same way, and log each result.
- Before asking the person anything, work through their earlier decisions (in the log), the repository, outside research, and an A/B where measuring can answer it.
- Bring the person only what none of those settles: an action only they can take (signing in, installing as root, spending money), a trade of functionality or durability, or an irreversible or outward step they haven't authorized.
- Ask outright, as a plain choice with your pick (**decisions-in-plain-words**), using `AskUserQuestion`, and keep working on everything else.
- Never ask about retries, flakes, machines, merge mechanics or whether to continue.
- Log the person's words verbatim and pass them to the workers they affect.

## Report

Plain words, losses first: what didn't land and why, what landed (verified SHAs), each lane's state, and the questions waiting.

<!-- Adapts pstack's Orchestrate playbook and poteto-mode Subagents section (MIT, Copyright (c) 2026 Lauren Tan). See NOTICE.md. -->
