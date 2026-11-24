# astack

astack makes coding agents work like the engineers you'd want on your team. They take one job at a time and prove it works. They make it work, then robust, then fast. They measure instead of guessing, try to break their own work before anyone else can, and make their own calls, writing down why. They come to you only when they truly need you.

It runs in Claude Code, Cursor and Codex, and grew out of Cursor's [pstack](https://github.com/cursor/plugins/tree/main/pstack).

## What we believe

- **Work, then robust, then fast.** In that order, every time.
- **Measure, don't guess.** Choices get settled by testing them. Numbers are learned or derived, never picked.
- **Faster never means less.** A quicker version still does everything the slower one did.
- **Cut before you add.** A good change often leaves less code. If the code can say it, a comment shouldn't.
- **Prove it.** Check the real thing, and show the work in a way anyone can rerun.
- **Leave it better.** If something broken is in your way, fix it, even if you didn't break it.
- **Freedom, on the record.** Agents explore, try things, fail and learn. They write down every decision, and don't ask you to confirm what they can settle themselves.
- **Keep it human.** Write code and words for the person reading them at 3am: impact first, plain, nothing they haven't seen.

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

Set the clocks once: how long a worker may run, when it starts wrapping up, and how often the lead checks in. Unless you say otherwise, that's 60, 5 and 5 minutes.

```
/astack:setup
```

Then give the lead a goal: what you want, how you'll know it's done, and where merges go.

```
/astack:lead Make the export pipeline 10x faster at p99 on the 10 GB sample, with byte-identical output,
measured against the current release on the same machine. Merges go to main after lint and tests.
```

The lead plans the work, starts a worker for each piece, checks every merge itself, and keeps a log under `~/.cache/astack/<program>/`. You'll hear from it when something is genuinely yours to decide. `/astack:status` shows who's working on what.

In Cursor, these are `/astack-setup`, `/astack-lead` and `/astack-status`; in Codex, `$astack-setup`, `$astack-lead` and `$astack-status`. In Codex, setup also installs the worker agent, which Codex plugins can't ship.

## The skills

Use any skill on its own, or let the lead and its workers reach for them as they go. Run one as `/astack:<name>` in Claude Code, `/<name>` in Cursor, or `$<name>` in Codex. In Cursor and Codex, `lead`, `setup`, `status` and `review` take an `astack-` prefix.

**Plan and run the work**

- `lead`: runs a program. It splits the work up, starts a worker for each piece, checks in, verifies every merge, and brings you only real decisions.
- `dagify`: breaks a request into small tasks, each with criteria and tests, ordered so most can run at once.
- `workflow-this`: turns that plan into a workflow that runs itself, and picks up where it left off after a crash.
- `track-it`: keeps the work in your issue tracker.
- `setup` and `status`: set the clocks, and see who's working on what.

**Ship it**

- `watch-pr`: takes a pull request to ready-to-merge.
- `address-feedback`: answers every review comment with a fix, an answer or evidence.
- `leave-it-better`: fixes the broken things you trip over, in their own PR.

**Review it**

- `review`: sends reviewers to break the work. Only findings a rerun proves survive.
- `adversarial-review`: how each reviewer does it: reproduce the problem, confirm the fix, then attack it like a user would.
- `worrywart`: pushes back on a review point with evidence, not argument.
- `blast-radius`: finds what a change could break beyond its diff.

**Write it well**

Each rule says what to start with, what to watch for, and when it doesn't fit.

- `no-implicit-states`: make state machines explicit.
- `no-hidden-flow-control`: no catch-alls; handle failures where they happen, or return them as values.
- `no-hidden-config`: every setting visible, documented and tested.
- `minimize-state-stores`: keep each piece of data in one place; caches have to earn theirs.
- `check-your-boundaries`: parse outside data once, at the edge, then trust it.
- `no-shared-writes`: give each writer its own state before reaching for a lock.
- `safe-to-rerun`: run it twice or crash it halfway, and it still ends up right.
- `no-bolt-ons`: design a new requirement in; don't bolt it on.
- `yagni`: one path per job, no shims or leftovers.
- `comment-cop`: if the code can say it, no comment.
- `delight-users`: the user's experience beats the builder's convenience.
- `no-picked-constants`: learn or derive every number.
- `event-driven`: wake on events, not timers.
- `never-trade-functionality`: faster never means less.

**Make it better**

- `simplify-me`: make what you just wrote smaller and clearer, without losing anything.
- `modularize`: split monolithic code into modules that each do one job.
- `clamber`: climb toward a performance goal in small, measured, committed steps.
- `explore-the-limits`: build competing versions and keep the measured winner.
- `deeper`: do the task the way the best in the field would, without making it bigger.

**Measure and prove**

- `benchmarking`, `ab-test`, `decide-by-data` and `fair-benchmarks`: measure properly, then decide.
- `tests-assert-behaviour` and `full-spectrum-testing`: test what users see, in every way it can break.
- `prove-it`: check the real thing, and show your evidence.
- `test-drive`: drive the real app the way its users do.
- `every-case`: formally verify what tests can't reach.
- `bugs-by-scenario`: a bug is real when a real scenario shows it.
- `research`: find out what's already known before building.

**Talk it through**

- `play-it-back`: say back what you heard, so a misunderstanding costs a line, not a build.
- `talk-to-me`: explain an idea with the right words, a picture, an example and an analogy.
- `play-with-me`: make a small demo or mockup to try before anything gets built.
- `how-it-works`: explain part of a system, every claim pointing at the code.
- `show-the-states`: draw how a system moves between states, and how it fails.
- `wat`: say that again, clearly.
- `rtfm`: read what's already there before asking.
- `decisions-in-plain-words`: decide what you can, and bring people only what's theirs.

**Learn**

- `make-it-stick`: keep what worked and what failed, with the conditions each held under.
- `automate-this`: script what repeats.
- `create-adc`: work out an architecture decision, and write it down.

**Agents:** `worker` builds one piece of a program within its time limit and reports what it lost first. `reviewer` reviews one change by trying to break it.

**Under the hood:** templates for a program's rules, a worker's brief, its report and the lane log; `astack-verify-merge`, which checks a claimed merge in one step; `astack-status`; a hook that timestamps the lane log; and evals that check workers wind down on time and report losses first.

## Working on astack

Edit the source at the root (`skills/`, `agents/`, `bin/`, `evals/`, and each tool's packaging in `packaging/`), run `python3 scripts/build.py` to regenerate the three packages under `harness/`, and commit both. `python3 -m unittest discover -s tests` runs the tests, which fail if `harness/` is stale.

The evals need a Claude Code login and use your plan: `claude plugin eval harness/claude-code --trust-plugin --scaffold --ablation none`.

## Credits

astack is MIT licensed ([LICENSE](./LICENSE)). It borrows good ideas from Lauren Tan's [pstack](https://github.com/cursor/plugins/tree/main/pstack), also MIT; [NOTICE.md](./NOTICE.md) lists what we adapted and carries its license.
