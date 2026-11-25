---
name: treeify
description: "Decompose work top-down into a tree of sub-component tasks down to the smallest testable, verifiable, documentable units, then build, vectored-review, and merge bottom-up in waves (leaves -> subsystems -> root). Use for greenfield features, subsystems, UI trees, or IaC stacks."
disable-model-invocation: true
---

# Treeify

Decompose work top-down into nested components, then build, vectored-review, and merge bottom-up in waves—from atomic leaves to subsystems to root. Use **dagify** for bug fixes, migrations, perf experiments, or irregular graphs.

## 1. Decompose top-down into a component tree

1. **Align on the goal (**run-it-back**):** state what the root delivers, how it is verified, and what is out of scope. Inspect existing code and tooling first (**rtfm**, **how-it-works**, **analyze-environment**).
2. **Split recursively by component** using read-only `astack-researcher` subagents until each leaf hits the **Stopping criterion:**
   - **Stopping criterion:** the smallest tangible unit of verifiable, testable, documentable functionality deliverable rapidly on its own (a class, pure function, UI control, or single IaC module).
   - **Don't over-split:** stop when splitting further produces code that cannot stand, be tested, or be documented on its own.
3. **Define contracts before building:** every parent specifies interfaces, data shapes, and disjoint writable paths for its children (**data-structures-first**, **no-shared-writes**). Put shared types or schemas in a **Wave 0 foundation leaf** that lands before parallel siblings start.
4. **Write and review the tree:** save a Mermaid diagram plus one self-contained task spec per node in the program folder. Audit the tree with `astack-reviewer` (**review**) for completeness, tight leaf boundaries, acyclic disjoint paths, and reachable contracts before Wave 0 starts.

## 2. Build, review, and merge bottom-up in waves

Each tree layer is one wave of parallel tasks. Execute waves through **lead** (isolated **slates** volumes or git worktrees, strict read-only reviewers never writing fixes themselves, watch-and-swap clocks, and cross-harness delegation via `astack-dispatch`).

1. **Dispatch subtree-ready waves in parallel:** run Wave 0 foundation leaves first, then leaves, then each parent once **all of its own children** clear vectored **review** and land. Parents wire merged children without re-implementing them.
2. **Gate every node before its parent starts:** verify local merges via `astack-verify-merge` and `astack-check-gates`, or shepherd per-node PRs via **watch-pr**.
3. **Escalate testing, review, and docs from leaves to root:**

| Layer | Worker focus | Testing & verification | Vectored review scope | Documentation (**technical-writing**) |
|---|---|---|---|---|
| **Leaves** | Build one atomic component to contract | Isolated unit, edge/failure, property/formal checks (**tests-assert-behaviour**, **formal-validate**) | Isolated behavior, boundaries, coding rules, contract fit | Concise interface/schema docs |
| **Middle layers** | Compose and wire merged children | Integration tests across seams, state, concurrency, faults (**full-spectrum-testing**, **blast-radius**) | Cross-child seams, error/state propagation, invariants | Subsystem wiring and config docs |
| **Root** | Finalize top-level subsystems | End-to-end proof on real system (**prove-it**, **full-spectrum-testing**) | Whole-system behavior, acceptance criteria, doc accuracy | Full README, Mermaid architecture, usage |

## 3. Re-tree when reality disagrees

If a leaf proves too large, a contract mismatches during composition, or a missing sibling emerges, update the tree and re-review the affected subtree before dispatching. Never silently balloon worker scope or weaken a gate.

## 4. Squish and close with **lookback**

Once the root clears review, run **squish** to rebase, squash, or combine fragmented commits or per-node PRs when justified. Then (or on unrecoverable failure) run **lookback** into `~/.astack/<project_name>/lessons/<lesson_name>/LESSON.md`, paired with **make-it-stick** for recurring structural guards.

Referenced skills: `dagify` (`../dagify/SKILL.md`), `run-it-back` (`../run-it-back/SKILL.md`), `rtfm` (`../rtfm/SKILL.md`), `how-it-works` (`../how-it-works/SKILL.md`), `analyze-environment` (`../analyze-environment/SKILL.md`), `data-structures-first` (`../data-structures-first/SKILL.md`), `no-shared-writes` (`../no-shared-writes/SKILL.md`), `review` (`../astack-review/SKILL.md`), `lead` (`../astack-lead/SKILL.md`), `slates` (`../slates/SKILL.md`), `watch-pr` (`../watch-pr/SKILL.md`), `technical-writing` (`../technical-writing/SKILL.md`), `tests-assert-behaviour` (`../tests-assert-behaviour/SKILL.md`), `formal-validate` (`../formal-validate/SKILL.md`), `full-spectrum-testing` (`../full-spectrum-testing/SKILL.md`), `blast-radius` (`../blast-radius/SKILL.md`), `prove-it` (`../prove-it/SKILL.md`), `lookback` (`../lookback/SKILL.md`), `squish` (`../squish/SKILL.md`), `make-it-stick` (`../make-it-stick/SKILL.md`). Read any cited skill file before acting when its trigger applies.
