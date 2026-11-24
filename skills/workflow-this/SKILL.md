---
name: workflow-this
description: "Turn a /dagify task graph into a workflow that runs itself: a script or automation where every task's state is explicit, transitions live in one place, and a crash or restart resumes where it stopped. Use when planned work should run, rerun or recur without an agent steering each step."
---

# Workflow this

Turn a task graph into a workflow that runs itself, with every state it can be in written down.

1. **Start from the graph** (**dagify**): its tasks, edges, criteria and tests, already reviewed.
2. **Pick the runner:** the tool's own workflow runner if it has one; a CI pipeline or a scheduled automation if it should run unattended or recur; otherwise a script in the project's language. Prefer what the project already runs (**automate-this**).
3. **Give each task an explicit state machine** (**no-implicit-states**): waiting, ready, running, in review, done, failed, blocked on the person. Transitions live in one place. A task becomes ready only when everything it depends on is done, and its dependents start only after its review passes. Draw it (**show-the-states**).
4. **Make every outcome a typed value** (**no-hidden-flow-control**): done, with its evidence; failed, with the reason; inconclusive; or blocked, with what the person must do. Nothing fails silently or retries out of sight.
5. **Keep state durable and separate.** Each task records its own state where a restart can read it (**no-shared-writes**), and every step is safe to run again, so a crash or restart resumes where it stopped (**safe-to-rerun**).
6. **Wake on events,** such as a task finishing, a review returning or a check completing, rather than polling (**event-driven**).
7. **Make its settings explicit** (**no-hidden-config**): how many tasks run at once (measured, not picked), which model and effort each role uses (from setup), and where it runs.
8. **Make it observable:** every transition logged with its task and reason, and one command that shows every task's state.
9. **Prove it** (**prove-it**): run it on the graph, or a small copy of it; kill it midway and confirm it resumes; make a task fail and confirm its dependents never start; confirm a review blocker stops its branch. Test the transitions themselves (**tests-assert-behaviour**).

Only the person's decisions stop it and wait for them (**decisions-in-plain-words**). Everything else, it settles or reports.
