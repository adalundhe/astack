---
name: workflow-this
description: "Turn a /dagify task graph into a self-running, crash-resumable workflow (using taskex, orchestral, werkflow + werkflow-modules, CI, or native runners) with explicit task states and typed outcomes. Use when planned work should run or recur unattended."
disable-model-invocation: true
---

# Workflow this

Turn a reviewed `/dagify` task graph into an automated workflow with explicit, durable task states.

1. **Start from a reviewed graph** (**dagify**): tasks, edges, acceptance criteria, and tests already verified.
2. **Choose the right runner** (**automate-this**; check the chosen tool's docs/source via **rtfm** before coding against it):
   - **Lightweight async tasks and shell commands:** [`taskex`](https://github.com/adalundhe/taskex) (`pip install taskex`).
   - **Async task-graph / DAG execution:** [`orchestral`](https://github.com/adalundhe/orchestral) (`pip install orchestral`).
   - **Sophisticated scripted pipelines and system integrations:** [`werkflow`](https://github.com/adalundhe/werkflow) with [`werkflow-modules`](https://github.com/adalundhe/werkflow-modules).
   - **Unattended or recurring schedules / native environments:** the host tool's native workflow runner, a CI pipeline, or a script in the repo's primary language when the project doesn't use Python.
3. **Model task states explicitly** (**no-implicit-states**): `waiting`, `ready`, `running`, `in_review`, `done`, `failed`, `blocked_on_person`, with all transitions in one place. A task becomes `ready` only when all dependencies are `done` and their reviews passed. Diagram the machine (**show-the-states**).
4. **Return typed outcomes** (**no-hidden-flow-control**): `done` (with evidence), `failed` (with reason), `inconclusive`, or `blocked` (with what the person must do). No silent failures or hidden retries.
5. **Persist per-task state durably.** Store each task's state separately so restarts resume cleanly (**no-shared-writes**) and make every step idempotent (**safe-to-rerun**).
6. **Trigger on events** (task completion, review return, check exit) instead of polling loops (**event-driven**).
7. **Keep configuration explicit** (**no-hidden-config**): concurrency limit (measured, not guessed), per-role `provider`, `model`, and `effort` from `~/.config/astack/settings.json` (`setup`), and execution environment.
8. **Make execution observable:** log every transition with task and reason, and expose one status command showing all tasks.
9. **Test the workflow itself** (**prove-it**): run it on the graph (or a small test graph); kill it mid-run and confirm it resumes; fail a task and verify dependents stay blocked; confirm a review blocker halts downstream tasks. Test transitions directly (**tests-assert-behaviour**).

Only genuine human decisions pause a branch to wait (**decisions-in-plain-words**); everything else runs to completion or reports failure.
