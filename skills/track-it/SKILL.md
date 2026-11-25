---
name: track-it
description: "Turn specs or DAGs into dependency-ordered tracker issues and sync state transitions with proof. Use when creating or updating tracker tickets."
disable-model-invocation: true
---

# Track it

Create and maintain dependency-ordered issues in the project's tracker (GitHub Issues, Jira, Linear, etc.). For watching queues and driving tickets via `go`, use **sprint**.

Only the Lead updates the tracker, because parallel worker edits create duplicates and status conflicts. Workers report outcomes to the Lead instead.

## 1. Confirm tracker and credentials

1. **Identify the tracker.** Use what the person named, or infer it from commits, PR links, and branch names. Ask if none exists while continuing unblocked work.
2. **Verify credentials read-only.** Run `astack-watch-tickets auth-check --tracker <tracker> --json` (or the tracker's authenticated CLI). If auth fails, isolate the human login step (**decisions-in-plain-words**). Never retry bad credentials.

## 2. Spec -> Blocked-Tickets flow

1. **Anchor with a parent Epic or PRD issue.** Summarize the spec, goals, and architecture in a reachable tracker issue or repo doc. Never link unreachable local `~/.cache/astack/` paths inside external tickets.
2. **Draft slices and confirm first.** Split the spec or **dagify** plan into vertical, testable slices with a `Blocked by` DAG. Confirm titles, acceptance criteria, and order first, honoring `~/.config/astack/settings.json` `autonomy`.
3. **Avoid duplicates.** Search existing issues before creating anything. Save the task-to-issue mapping in `<program>/tickets.json` so reruns update existing tickets instead of duplicating them.
4. **Create upstream blockers first.** Follow topological order so root issues exist before dependents. Every `Blocked by` link then resolves to a real `#N` or `KEY`.
5. **Gate `sprint` readiness.** Include an outcome-oriented title, parent Epic link, acceptance criteria, test plan, and `Blocked by` refs. Never tag a blocked downstream ticket as `sprint`-ready until upstream blockers close.

## 3. Sync states and close with proof

1. **Move on real transitions.** Mark `in progress` on start and `in review` when the PR opens. Mark `done` on verified merge, or `blocked` with the blocker ref.
2. **Close with proof (**prove-it**).** Post what changed, the PR or SHA, and how done-when passed. When a ticket splits or re-plans, note the update instead of deleting it.
3. **Keep notifications narrow.** Notify only the person or people explicitly requested.

**Reply:** list the parent Epic ref, created or updated ticket IDs in dependency order, `<program>/tickets.json`, and ready vs. blocked tickets.
