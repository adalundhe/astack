---
name: whatsup
description: "Single-pane-of-glass catch-up and context rebuild after a break, restart, or compaction: waiting decisions, bugs/regressions, milestones, experiments/research, and active work. Use for /astack:whatsup or catching up on a project."
disable-model-invocation: true
---

# Whatsup

Give the person one concise engineering brief of what changed since their last check-in, and rebuild working context cleanly from durable state after a break, restart, or compaction.

## 1. Reconstruct live state from durable sources—never memory

- **Program records:** under `~/.cache/astack/` (or the named program folder), read `RULES.md` (including `## Revisions`), active briefs, recent reports, and PR markers (`watch/*.md`). Run `astack-status` and `astack-decisions` (filtering `--since` the last `person:` line when catching up).
- **Code and shipping:** check `git status`, `git worktree list`, `git log`, active branches, stashes, open PRs, and CI status.
- **Experiments, research, and lessons:** check benchmark write-ups, A/B and `clamber` logs, **research-this** findings, `AD_*.draft.md` drafts, `dagify` graphs, and saved lessons via **lookup** (`astack-tools lessons list`).
- **Reconcile drift:** flag mismatches between recorded state and reality (dead workers still marked running, unlogged commits, unverified merges lacking `astack-verify-merge`, or stale workspaces).

## 2. Present strictly in this order

Omit empty sections or write `none`:

1. **Waiting on you:** unanswered questions, approvals, PRs stuck 24h+, or human-only blockers (like interactive auth). Frame each as a plain choice with your pick (**decisions-in-plain-words**). Never list internal astack state here (single-model reviewer pool, `settings.json` defaults, model rosters, worktree paths).
2. **Bugs, regressions, and losses:** new bugs, regressions, failed runs, failing CI, overdue workers, unmerged work, or state drift—impact first.
3. **Features, fixes, and milestones:** shipped capabilities and resolved bugs stated as user impact (verified SHAs or PR numbers in parentheses—not raw commit dumps).
4. **Hypotheses, experiments, and research:** what we tested, proved, or disproved (A/B winners, grafted ideas, losers with numbers, A–F research grades) and how it changed the plan.
5. **Decisions settled:** notable `decided:` and verbatim `person:` entries since last check-in, naming the choice and evidence.
6. **In flight and next:** active lanes, running experiments, open PRs, and the next concrete milestone.

## 3. Keep it sharp

Lead every bullet with what matters, cut internal task IDs and process narration (**wat**), and mark claims as measured, verified, or inferred. Stay read-only when only reporting. When resuming after a break, log any `correction:` line in `LANES.md` and continue immediately on unblocked work.

Referenced skills: `research-this` (`${CLAUDE_SKILL_DIR}/../research-this/SKILL.md`), `lookup` (`${CLAUDE_SKILL_DIR}/../lookup/SKILL.md`), `decisions-in-plain-words` (`${CLAUDE_SKILL_DIR}/../decisions-in-plain-words/SKILL.md`), `wat` (`${CLAUDE_SKILL_DIR}/../wat/SKILL.md`). Read any cited skill file before acting when its trigger applies.
