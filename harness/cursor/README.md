# astack

Skills and agents for Claude Code, Cursor and Codex that change how coding agents work:

- A big job gets split into pieces with a clear finish line. Each piece goes to its own agent with a time limit, and nothing merges until the lead has checked it.
- Agents prove what they claim. They run the code, reproduce the bug, and show you the output instead of telling you it works.
- Choices get settled by measuring the options, and every decision is written down where you can read it.
- Reviews try to break a change the way a user would, and block only on problems they reproduced.
- Performance work starts from a full baseline, commits each gain on its own, and reverts anything that regresses.
- You get asked about sign-ins, installs and trade-offs that are yours to make, and little else.

It's modeled on Cursor's [pstack](https://github.com/cursor/plugins/tree/main/pstack).

## The rules agents follow

- Make it work, then make it robust, then make it fast.
- No number is picked out of the air: limits, timeouts and sizes are measured or derived.
- A faster version returns the same results, just as fresh, with the same guarantees.
- Code that explains itself gets no comment, and code nobody needs gets deleted.
- If something broken is in the way, fix it in its own PR, even if someone else broke it.
- Agents try things, fail and learn without asking permission, and record every decision they make.
- Anything written for a person leads with what matters to them, in plain words.

## Install

**Claude Code**

```
/plugin marketplace add adalundhe/astack
/plugin install astack@astack
```

Then restart, or run `/reload-plugins`. To pick up a new release: `claude plugin marketplace update astack`, then `claude plugin update astack@astack`.

**Cursor:** open **Customize**, choose **From GitHub Repository**, and enter `adalundhe/astack`.

**Codex**

```
codex plugin marketplace add adalundhe/astack
codex plugin add astack@astack
```

Then start a new session.

## Get started

Set how long a worker may run, when it starts wrapping up, and how often the lead checks in (60, 5 and 5 minutes by default):

```
/astack:setup
```

Then give the lead a goal: what you want, how you'll know it's done, and where merges go.

```
/astack:lead Make the export pipeline 10x faster at p99 on the 10 GB sample, with byte-identical output,
measured against the current release on the same machine. Merges go to main after lint and tests.
```

The lead splits the work, starts a worker for each piece, verifies every merge, and logs what happens under `~/.cache/astack/<program>/`. `/astack:status` shows which workers are running, their time left and their last commits.

In Cursor these are `/astack-setup`, `/astack-lead` and `/astack-status`; in Codex, `$astack-setup`, `$astack-lead` and `$astack-status`. In Codex, setup also installs the worker agent, which Codex plugins can't ship.

## The skills

Run a skill as `/astack:<name>` in Claude Code, `/<name>` in Cursor, or `$<name>` in Codex. In Cursor and Codex, `lead`, `setup`, `status` and `review` take an `astack-` prefix. Agents also use them on their own as they work.

**Plan and run the work**

- `lead`: splits a job into pieces, starts a worker for each, checks in on a schedule, verifies every merge, and asks you only what's yours to decide.
- `dagify`: turns a request into small tasks, each with acceptance criteria and tests, ordered so independent ones run in parallel.
- `workflow-this`: turns that task list into a script or automation that tracks each task's state and resumes after a crash.
- `track-it`: creates and updates issues for the work in GitHub, Jira, Linear or whatever tracker you use.
- `setup`: sets how long workers run and how often the lead checks in.
- `status`: shows running workers, their time left and their last commits.

**Ship it**

- `watch-pr`: gets a pull request to ready-to-merge: green CI, every comment handled, and a ping to you every 24 hours it waits.
- `address-feedback`: works through review comments, fixing each one, answering it, or showing with evidence why it's wrong.
- `leave-it-better`: fixes broken tests, builds and checks you run into, in a separate PR.
- `cleanup`: removes the temp files, build output, caches and test data your work left behind.

**Review it**

- `review`: sends several reviewers at a change and keeps only the problems they can reproduce.
- `adversarial-review`: reproduces the reported bug, checks the fix, then attacks the change with bad input, load, faults and races.
- `worrywart`: answers a review point you think is wrong with logs, runs and scripts, not opinion.
- `blast-radius`: finds what a change could break outside its diff, and proves why it's safe.

**Write it well**

Each of these says where to start, what to look for, and when it doesn't apply.

- `no-implicit-states`: replaces piles of flags and status strings with one explicit state type.
- `no-hidden-flow-control`: replaces catch-all error handling with specific handling or typed error values.
- `no-hidden-config`: puts every setting and environment variable in one place, documented and tested.
- `minimize-state-stores`: removes caches, copies and globals that no measurement justifies.
- `check-your-boundaries`: parses input once where it enters, so the code inside can trust it.
- `no-shared-writes`: gives each thread, process or agent its own state instead of a lock.
- `safe-to-rerun`: makes commands, jobs and migrations safe to retry or resume after a crash.
- `no-bolt-ons`: folds a new requirement into the design instead of adding special cases.
- `yagni`: deletes compatibility shims, dead paths and unused flags.
- `comment-cop`: deletes comments the code already explains.
- `delight-users`: checks the details users meet: feedback, error messages, empty and loading states, defaults.
- `no-picked-constants`: replaces hard-coded limits and timeouts with measured or derived values.
- `event-driven`: replaces sleeps, timers and polling with waits on real events.
- `never-trade-functionality`: checks that a speedup still returns the same results with the same guarantees.

**Make it better**

- `simplify-me`: shrinks and clarifies code you just wrote, keeping it as correct and as fast.
- `modularize`: splits a large file, package or codebase into modules that each do one job.
- `clamber`: improves a performance metric step by step, committing each gain and reverting each regression.
- `explore-the-limits`: builds competing implementations and keeps whichever measures best.
- `deeper`: rewrites a task to the standard the best in the field would hold it to, without adding scope.

**Measure and prove**

- `benchmarking`: writes benchmarks from performance targets, with known noise and a pass bar set in advance.
- `ab-test`: settles a choice by building each option and measuring them the same way.
- `decide-by-data`: chooses between designs by measuring them, not by arguing.
- `fair-benchmarks`: compares against other systems on the same machine with the same client.
- `tests-assert-behaviour`: tests what users can observe, never internals or timing.
- `full-spectrum-testing`: writes tests for failures, edge cases, races and injected faults, not just the happy path.
- `prove-it`: checks results on the real thing and hands you something you can rerun.
- `test-drive`: writes a script that runs the real app the way its users do.
- `every-case`: formally verifies concurrency, retries and state machines that tests can't cover.
- `bugs-by-scenario`: confirms a bug with a real query or workload before anyone fixes it.
- `research`: finds existing implementations, papers and data before anything gets built.

**Talk it through**

- `play-it-back`: restates what you asked for, so a misunderstanding is caught before work starts.
- `talk-to-me`: explains an unfamiliar idea with the right terms, a diagram, a worked example and an analogy.
- `play-with-me`: builds a quick mockup or demo you can try before the real thing is built.
- `how-it-works`: explains part of a codebase, citing a file and line for every claim.
- `show-the-states`: draws a state diagram of how a system behaves, or how it failed.
- `wat`: rephrases the last message so it's clear.
- `rtfm`: reads the docs, code and history before asking you anything.
- `decisions-in-plain-words`: settles what it can, and asks you the rest as a plain choice with a recommendation.

**Learn**

- `make-it-stick`: records what worked and what failed, and under what conditions, so the next agent knows when a lesson applies.
- `automate-this`: turns repeated commands and manual checking into scripts and watchers.
- `create-adc`: works through an architecture decision with you and writes it up as a decision record.

**Agents:** `worker` builds one piece within its time limit and reports what it didn't finish first. `reviewer` reviews one change by trying to break it.

**Also included:** templates for a program's rules, a worker's brief, its report and the log; `astack-verify-merge`, which confirms a merge landed and what it changed; `astack-status`; a hook that timestamps each log line; and evals that check workers stop on time and report losses first.

## Working on astack

Edit the source at the root (`skills/`, `agents/`, `bin/`, `evals/`, and each tool's packaging in `packaging/`), run `python3 scripts/build.py` to regenerate the three packages under `harness/`, and commit both. `python3 -m unittest discover -s tests` runs the tests, which fail if `harness/` is stale.

The evals need a Claude Code login and use your plan: `claude plugin eval harness/claude-code --trust-plugin --scaffold --ablation none`.

## Credits

astack is MIT licensed ([LICENSE](./LICENSE)). It adapts parts of Lauren Tan's [pstack](https://github.com/cursor/plugins/tree/main/pstack), also MIT; [NOTICE.md](./NOTICE.md) lists which files and carries its license.
