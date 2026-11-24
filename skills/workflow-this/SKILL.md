---
name: workflow-this
description: "Turn a /dagify task graph into a self-running, crash-resumable script or CI workflow with explicit task states and typed outcomes. Use when planned work should run or recur unattended."
---

# Workflow this

Turn a reviewed `/dagify` task graph into an automated workflow with explicit, durable task states.

1. **Start from a reviewed graph** (**dagify**): tasks, edges, acceptance criteria, and tests already verified.
2. **Choose the simplest fitting runner:** your tool's native workflow runner if available, a CI pipeline/scheduled job for unattended or recurring runs, or a script in the repo's primary language (**automate-this**).
3. **Model task states explicitly** (**no-implicit-states**): `waiting`, `ready`, `running`, `in_review`, `done`, `failed`, `blocked_on_person`, with all transitions in one place. A task becomes `ready` only when all dependencies are `done` and their reviews passed. Diagram the machine (**show-the-states**).
4. **Return typed outcomes** (**no-hidden-flow-control**): `done` (with evidence), `failed` (with reason), `inconclusive`, or `blocked` (with what the person must do). No silent failures or hidden retries.
5. **Persist per-task state durably.** Store each task's state separately so restarts resume cleanly (**no-shared-writes**) and make every step idempotent (**safe-to-rerun**).
6. **Trigger on events** (task completion, review return, check exit) instead of polling loops (**event-driven**).
7. **Keep configuration explicit** (**no-hidden-config**): concurrency limit (measured, not guessed), model/effort per role if configurable, and execution environment.
8. **Make execution observable:** log every transition with task and reason, and expose one status command showing all tasks.
9. **Test the workflow itself** (**prove-it**): run it on the graph (or a small test graph); kill it mid-run and confirm it resumes; fail a task and verify dependents stay blocked; confirm a review blocker halts downstream tasks. Test transitions directly (**tests-assert-behaviour**).

Only genuine human decisions pause a branch to wait (**decisions-in-plain-words**); everything else runs to completion or reports failure.
