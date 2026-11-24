---
name: every-case
description: "Set up and maintain formal verification (TLA+, code verifiers, or generated checks) for concurrency, state machines, protocols, parsers, or unsafe code, and replay counterexamples on real code. Use when tests can't cover dangerous orderings or inputs, or after verified code changes."
disable-model-invocation: true
---

# Every case

Formally verify high-stakes invariants where normal tests fall short, and keep the verification in sync as the code evolves.

Check whether the project already has a `verify-<area>` skill for this area. If not, create one; if it does, keep it in sync.

## Create

1. **Pick a high-value target** starting where the person pointed: a safety or correctness guarantee whose failure hurts users in cases tests rarely hit. Pick the strongest invariant, not the easiest one.
2. **Match the tool to the question** (**research-this** standard options first):
   - **Bad interleavings or ordering:** model checker on a tight model of the design (e.g. TLA+).
   - **Per-input invariants (memory safety, overflow, data-structure invariants):** a verifier that runs directly on the code.
   - **No verifier for the language:** generated/property-based inputs against the real code rather than a disconnected hand-written model.
   - **Must hold at arbitrary scale:** a formal proof.

   Prefer tools the project's developers can install and run locally, and state why you picked it.
3. **Hold the verification to these standards:**
   - **Faithful to the code:** every element maps to real code a reviewer can inspect; atomic steps match; names match the repo.
   - **Proven able to fail:** demonstrate each property failing against a deliberately broken variant (removed check, reordered step).
   - **Never weaken properties to pass:** report counterexamples as real findings; fixes go in a separate change starting from a failing test.
   - **Explicit scope:** document what is verified, exact bounds/assumptions, and what's excluded.
   - **Readable without the tool:** state each property and its user impact in one plain sentence, and translate counterexamples into plain code-level steps.
   - **Cheap to rerun:** one command, pinned tool version, fast enough to run on relevant changes.
4. **Visualize failures and state spaces** when review needs it (**show-the-states**): for TLA+ models, run `astack-statechart check <model.tla>` (or `astack-statechart render <states.dot> --trace <tlc.out>`) to report the shortest path to each broken invariant and generate a Mermaid `stateDiagram-v2` directly from TLC output.
5. **Replay every counterexample on real code** as a test or live repro, step for step. If a step can't happen in real code, the model is wrong until proven otherwise.
6. **Write a project skill (`verify-<area>`)** in the project's skills folder so the next agent can tell whether a diff touches verified code, run the check, distinguish real bugs from modeling drift, and update the check for intentional changes. Record covered files and the last confirmed commit SHA.
7. **Prove the skill works:** follow it cold against a scratch mutation that breaks the invariant in real code, confirm it catches the break, then revert the mutation and confirm green again.

## Keep it true

Use when verified code changed without updating verification. Edit only verification artifacts (models, harnesses, properties, verify skill)—never product code. Every check ends as **in sync**, **updated**, **bug** (verification matches code, code violates property), or **blocked** (a check can be both **updated** and **bug**).

1. **Gather check metadata:** property, covered code, bounds, assumptions, command, and last confirmed commit (fall back to the last commit touching the verification if unrecorded, and note it).
2. **Run as-is first.** Passing only proves the old model held—not that the current code is right.
3. **Inspect every commit touching covered code** since the confirmed commit (including renames, moves, splits, and new callers touching guarded state). Classify each change:
   - no effect on modeled behavior (judged from code, not commit messages);
   - model no longer matches code (drift);
   - invariant changed intentionally (cite docs, tests, changelog, or commit);
   - invariant may be broken.
4. **Update the verification from the code before rerunning.** Only change a property for an intentional spec change (recording old wording, new wording, and citation). Preserve bounds, or explicitly report any reduction.
5. **Rerun and validate:**
   - **If it passes:** inject a temporary bug violating the property, confirm the check catches it, then revert the mutation.
   - **If it fails:** replay the counterexample on real code step by step. An impossible step means model error—fix it and explain the discrepancy. A valid trace is a real bug—report steps, one-sentence user harm, and the introducing commit.
6. **Update the `verify-<area>` skill** (coverage, commands, bounds, assumptions, and confirmed commit—leaving the commit unmoved if blocked), then run through it once as the next agent would.
7. **Report clearly:** outcome per check, commits reviewed, updates made, mutation check confirming it still fails on breaks, any bugs in plain language, and remaining gaps. Distinguish model drift from real bugs, and ship verification updates separately from product fixes.

Referenced skills: `research-this` (`${CLAUDE_SKILL_DIR}/../research-this/SKILL.md`), `show-the-states` (`${CLAUDE_SKILL_DIR}/../show-the-states/SKILL.md`). Read any cited skill file before acting when its trigger applies.

<!-- Adapts pstack's create-formal-verification-skill and maintain-formal-verification-skill skills (MIT, Copyright (c) 2026 Lauren Tan). See NOTICE.md. -->
