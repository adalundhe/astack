---
name: dagify
description: "Break a large request into a dependency graph of small, parallelizable tasks with acceptance criteria and tests, avoiding overlapping file edits. Use before building multi-task work or re-planning a program."
disable-model-invocation: true
---

# Dagify

Break a request into tasks that one agent each can complete and verify, ordered so independent work runs in parallel.

1. **Align on the goal** (**run-it-back**): state what users will see when done and what's out of scope. Read the affected code first (**how-it-works**), and diagram states when behavior depends on history (**show-the-states**).
2. **Pick a workflow shape.** Every shape ends in a review that must pass before dependent tasks start.
   - **Bug:** reproducing failing test -> root-cause diagnosis (**find-it**) -> fix (**fix-it**) -> review.
   - **Feature:** data shape and acceptance criteria -> end-to-end vertical slices -> end-to-end tests -> review.
   - **Performance:** harness and baseline -> candidate variants -> A/B measurement -> review of winner (**benchmarking**, **ab-test**).
   - **Refactor:** tests pinning current behavior -> refactor -> review.

   Adapt as needed, but keep the first task and final review. If no shape fits, build a custom graph: tackle the riskiest unknown first, establish harnesses/baselines before changes, and make each task a verifiable experiment (`verified`, `not verified`, or `inconclusive`).
3. **Scope each task tightly:** one deliverable, one done-when, doable and provable by a single agent, small enough for a reviewer to hold in their head. Split multi-deliverable tasks; merge tasks that can't be verified independently.
4. **Fill in every task's fields:**
   - **Description:** at most 2–3 sentences.
   - **Implementation guide:** brief notes, references, examples, and sample inputs/outputs.
   - **Acceptance criteria:** user-observable behavior. Include numeric targets only when set by the person or measured via **benchmarking** / **ab-test**.
   - **Tests:** scoped to the task, checking behavior over implementation, isolated, diamond-shaped, covering failure paths, edge cases, races/deadlocks/livelocks, fuzzing, and injected faults where applicable (**tests-assert-behaviour**, **full-spectrum-testing**).
   - **Touches:** files, data, and interfaces read or written, plus states introduced.
5. **Add dependency edges.** Draw an edge only when task B needs task A's output, or when both write the same file, data, or interface (**no-shared-writes**). Order prerequisites cleanly: failing test before fix, deletion before reshape, baseline before optimization.
6. **Parallelize independent tasks** up to what the machine can handle (**no-picked-constants**). **Isolation & watch/swap:** workers implement all changes and fixes in **slates** in-memory VFS volumes (`https://github.com/hyper-light/slates`, preferred when available) or git worktrees; reviewers run reproductions and verify worker-submitted changes read-only in **slates** volumes or review worktrees—never writing fixes themselves, instead sending recommended fixes and results back to workers to implement and resubmit. Enforce **lead**'s watch/swap clocks across all workers and reviewers (`LANES.md` + `astack-status` every `check_in_minutes`, wind-down reminder, fresh successor with reset timers on overdue runs).
7. **Write the graph** where requested (or in the program folder, in an astack program): every task with its fields, explicit edges, and a Mermaid diagram. Each task should be directly usable as a worker brief.
8. **Review the plan before starting,** dispatching fresh `astack:reviewer` subagent(s) from `reviewer_pool` (using a model other than the plan author's when the pool allows): start with one reviewer for a small, low-risk plan, or at least two blind reviewers on different approved models when the plan touches high-risk triggers (shared interfaces, concurrency, persistence, auth/security, or a large graph), stopping via `astack-review-ledger` (**review**). Check that tasks are:
   - **Coherent:** together they satisfy the goal with no gaps or overlap, and edges match actual data/file dependencies.
   - **In scope:** one deliverable each, nothing unrequested added, nothing requested omitted.
   - **Self-contained:** an agent can execute from the task alone without hidden context.
   - **Reachable:** the done-when can be proven by one agent inside available environments without waiting on downstream tasks.
   - **Accurate:** acceptance criteria reflect real user-visible requirements, backed by tests that catch realistic failures.

   Fix review findings and re-check until clear (**address-feedback**).

Re-plan if failures share an external root cause, a task needs splitting, or unexpected prerequisite work emerges. Never silently expand a task's scope instead.

**Guard the task contract:** the acceptance criteria and tests in a task are the whole bar—workers must neither invent extra unasked gates nor game existing ones. Check full lane ranges with `astack-check-gates <base>..<head>` (or `astack-verify-merge <sha> --base <base> --strict-gates`) alongside **review**; if a worker games a gate, reset the contract (revert the gamed change, tighten the brief/tests, and dispatch a fresh worker). If a gate itself is genuinely wrong or broken, fix the gate in its own dedicated task/change rather than weakening it inside feature work.

<!-- Adapts pstack's figure-it-out skill and its sequence-verifiable-units principle (MIT, Copyright (c) 2026 Lauren Tan). See NOTICE.md. -->
