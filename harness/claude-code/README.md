# astack

astack runs a program of work as lanes. A lead agent splits the program into lanes, each one deliverable with a clear definition of done. A worker subagent builds each lane within a hard time limit. The lead checks in on a schedule, verifies every merge, starts successors, keeps a lane log, and brings the person only real decisions.

It works in Claude Code, Cursor and Codex. It is modeled on Cursor's [pstack](https://github.com/cursor/plugins/tree/main/pstack).

## The method

- **Lanes.** One deliverable each, with a stated point at which it is done.
- **Order.** Make it work, then make it robust, then make it fast.
- **No scope growth.** No extra units, no "if time allows". A side finding gets one line in the report and is left alone.
- **A hard time limit.** At the wind-down point, a worker merges what is green, pushes the rest to its branch, reports losses first, and ends.
- **Successors.** A new worker on the same lane, briefed with the original brief, every later directive, and the previous worker's report.
- **The lead.** It checks in on a fixed schedule, verifies every merge itself, steers workers with short messages, and keeps the lane log.
- **Decisions.** Workers decide for themselves: from the person's earlier decisions, the repository, outside research, then an A/B. Only what none of those settles reaches the person, such as a sign-in or an install as root, asked as a plain choice.
- **Bugs.** A bug is real when a real scenario shows it: the query, the workload, the benchmark against competitors.
- **Standing rules.** Decide by data, with a controlled A/B. Benchmarks are fair. No picked constants. Event-driven, not timers. Never trade functionality for speed. Tests assert behaviour. Plain words to the person.

## Install

**Claude Code**

```
/plugin marketplace add adalundhe/astack
/plugin install astack@astack
```

Or from a shell: `claude plugin marketplace add adalundhe/astack`, then `claude plugin install astack@astack`. On Claude Code 2.1.275 or later, `/plugin install astack --marketplace adalundhe/astack` does both. Restart, or run `/reload-plugins`.

**Cursor**

In Cursor, open **Customize**, choose **From GitHub Repository**, and enter `adalundhe/astack`.

**Codex**

```
codex plugin marketplace add adalundhe/astack
codex plugin add astack@astack
```

Then start a new session.

## Set up

Run setup once, and again whenever you want to change it:

| Claude Code | Cursor | Codex |
|---|---|---|
| `/astack:setup` | `/astack-setup` | `$astack-setup` |

It asks how many minutes a worker may run, how long before that limit it winds down, and how often the lead checks in. The defaults are 60, 5 and 5. It saves your answers to `~/.config/astack/settings.json`. In Codex, it also installs the worker agent, which Codex plugins can't ship.

## Start a program

| Claude Code | Cursor | Codex |
|---|---|---|
| `/astack:lead` | `/astack-lead` | `$astack-lead` |

Follow it with the program: the goal, how it is measured, the lanes you know of, and where merges go.

```
/astack:lead Make the export pipeline 10x faster at p99 on the 10 GB sample, with byte-identical output,
measured against the current release on the same machine and client. Lanes I know of: streaming writer,
parallel compression. Merges go to main after lint and the tests a worker touched.
```

The lead restates the goal, lists the lanes, writes the program's rules and lane log under `~/.cache/astack/<program>/`, and starts a worker per lane. You hear from it only when a decision is yours. To change course, tell the lead; it logs your words and passes them on. For a view of running workers, their clocks and last commits, run `/astack:status` (Cursor `/astack-status`, Codex `$astack-status`).

## What's inside

| Part | What it does |
|---|---|
| `lead` skill | Runs the program: rules, briefs, workers, check-ins, steering, merge verification, successors, the lane log, decisions. |
| `worker` agent | Builds one lane: rules first, one deliverable, work then robust then fast, its own design choices settled by A/B, merge after lint and the tests it touched, wind down on time, report losses first. |
| `ab-test` skill | Settles a choice by measuring: quantifiable metrics, the best-suited environment set up without asking, baseline noise, a meaningful-improvement bar, a worktree per variant and combination, production builds, anomalies recorded, a plain write-up, then the decision. |
| `create-adc` skill | Works out an architecture decision with you, one evidenced decision at a time, and writes it up as the project's next architecture decision document of record (AD-N). |
| `setup` skill | Sets the worker time limit, the wind-down point and the check-in interval. |
| `status` skill | Shows running workers, their clocks and last commits, lanes, and questions waiting on you. |
| Eight rule skills | `decide-by-data`, `fair-benchmarks`, `bugs-by-scenario`, `no-picked-constants`, `event-driven`, `never-trade-functionality`, `tests-assert-behaviour`, `decisions-in-plain-words`. |
| Templates | A program's `RULES.md` (rule 0 first), a worker's brief, the lane report and the lane log. |
| `astack-verify-merge` | Verifies a claimed merge in one step: the commit is on the target, what it changed, and optionally a check on the target's tip. |
| `astack-status` | Prints the status view, or one line with `--line`. |
| Lane log hook | Stamps each lane log line with the UTC time as it is saved. |
| Evals | Claude Code evals that check a worker winds down on time and reports losses first. |

## Working on astack

The source is at the repository root: `skills/`, `agents/`, `bin/`, `evals/`, and each tool's manifest, hook and wording in `packaging/`. `python3 scripts/build.py` writes the three packages under `harness/`; commit them with the source. `python3 -m unittest discover -s tests` runs the tests, which fail if `harness/` is out of date.

To run the evals, which need a Claude Code login and use your plan: `claude plugin eval harness/claude-code --trust-plugin --scaffold --ablation none`. `--scaffold` lets each case put its `RULES.md` where the worker's brief points.

## Credits and license

astack is MIT licensed; see [LICENSE](./LICENSE). It adapts parts of pstack by Lauren Tan under pstack's MIT license; [NOTICE.md](./NOTICE.md) names the files and carries that license.
