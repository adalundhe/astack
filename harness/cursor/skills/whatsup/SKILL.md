---
name: whatsup
description: "Single-pane-of-glass catch-up and context rebuild after a break, restart, or compaction: waiting decisions, bugs/regressions, features/fixes/milestones, hypotheses/experiments/research proved or disproved, and active work. Use for /whatsup or when catching up on a project."
disable-model-invocation: true
---

# Whatsup

Give the person a single-pane-of-glass engineering brief covering everything meaningful that happened since their last check-in—and rebuild full working context cleanly from durable state after a break, session restart, or context compaction.

1. **Reconstruct live state from durable sources** (never rely on memory):
   - **Program records** (when an astack program exists under `~/.cache/astack/` or a named folder): read `RULES.md` (including `## Revisions`), run `astack-status` and `astack-decisions` (filtering `--since` the last `person:` line in `LANES.md` when catching up), read active briefs, recent worker reports, and PR watch markers (`watch/*.md`).
   - **Code, branches, and shipping:** inspect `git status`, `git worktree list`, merged commits (`git log`), active branches, stashes, open PRs, and CI status.
   - **Experiments, research, and planning:** check recent benchmark write-ups, A/B and `clamber` logs, `research-this` findings (or `kiln` records), `AD_*.draft.md` drafts, `dagify` task graphs, and `LESSONS.md` (project and `~/.config/astack/LESSONS.md`).
   - **Reconcile drift:** flag mismatches between recorded state and reality (e.g. a worker marked running whose process is gone, branches with unlogged commits, claimed merges not yet verified with `astack-verify-merge`, or stale worktrees).
2. **Present strictly in this order** (omit empty sections or write `none`):
   - **Waiting on you:** unanswered questions, approvals needed, PRs stuck 24h+, or blockers only the person can resolve (e.g., interactive login/auth)—each framed as a plain choice with your recommendation (**decisions-in-plain-words**). Never list internal harness/astack state (single-model reviewer pool, `settings.json` defaults, model rosters, worktree paths) here.
   - **Bugs, regressions, and losses:** new bugs encountered, regressions caught, failed runs/experiments, failing CI, workers past their limit, unmerged work, or state drift—impact first.
   - **Features, fixes, and milestones:** concrete capabilities shipped, bugs resolved, and significant milestones reached, written in terms of user/system impact (with verified SHAs or PR numbers in parentheses—not raw commit dumps).
   - **Hypotheses, experiments, and research:** what we tested, proved, or disproved—A/B winners, grafted ideas, and losers with numbers, benchmark shifts, key concepts/data/limits uncovered (with A–F grades when from **research-this**), and how they changed our plan.
   - **Decisions settled:** notable choices resolved while the person was away (`decided:` entries and verbatim `person:` directives), naming the choice and what settled it.
   - **In flight and next:** active lanes/workers, running experiments, open PRs, and the next concrete milestone.
3. **Keep it sharp:** lead every bullet with what matters, cut internal task IDs and process narration (**wat**), and mark whether claims are measured, verified, or inferred. Stay read-only when simply reporting; if invoked to resume work after a break, log any needed `correction:` line in `LANES.md` and continue immediately on unblocked work.

Referenced skills: `decisions-in-plain-words` (`../decisions-in-plain-words/SKILL.md`), `research-this` (`../research-this/SKILL.md`), `wat` (`../wat/SKILL.md`). Read any cited skill file before acting when its trigger applies.
