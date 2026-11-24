---
name: dagify
description: "Break a request into a graph of small tasks, each with a description, an implementation guide, user-observable acceptance criteria and its tests, ordered so the most can run at once without two touching the same thing. Use before building anything larger than one task, and when planning or re-planning a program."
---

# Dagify

Turn a request into tasks that one agent each can finish and prove, ordered so as many as possible run at once.

1. **Start from the goal** (**play-it-back**): what users will see when it's done, and what's left out. Read the code it touches first (**how-it-works**), and draw its states when behaviour depends on what happened before (**show-the-states**).
2. **Pick the shape that fits.** Each ends in a review that must pass before anything depending on it starts.
   - **Bug:** a failing test that reproduces it, the fix, review.
   - **Feature:** the data shape and acceptance criteria, slices that each work end to end, the end-to-end tests, review.
   - **Performance:** the harness and baseline, the variants, the A/B, review of the winner (**benchmarking**, **ab-test**).
   - **Refactor:** tests that pin today's behaviour, the change, review.

   Adapt a shape, but keep its first task and its final review. When none fits, build one: the riskiest unknown first, the harness and baseline before the work, each task an experiment whose result is verified, not verified, or inconclusive.
3. **Cut tasks to size:** one deliverable, one done-when, finished and proven by one agent, small enough for a reviewer to hold in their head. Split a task with two deliverables; merge tasks that can't be checked apart.
4. **Write each task:**
   - **Description:** two or three sentences at most.
   - **Implementation guide:** brief notes, research references, examples, sample inputs and outputs.
   - **Acceptance criteria:** behaviour users can observe. A number only if the person set it, or **benchmarking** or **ab-test** measured it.
   - **Tests:** scoped to the task; behaviour, not implementation; isolated; failure paths, edge cases, races, deadlock and livelock, fuzzing and injected faults where they apply; diamond-shaped (**tests-assert-behaviour**, **full-spectrum-testing**).
   - **Touches:** the files, data and interfaces it reads and writes, and the states it builds.
5. **Draw the edges.** A task depends on another when it needs that one's output, or when both would write the same file, data or interface (**no-shared-writes**). Nothing else is an edge. Within a shape, the failing test comes before the fix, the deletion before the reshape, the baseline before the change.
6. **Run what has no path between it at once,** as far as the machine's measured room allows (**no-picked-constants**).
7. **Write the graph** where it was asked for (in Go mode, the program's folder): every task with its fields, the edges, and a Mermaid chart of the graph. Each task should be ready to brief as written.
8. **Have the tasks reviewed before any starts,** by a reviewer who didn't write them. Each task must be:
   - **coherent:** together, the tasks deliver the goal, with no gaps and no overlaps, and the edges match what each task needs and touches;
   - **in scope:** one deliverable, nothing the request didn't ask for, and nothing it asked for left out;
   - **clear:** an agent could start from the task alone, with nothing in it the agent can't see;
   - **reachable:** its done-when is evidence one agent can produce within the task, in the environments it can use, without waiting on a later task;
   - **accurate:** every acceptance criterion is something the request needs and users can observe, and every criterion has tests that fail when it breaks, chosen for the failures that can actually happen here.

   Fix what the review finds, and repeat until it comes back clear (**address-feedback**).

Re-plan when a task's failures share a cause the task itself can't fix, when it needs splitting, or when it uncovers work the graph doesn't hold. Never grow a task instead.

<!-- Adapts pstack's figure-it-out skill and its sequence-verifiable-units principle (MIT, Copyright (c) 2026 Lauren Tan). See NOTICE.md. -->
