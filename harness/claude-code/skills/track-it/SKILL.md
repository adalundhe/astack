---
name: track-it
description: "Create and manage issues and tickets for agent work in the person's tracker (GitHub, Jira, Linear or another). Run by the lead. Use when the person wants the work tracked."
---

# Track it

Create and manage issues and tickets for agent work.

The lead does this, since it owns the plan. Workers report to the lead and don't touch the tracker.

1. **Find the tracker.** Use the one the person named. Otherwise, use the one the project already uses; commit messages, PR links and branch names usually show it (**rtfm**). If the project has none, ask the person which to use, and keep working in the meantime.
2. **Use the person's access:** the tracker's CLI, API or a connected tool, already signed in. If it isn't signed in, ask them to sign in.
3. **Use the tracker's own structure.** For example, the goal becomes an epic, project or milestone; each task becomes an issue or story; and dependencies become "blocked by" links. Follow the project's existing templates and labels.
4. **Write each issue from its task** (**dagify**): a title that states the result, the description, the acceptance criteria and the tests, and links to the plan.
5. **Check before creating.** Search for an existing issue first, and keep a list of which task maps to which issue, so running this again updates issues instead of duplicating them (**safe-to-rerun**).
6. **Update issues when things happen:** in progress when work starts, in review when the PR opens, done when it merges, and blocked with the reason (**event-driven**).
7. **Close each issue with proof:** what changed, the PR, and how you checked it's done (**prove-it**). If a task is split or re-planned, say so on the issue rather than deleting it.
8. **Notify only the person,** or whoever they ask you to.
