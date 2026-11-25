---
name: dagify
description: "Turn multi-task specs into a reviewed DAG of parallelizable vertical slices with non-overlapping paths. Use for work spanning 3+ files or multiple independent units."
disable-model-invocation: true
---

# Dagify

Break multi-task work into small units that one agent each can build and verify, ordered so independent work runs in parallel. For greenfield subsystems, UI trees, or IaC stacks built bottom-up by component waves, use **treeify** instead.

**Skip if small:** if the change touches 1–2 files with an obvious approach, skip the DAG. Say so and build it directly, because planning overhead slows down trivial work.

## 0. Clear open spec decisions

Before slicing a spec or PRD, identify unresolved product, interface, or architecture branches. Resolve genuine human choices one focused exchange at a time with your recommendation, or record unambiguous defaults as `decided:` in `LANES.md`. Never slice around an open branch, because one upstream change invalidates every downstream task.

## 1. Align and pick a workflow shape

1. **Check prior lessons and align:** run **lookup** on `~/.astack` first to catch past traps. State what users will see when done and what is out of scope (`run-it-back`). Read affected code (`how-it-works`), and diagram states when behavior depends on history (`show-the-states`).
2. **Pick a shape.** Every shape ends in a review that passes before dependent tasks start:
   - **Bug:** shrunk failing repro (`bugbash`) -> root-cause diagnosis (`find-it`) -> fix (`fix-it`) -> review.
   - **Feature:** data shape and acceptance criteria -> thin vertical "tracer bullet" slices (end-to-end across layers to prove integration early, not horizontal stubs) -> end-to-end tests -> review.
   - **Performance:** harness and baseline -> candidate variants -> A/B measurement -> review of winner (`benchmarking`, `ab-test`).
   - **Refactor:** pinning behavior tests -> refactor -> review.
   - **Migration / Cutover:** expand (additive schema/auth/infra keeping old workloads + rollback working) -> switch callers & prove zero legacy traffic -> contract in a later release (**safe-to-deploy**).

   Adapt as needed, keeping the first step and final review. For custom graphs, tackle the riskiest unknown first and make each task a verifiable experiment.

## 2. Scope tasks and fill required fields

Scope each task tightly: one deliverable, one done-when, provable by one agent, small enough for a reviewer to hold in mind. Prefer thin vertical slices that cross the real stack end-to-end so integration breaks early. Split multi-deliverable tasks; merge tasks that cannot be verified alone.

Fill every task's fields:

- **Description:** 2–3 sentences max.
- **Implementation guide:** brief notes, references, and sample inputs/outputs.
- **Acceptance criteria:** user-observable behavior. Add numeric targets only when set by the person or measured via `benchmarking` / `ab-test`.
- **Tests:** scoped behavior tests covering failures, edge cases, races, fuzzing, and faults where applicable (`tests-assert-behaviour`, `full-spectrum-testing`).
- **Touches:** writable files, data, interfaces, states introduced, and impacted repo docs (`technical-writing`). Add a downstream doc-sync task when parallel tasks share docs.

## 3. Add edges, parallelize, and write the graph

1. **Draw edges sparingly,** because every extra edge serializes parallel work. Add an edge only when task B needs task A's output or both write the same file or interface (`no-shared-writes`). Order failing test before fix, deletion before reshape, and baseline before optimization.
2. **Parallelize independent tasks** up to machine capacity (`no-picked-constants`). Follow **lead** for isolated workspaces (**slates** or git worktrees), read-only reviewer separation, watch-and-swap clocks, and cross-harness delegation (`astack-dispatch`).
3. **Write the graph** in the program folder (or requested path): every task with its fields, explicit edges, and a Mermaid diagram. Each task must work directly as a worker brief.

## 4. Review the plan before starting

Dispatch fresh `astack:reviewer` subagents from `reviewer_pool` (using a non-author model when available). Use 1 reviewer for a low-risk plan, or ≥2 blind models for risky triggers (shared interfaces, concurrency, persistence, auth/security, or a large graph). Stop via `astack-review-ledger` (**review**).

Check five bars:

- **Coherent:** tasks cover the goal with no gaps or overlap, and edges match real dependencies.
- **In scope:** one deliverable each, nothing unrequested added, nothing requested omitted.
- **Self-contained:** one agent can execute from the task alone with no hidden context.
- **Reachable:** one agent can prove done-when in available environments without downstream tasks.
- **Accurate:** acceptance criteria match user requirements, backed by tests that catch real failures.

Fix review findings and re-check until clear (**address-feedback**). Re-plan if failures share an external cause or a task needs splitting—never silently expand scope.

## 5. Guard contracts, squish, and close

- **Guard the contract:** acceptance criteria and tests are the whole bar—neither add unasked gates nor game existing ones. Check lanes with `astack-check-gates <base>..<head>` alongside **review**. Revert gamed gates, tighten the brief, and dispatch a fresh worker. Fix genuinely broken gates in their own dedicated task.
- **Close cleanly:** once the DAG finishes, run **squish** to consolidate fragmented commits or PRs when justified. Then (or on unrecoverable failure) run **lookback** into `~/.astack/<project_name>/lessons/<lesson_name>/LESSON.md`, paired with **make-it-stick** for recurring structural guards.

**Done when:** all tasks pass **review** and gate checks, justified commits/PRs are squished, and **lookback** captured the lesson.

Referenced skills: `treeify` (`${CLAUDE_SKILL_DIR}/../treeify/SKILL.md`), `lookup` (`${CLAUDE_SKILL_DIR}/../lookup/SKILL.md`), `safe-to-deploy` (`${CLAUDE_SKILL_DIR}/../safe-to-deploy/SKILL.md`), `lead` (`${CLAUDE_SKILL_DIR}/../lead/SKILL.md`), `slates` (`${CLAUDE_SKILL_DIR}/../slates/SKILL.md`), `review` (`${CLAUDE_SKILL_DIR}/../review/SKILL.md`), `address-feedback` (`${CLAUDE_SKILL_DIR}/../address-feedback/SKILL.md`), `squish` (`${CLAUDE_SKILL_DIR}/../squish/SKILL.md`), `lookback` (`${CLAUDE_SKILL_DIR}/../lookback/SKILL.md`), `make-it-stick` (`${CLAUDE_SKILL_DIR}/../make-it-stick/SKILL.md`). Read any cited skill file before acting when its trigger applies.

<!-- Adapts pstack's figure-it-out skill and its sequence-verifiable-units principle (MIT, Copyright (c) 2026 Lauren Tan). See NOTICE.md. -->
