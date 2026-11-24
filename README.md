# astack

astack holds coding agents to a careful engineer's standard: small pieces of work, each proven; choices settled by measurement; code checked against clear rules; nothing claimed without evidence the person can rerun. Its lead runs a program of work as lanes: each lane is one deliverable with a clear definition of done, built by a worker within a hard time limit, while the lead checks in, verifies every merge, keeps a lane log, and brings the person only real decisions. Every skill also works on its own.

It works in Claude Code, Cursor and Codex. It is modeled on Cursor's [pstack](https://github.com/cursor/plugins/tree/main/pstack).

## The method

- **Lanes.** One deliverable each, with a stated point at which it is done.
- **Order.** Make it work, then make it robust, then make it fast.
- **No scope growth.** No extra units, no "if time allows". A side finding gets one line in the report and is left alone.
- **A hard time limit.** At the wind-down point, a worker merges what is green, pushes the rest to its branch, reports losses first, and ends.
- **Successors.** A new worker on the same lane, briefed with the original brief, every later directive, and the previous worker's report.
- **The lead.** It checks in on a fixed schedule, verifies every merge itself, steers workers with short messages, and keeps the lane log.
- **Autonomy, on the record.** Agents are free to explore, research, form hypotheses, try things, succeed, fail, learn and improve. They settle questions from the person's earlier decisions, the repository, outside research, an A/B or a proof of concept, and record every decision with what settled it. They don't ask for confirmation, for approval already given, or for what an A/B or a proof of concept can settle. Only what none of those settles reaches the person, such as a sign-in or an install as root, asked as a plain choice.
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

In Claude Code, run a skill as `/astack:<name>`. In Cursor it's `/<name>` and in Codex `$<name>`, except `lead`, `setup`, `status` and `review`, which take an `astack-` prefix there.

**Running a program**

| Part | What it does |
|---|---|
| `lead` | Runs a program as lanes: rules, briefs, workers, check-ins, merge checks, successors, the lane log, decisions. |
| `worker` agent | Builds one lane within its time limit, decides for itself, and reports losses first. |
| `reviewer` agent | Reviews one change by trying to break it the way its users would. |
| `dagify` | Breaks a request into a graph of small tasks, each with criteria and tests, ordered to run in parallel. |
| `workflow-this` | Turns a task graph into a workflow that runs itself, with explicit states, and resumes after a crash. |
| `track-it` | Creates and manages issues and tickets for agent work in your tracker (GitHub, Jira, Linear or another); run by the lead. |
| `review` | Sends reviewers to break a change, keeping only findings a rerun proves. |
| `setup` | Sets the worker time limit, the wind-down point and the check-in interval. |
| `status` | Shows running workers, their clocks and last commits, and questions waiting on you. |

**Pull requests**

| Skill | What it does |
|---|---|
| `watch-pr` | Takes a PR to ready-to-merge: CI, every comment, a flag to you every 24 hours, hand-over at the time limit. |
| `address-feedback` | Closes every finding and comment: fix it, answer it, or show it's wrong. |
| `leave-it-better` | Fixes the broken tests, builds and checks you run into, in a separate PR. |

**Understanding and explaining**

| Skill | What it does |
|---|---|
| `play-it-back` | Restates what you want, one line each you can correct. |
| `talk-to-me` | Explains an idea with the field's terms, a picture, a worked example and an analogy. |
| `play-with-me` | Makes a small, throwaway demo, mockup or script so you can try an idea before it's built, and presents it unasked. |
| `how-it-works` | Explains part of a system, every claim cited to the code. |
| `show-the-states` | Draws how a system moves between states, what triggers each move, and how it fails. |
| `wat` | Rephrases the last message clearly: impact and decisions first, no jargon or internal references. |
| `rtfm` | Reads what already exists before asking you anything. |
| `decisions-in-plain-words` | Brings you only what's yours to decide, as a plain choice with a recommendation. |

**Deciding and measuring**

| Skill | What it does |
|---|---|
| `research` | Finds what's already known, ranked by how far it can be trusted, and cited. |
| `deeper` | Rewrites a task to the standard of the best in its field, without growing it. |
| `explore-the-limits` | Builds competing implementations and keeps the measured winner. |
| `ab-test` | Settles a choice by measuring the options. |
| `decide-by-data` | Chooses by measurement, never by argument. |
| `benchmarking` | Writes and runs benchmarks the way tests are written: from the criteria, across the spectrum, against known noise. |
| `fair-benchmarks` | Compares against other systems fairly. |

**Proving it works**

| Skill | What it does |
|---|---|
| `prove-it` | Checks results on the real thing, and backs claims with evidence you can rerun. |
| `test-drive` | Gives a project a scripted way to use the real app as its users do. |
| `every-case` | Formally verifies a promise that tests can't reach. |
| `bugs-by-scenario` | Treats a bug as real only when a real scenario shows it. |
| `tests-assert-behaviour` | The testing Principle: tests check behaviour users can observe. |
| `full-spectrum-testing` | Writes a task's tests across the diamond and the full spectrum of failure. |
| `blast-radius` | Finds what a change could break beyond its diff. |

**Improving code**

| Skill | What it does |
|---|---|
| `clamber` | Improves performance toward a goal in small measured steps, each committed, and reverted if it regresses. |
| `simplify-me` | Makes code you just wrote or are reviewing smaller, clearer and easier to test, without losing correctness or speed. |
| `modularize` | Splits monolithic code into modules that each do one job, test alone and swap behind small interfaces, without needless abstraction. |

**Review and rules**

| Skill | What it does |
|---|---|
| `adversarial-review` | Reviews a change by trying to break it in its real setting, blockers first. |
| `worrywart` | Refutes a wrong review point with evidence. |
| `no-implicit-states` | State machines are explicit: named states, transitions in one place. |
| `no-hidden-flow-control` | Failures are handled specifically or returned as typed values. |
| `no-hidden-config` | Every setting is read in one place, documented and tested. |
| `minimize-state-stores` | Each piece of data lives in one place; caches must be measured into existence. |
| `check-your-boundaries` | Outside data is parsed once where it enters, then trusted. |
| `no-shared-writes` | Concurrent writers each get their own state; locks are the last resort. |
| `safe-to-rerun` | Operations end in the right state however often they run. |
| `no-bolt-ons` | New requirements are designed in, not bolted on. |
| `yagni` | One path per job: no shims, aliases or legacy paths. |
| `comment-cop` | Code explains itself; comments keep only what code can't say. |
| `delight-users` | The user's experience beats the builder's convenience. |
| `no-picked-constants` | Limits, timeouts and sizes are learned or derived, never picked. |
| `event-driven` | Work wakes on events, never on timers or polling. |
| `never-trade-functionality` | A faster version still does everything the slower one did. |

**Learning and records**

| Skill | What it does |
|---|---|
| `make-it-stick` | Records what worked and what failed with the conditions each held under; a success is a hypothesis for a matching situation, never a default. |
| `automate-this` | Replaces repeated manual work with scripts and watchers. |
| `create-adc` | Works out an architecture decision with you and records it as the project's next AD document. |

**Tools**

| Part | What it does |
|---|---|
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
