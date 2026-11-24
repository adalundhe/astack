---
name: track-it
description: "Create and maintain issues for lanes in the project's tracker (GitHub, Jira, Linear, etc.) without duplicates, updating states on events and closing with proof. Run by the lead when tracking is requested."
disable-model-invocation: true
---

# Track it

Create and keep issues up to date in the project's issue tracker.

Only the lead updates the tracker; workers report to the lead and don't edit tickets directly.

1. **Identify the tracker:** use what the person specified, or infer it from repo conventions (commit messages, PR links, branch names—**rtfm**). If none exists, ask which tracker to use while continuing unblocked work.
2. **Use existing credentials:** use the tracker's authenticated CLI, API, or connected tool. If not logged in, ask the person to sign in.
3. **Match project structure:** map goals to epics/milestones, tasks to issues/stories, and dependencies to "blocked by" links, following existing templates and labels.
4. **Populate issues from the task plan** (**dagify**): outcome-oriented title, description, acceptance criteria, test plan, and link to the plan.
5. **Avoid duplicates:** search existing issues first and keep a task-to-issue mapping so reruns update existing tickets instead of creating copies (**safe-to-rerun**).
6. **Sync on state transitions:** move issues on real events—in progress on start, in review when PR opens, done on verified merge, blocked with reason (**event-driven**).
7. **Close with proof:** record what changed, the PR/SHA, and how done-when was verified (**prove-it**). If a task is split or re-planned, note that on the ticket instead of deleting it.
8. **Limit notifications** to the person (or anyone they explicitly ask to include).

Referenced skills: `rtfm` (`${CLAUDE_SKILL_DIR}/../rtfm/SKILL.md`), `dagify` (`${CLAUDE_SKILL_DIR}/../dagify/SKILL.md`), `safe-to-rerun` (`${CLAUDE_SKILL_DIR}/../safe-to-rerun/SKILL.md`), `event-driven` (`${CLAUDE_SKILL_DIR}/../event-driven/SKILL.md`), `prove-it` (`${CLAUDE_SKILL_DIR}/../prove-it/SKILL.md`). Read any cited skill file before acting when its trigger applies.
