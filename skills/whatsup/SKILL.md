---
name: whatsup
description: "Deliver a concise catch-up brief and rebuild context from durable state after a break or compaction. Use for /astack:whatsup or catching up."
disable-model-invocation: true
---

# Whatsup

Give one concise brief of what changed since the last check-in. Rebuild working context from durable files after a break, restart, or compaction.

## 1. Reconstruct live state from durable sources—never memory

Read durable artifacts first, because compaction drops context silently. If no program folder exists yet, build the brief from git, open PRs, CI, and saved lessons.

- **Program records.** Under `~/.cache/astack/` (or the named folder), read `RULES.md` (`## Revisions`), active briefs, recent reports, and PR markers (`watch/*.md`). Run `astack-status` and `astack-decisions` (filter `--since` the last `person:` line).
- **Code and shipping.** Check `git status`, `git worktree list`, and `slates volume list` (if installed). Inspect `git log`, branches, stashes, open PRs, and CI status.
- **Experiments, research, and lessons.** Check benchmark write-ups, `ab-test`/`clamber` logs, `research-this` notes, `AD_*.draft.md`, `dagify` graphs, and **lookup** (`astack-tools lessons list`).
- **Reconcile drift.** Flag mismatches between logs and reality. Catch dead workers marked running, unlogged commits, unverified merges lacking `astack-verify-merge`, or stale workspaces.

## 2. Present strictly in this order

Omit empty sections or write `none`:

1. **Waiting on you.** List unanswered questions, approvals, PRs stuck 24h+, or human-only blockers like interactive auth. Frame each as a plain choice with your pick (**decisions-in-plain-words**). Never list internal state here (single-model reviewer pool, `settings.json` defaults, model rosters, worktree paths).
2. **Bugs, regressions, and losses.** Lead with impact: new bugs, regressions, failed runs, red CI, overdue workers, unmerged work, or state drift.
3. **Features, fixes, and milestones.** State shipped features and fixed bugs as user impact. Put verified SHAs or PR numbers in parentheses—never raw commit dumps.
4. **Hypotheses, experiments, and research.** Summarize what we tested, proved, or disproved (A/B winners, grafts, losers with numbers, A–F grades). Note how results changed the plan.
5. **Decisions settled.** List notable `decided:` and verbatim `person:` entries since last check-in, with the choice and evidence.
6. **In flight and next.** List active lanes, running experiments, open PRs, and the next concrete milestone.

## 3. Keep it sharp

Lead every bullet with what matters and cut internal IDs or narration (**wat**). Tag claims as measured, verified, or inferred. Stay read-only when only reporting. When resuming after a break, log any `correction:` line in `LANES.md` and resume unblocked work.

**Done when:** all six sections match live disk, git, and PR state with zero memory-only guesses, and any drift is flagged plainly.
