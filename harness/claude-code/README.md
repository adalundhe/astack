# astack

astack is a Claude Code plugin for running a program of work with a lead agent and workers: tightly scoped work, a clear definition of done, and nothing past it.

> "Left unsupervised, agents will simply infinitely expand scope. We want a complete implementation first, a robust one second, and a performant one third. Make it work, make it robust, make it fast." (Ada Lündhé)

It is modeled on Cursor's [pstack](https://github.com/cursor/plugins/tree/main/pstack): short skills and agents, each saying when it applies, with the reason beside each rule.

## The method

- **Lanes.** The lead splits a program into lanes. Each lane is one deliverable with a stated point at which it is done. A worker subagent builds it.
- **Order.** Make it work, then make it robust, then make it fast.
- **No scope growth.** No extra units and no "if time allows" items. A side finding gets one line in the report and is left alone.
- **One hour, hard.** At 55 minutes a worker merges what is green, pushes the rest to its branch, reports with losses first, and ends.
- **Successors.** The lead then starts a new worker on the same lane with a consolidated brief: the original brief, every later directive, and the previous worker's report.
- **The lead's job.** It checks in on a fixed schedule, verifies every claimed merge itself, steers running workers with short messages, and keeps a lane log.
- **Decisions.** The lead brings the person only real decisions, as plain choices. Anything that can be measured is measured, never asked.
- **Bugs.** A bug counts when a real scenario shows it: the query, the workload, or the benchmark against competitors. A list of failing tests doesn't.
- **Standing rules.** A/B at the extremes and decide by data. Benchmarks are fair: same client, same platform. No picked constants. Event-driven, not timers. Never trade functionality for speed. Tests assert behaviour. Plain words to the person.

## Install

In Claude Code:

```
/plugin marketplace add adalundhe/astack
/plugin install astack@astack
```

On Claude Code 2.1.275 or later, one line does both:

```
/plugin install astack --marketplace adalundhe/astack
```

From a shell:

```bash
claude plugin marketplace add adalundhe/astack
claude plugin install astack@astack
```

Restart Claude Code, or run `/reload-plugins`, to load it. To update later, run `claude plugin marketplace update astack`, then `claude plugin update astack@astack`.

Claude Code prefixes a plugin's skills and agents with its name. The lead is `/astack:lead`, and the worker agent is `astack:worker`.

## Start a program

1. Open Claude Code in the repository the program changes.
2. Type `/astack:lead`, then the program: the goal, how it is measured, the lanes you already know, and where merges go. For example:

   ```
   /astack:lead Make the export pipeline 10x faster at p99 on the 10 GB sample, with byte-identical
   output, measured against the current release on the same machine and client. Lanes I know of:
   streaming writer, parallel compression. Merges go to main after lint and the tests a worker touched.
   ```

3. The lead restates the goal, lists the lanes, writes the program's `RULES.md` and `LANES.md` (in `~/.cache/astack/<program>/` unless you name a folder), and starts a worker per lane.

From then on:

- Workers run in the background, one hour each. The lead checks in every five minutes, or at the interval you name.
- The lane log is a file you can read at any time. Every line carries a real timestamp.
- You hear from the lead when a decision is yours: one plain question, with its recommendation first.
- To change course, tell the lead. It logs your words verbatim and passes them to the workers they change.
- At the end you get a report, losses first, with every merge verified on the branch.

## What's inside

| Part | What it is |
|---|---|
| [`/astack:lead`](./skills/lead/SKILL.md) | The lead's playbook: the rules and the lane log, briefs, starting workers, check-ins, steering, merge verification, successors, and decisions to the person. You type it. |
| [`astack:worker`](./agents/worker.md) | The worker subagent: rules first, one deliverable, work then robust then fast, merge after lint and the tests it touched, wind down at 55 minutes, report losses first. The lead spawns one per lane. |
| [`templates/RULES.md`](./skills/lead/templates/RULES.md) | A project's rules for every worker, with rule 0 first. |
| [`templates/brief.md`](./skills/lead/templates/brief.md) | A worker's brief: one deliverable, its done-when, and for a successor the directives and the previous report. |
| [`templates/report.md`](./skills/lead/templates/report.md) | The lane report: a worker's final message, losses first, in a fixed format. |
| [`templates/LANES.md`](./skills/lead/templates/LANES.md) | The lane log: one line per event, stamped from the clock, append only. |
| [`decide-by-data`](./skills/decide-by-data/SKILL.md) | Choosing between two designs: build both, A/B at the extremes, let the numbers choose. |
| [`fair-benchmarks`](./skills/fair-benchmarks/SKILL.md) | Comparing against another system: the same client and the same platform. |
| [`bugs-by-scenario`](./skills/bugs-by-scenario/SKILL.md) | A failing test or suspected bug: it counts when a real scenario shows it. |
| [`no-picked-constants`](./skills/no-picked-constants/SKILL.md) | A number in code: learned where it runs, or derived from a cited source. |
| [`event-driven`](./skills/event-driven/SKILL.md) | A wait, timer or poll: wake on the event instead. |
| [`never-trade-functionality`](./skills/never-trade-functionality/SKILL.md) | A speedup that changes what users get: don't. |
| [`tests-assert-behaviour`](./skills/tests-assert-behaviour/SKILL.md) | Writing a test: assert what users observe, never elapsed time. |
| [`decisions-in-plain-words`](./skills/decisions-in-plain-words/SKILL.md) | Anything for the person: only real decisions, asked outright in plain words. |

Claude can load a standing-rule skill by itself when its trigger comes up, in the lead, a worker or any other session. You can also type one, such as `/astack:fair-benchmarks`.

## Credits and license

astack is MIT licensed; see [LICENSE](./LICENSE). It adapts parts of pstack by Lauren Tan under pstack's MIT license; [NOTICE.md](./NOTICE.md) names the files and carries that license.

## Later

- Cursor packaging, with a `.cursor-plugin/plugin.json`.
- Codex packaging.
- An eval harness: cases that check a worker winds down at 55 minutes, reports losses first and leaves side findings alone.
- A script that verifies a claimed merge in one step: SHA on the target, diff, touched tests on main.
- A hook that stamps each lane log line from the clock.
- A status view of running workers, their clocks and their last commits.
