---
name: treeify
description: "Decompose work top-down into atomic component leaves, then build, review, and merge bottom-up in waves. Use for greenfield subsystems, UI trees, or IaC."
disable-model-invocation: true
---

# Treeify

Decompose work top-down into nested components. Build, review, and merge bottom-up in waves—from leaves to subsystems to root. Use **dagify** for bugs, migrations, perf work, or irregular graphs.

**Skip if small.** If the change fits 1–2 files with a clear design, build it directly. Tree overhead slows trivial work.

## 1. Decompose top-down into a component tree

1. **Align on the goal.** Restate what the root delivers, how it is verified, and what is out of scope. Read existing code and tooling first.
2. **Split recursively by component.** Use read-only `astack-researcher` subagents until each leaf meets the **Stopping criterion:**
   - **Stopping criterion:** the smallest verifiable, testable, documentable unit deliverable fast on its own (a class, pure function, UI control, or single IaC module).
   - **Don't over-split.** Stop when another split creates code that cannot stand, test, or document alone.
3. **Define contracts before building.** Every parent sets interfaces, data shapes, and disjoint writable paths (**data-structures-first**). Put shared types or schemas in a **Wave 0 foundation leaf** that lands first, because siblings drift without a frozen contract.
4. **Write and review the tree.** Save a Mermaid diagram and one self-contained task spec per node in the program folder. Audit the tree with `astack-reviewer` (**review**) for completeness, tight leaves, disjoint paths, and reachable contracts before Wave 0 starts.

## 2. Build, review, and merge bottom-up in waves

Each tree layer is one wave of parallel tasks. Run waves via **lead** using **slates** volumes (or git worktrees) and watch-and-swap clocks. Reviewers stay read-only, never writing fixes themselves.

1. **Dispatch subtree-ready waves in parallel.** Run Wave 0 foundation leaves first, then leaves. Start each parent once all of its children clear vectored **review** and land. Parents wire merged children without re-implementing them.
2. **Gate every node before its parent starts.** Verify local merges with `astack-verify-merge` and `astack-check-gates`, or shepherd per-node PRs via `watch-pr`.
3. **Escalate testing, review, and docs from leaves to root:**

| Layer | Worker focus | Testing & verification | Vectored review scope | Documentation (**technical-writing**) |
|---|---|---|---|---|
| **Leaves** | Build one atomic component to contract | Isolated unit, edge/failure, property/formal checks (`tests-assert-behaviour`, `formal-validate`) | Isolated behavior, boundaries, coding rules, contract fit | Concise interface/schema docs |
| **Middle layers** | Compose and wire merged children | Integration tests across seams, state, concurrency, faults (`full-spectrum-testing`, `blast-radius`) | Cross-child seams, error/state propagation, invariants | Subsystem wiring and config docs |
| **Root** | Finalize top-level subsystems | End-to-end proof on real system (`prove-it`, `full-spectrum-testing`) | Whole-system behavior, acceptance criteria, doc accuracy | Full README, Mermaid architecture, usage |

## 3. Re-tree when reality disagrees

If a leaf proves too large, a contract mismatches, or a sibling is missing, update the tree first. Re-review the affected subtree before dispatching. Never silently widen worker scope or weaken a gate.

## 4. Squish and close

Once the root clears review, run **squish** to consolidate noisy commits or per-node PRs when justified. Then (or on unrecoverable failure) run **lookback** into `~/.astack/<project_name>/lessons/<lesson_name>/LESSON.md`. Pair recurring guards with **make-it-stick**.

**Done when:** the root clears vectored **review** and end-to-end tests, history is squished if needed, docs match, and **lookback** is logged.

Referenced skills: `dagify` (`../dagify/SKILL.md`), `data-structures-first` (`../data-structures-first/SKILL.md`), `review` (`../astack-review/SKILL.md`), `lead` (`../astack-lead/SKILL.md`), `slates` (`../slates/SKILL.md`), `technical-writing` (`../technical-writing/SKILL.md`), `squish` (`../squish/SKILL.md`), `lookback` (`../lookback/SKILL.md`), `make-it-stick` (`../make-it-stick/SKILL.md`). Read any cited skill file before acting when its trigger applies.
