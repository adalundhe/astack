---
name: treeify
description: "Decompose a task or work into a tree of sub-component work tasks down to the smallest testable, verifiable, documentable units, then build, vectored-review, and merge bottom-up in waves (leaves -> subsystems -> root) with escalating testing, review rigor, and documentation. Use for greenfield features, subsystems, UI trees, or IaC stacks built bottom-up."
disable-model-invocation: true
---

# Treeify

Decompose a task or work top-down into a tree of sub-component work tasks, then build, vectored-review, and merge bottom-up in waves—from atomic leaf components to integrated subsystems to the complete root solution.

Use **treeify** when work composes naturally into nested components; use **dagify** for bug fixes, migrations, perf experiments, or irregular task graphs.

## 1. Decompose top-down into a component tree

1. **Align on the goal** (**run-it-back**): state what the root delivers, how it is verified, and what is out of scope. Inspect existing code and environment first (**rtfm**, **how-it-works**, **analyze-environment**).
2. **Recursively split by component** with read-only `astack-researcher` subagents (under **lead**'s timers): start at the root deliverable and split each component into child components until every leaf hits the **stopping criterion**:
   - **Stopping criterion:** the smallest tangible unit of formally verifiable, testable, documentable functionality deliverable rapidly on its own (e.g., a class, method, pure function, single UI control, or single Terraform module with its variables and data).
   - **Don't over-split:** stop when splitting further produces code that cannot stand, be tested, or be documented meaningfully on its own.
3. **Define contracts before building:** every parent node specifies the interfaces, data shapes, and non-overlapping writable paths its children implement (**data-structures-first**, **no-shared-writes**). Place shared types, interfaces, or schemas used by sibling leaves in a **Wave 0 foundation leaf** that lands before parallel sibling leaves start.
4. **Write and review the tree:** save the tree in the program folder as a Mermaid diagram plus one self-contained task spec per node (component contract, children to integrate, writable paths, tests, docs, and done-when). Audit the tree with `astack-reviewer` (**review**) for completeness, tight leaf boundaries, acyclic non-overlapping paths, and reachable contracts before Wave 0 starts.

## 2. Build, review, and merge bottom-up in waves

Each tree layer is one wave of parallel tasks. Execute waves bottom-up through **lead**: workers implement in isolated **slates** volumes (`https://github.com/hyper-light/slates`, preferred when available) or git worktrees; read-only `astack-reviewer` subagents verify worker-submitted changes in **slates** volumes or review worktrees (never writing fixes themselves—sending recommended fixes to workers to implement and resubmit); enforce watch/swap clocks across every worker, reviewer, and researcher (`LANES.md` + `astack-status` every `check_in_minutes`, wind-down reminder, fresh successor on overdue runs).

1. **Dispatch subtree-ready waves in parallel:** start Wave 0 foundation leaves (if any), then leaf components, then each parent component as soon as **all of its own children** clear vectored **review** and land. Leaf workers build atomic components; parent workers compose and wire already-merged children without re-implementing them.
2. **Gate every node before its parent starts:** match the program's merge mode—local target-branch merges verified with `astack-verify-merge` / `astack-check-gates` for local programs, or one PR per node via **watch-pr** when shipping via PRs. Scope every reviewer's brief to that node's component and layer depth (below).
3. **Escalate testing, review, and documentation from leaves to root:**

| Layer | Worker focus | Testing & verification | Vectored review scope | Documentation (**technical-writing**) |
|---|---|---|---|---|
| **Leaves** | Build one atomic component to contract | Isolated unit, edge/failure, property/formal checks (**tests-assert-behaviour**, **formal-validate**) | Isolated behavior, boundary handling, coding rules, contract fit | Concise contract/interface docs (docstrings, schema/variable docs) |
| **Middle layers** | Compose and integrate merged children | Integration tests across child seams, state, concurrency, faults (**full-spectrum-testing**, **blast-radius**) | Cross-child seams, error/state propagation, integration invariants | Subsystem docs cataloging child components, wiring, and config |
| **Root** | Finalize and integrate top-level subsystems | End-to-end verification on the real system (**prove-it**, **full-spectrum-testing**) | Whole-system behavior, acceptance criteria, regressions, doc accuracy | Complete feature/system docs (README, architecture/Mermaid, usage) |

## 3. Re-tree when reality disagrees

If a leaf proves too large, a contract mismatches during composition, or a missing sibling emerges, update the tree and re-review the affected subtree before dispatching—never silently balloon a worker's scope or weaken a gate.

Referenced skills: `dagify` (`../dagify/SKILL.md`), `run-it-back` (`../run-it-back/SKILL.md`), `rtfm` (`../rtfm/SKILL.md`), `how-it-works` (`../how-it-works/SKILL.md`), `analyze-environment` (`../analyze-environment/SKILL.md`), `lead` (`../astack-lead/SKILL.md`), `data-structures-first` (`../data-structures-first/SKILL.md`), `no-shared-writes` (`../no-shared-writes/SKILL.md`), `review` (`../astack-review/SKILL.md`), `slates` (`../slates/SKILL.md`), `watch-pr` (`../watch-pr/SKILL.md`), `technical-writing` (`../technical-writing/SKILL.md`), `tests-assert-behaviour` (`../tests-assert-behaviour/SKILL.md`), `formal-validate` (`../formal-validate/SKILL.md`), `full-spectrum-testing` (`../full-spectrum-testing/SKILL.md`), `blast-radius` (`../blast-radius/SKILL.md`), `prove-it` (`../prove-it/SKILL.md`). Read any cited skill file before acting when its trigger applies.
