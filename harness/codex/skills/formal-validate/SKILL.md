---
name: formal-validate
description: "Set up and maintain formal checks (TLA+, verifiers, property tests) and replay counterexamples on real code. Use when tests miss dangerous orderings or after verified code changes."
---

# Formal validate

Formally verify high-stakes invariants where normal tests fall short. Keep verification in sync as the code evolves.

Check whether the project already has a `verify-<area>` skill for this area. Create one if missing; otherwise keep it in sync.

## Create

1. **Pick a high-value target:** start where the person pointed. Target a safety or correctness guarantee whose failure hurts users in rare cases. Pick the strongest invariant, not the easiest.
2. **Match the tool to the question** (**research-this** standard options first):
   - **Bad interleavings or ordering:** model checker on a tight design model (e.g. TLA+).
   - **Per-input invariants (memory safety, overflow, data structures):** a verifier running directly on the code.
   - **No verifier for the language:** property-based inputs against real code instead of a disconnected model.
   - **Must hold at arbitrary scale:** a formal proof.

   Prefer tools developers can install and run locally. State why you picked the tool.
3. **Hold the verification to these standards:**
   - **Faithful to the code:** map every element to real code a reviewer can inspect. Match atomic steps and repo names.
   - **Proven able to fail:** break a check or reorder a step and confirm the property fails, because vacuous checks always pass.
   - **Never weaken properties to pass:** report counterexamples as real findings, because relaxed properties hide real bugs. Fix product bugs separately from a failing test.
   - **Explicit scope:** document what is verified, exact bounds and assumptions, and exclusions.
   - **Readable without the tool:** state each property and user impact in one plain sentence. Translate counterexamples into plain code-level steps.
   - **Cheap to rerun:** use one command with a pinned tool version that runs fast on relevant changes.
4. **Visualize failures and state spaces** when review needs it (**show-the-states**). For TLA+, run `astack-statechart check <model.tla> --view <view.py>` (installs pinned TLC automatically when Java is present, or run `astack-statechart install-tlc`) or `astack-statechart render <states.dot> --trace <tlc.out> --view <view.py>`. Never hand-rename a raw TLC graph—compute the reader's chart via a small view module (review `.py` views before running them). Model intentional termination with a self-looping end action (`Done == pc = "done" /\ UNCHANGED vars`) instead of blindly disabling deadlock checking with `--no-deadlock`.
5. **Replay every counterexample on real code** as a test or live repro, step for step. If a step cannot happen in real code, treat the model as wrong, because an unfaithful model produces false alarms.
6. **Write a project skill (`verify-<area>`)** in the repo's skills folder, not `~/.astack`. Cover how to spot touched code, run the check, separate real bugs from drift, and update for intentional changes. Record covered files and the last confirmed commit SHA.
7. **Prove the skill works:** if the current code passes, follow the skill cold against a scratch mutation breaking the invariant in real code, confirm it catches the break, revert, and confirm green again. If the current code already fails with a verified counterexample, replay it on real code and report it as a real bug without weakening the property.

**Done when:** the check catches a real mutation and either passes a cold run on clean code or replays and reports a real product-bug counterexample without weakening properties, with `verify-<area>` saved in the repo.

## Keep it true

Use when verified code changed without updating verification. Edit only verification artifacts (models, harnesses, properties, verify skill)—never product code. Every check ends as **in sync**, **updated**, **bug**, or **blocked**. A check can be both **updated** and **bug**.

1. **Gather check metadata:** collect property, covered code, bounds, assumptions, command, and last confirmed commit. If unrecorded, fall back to the last commit touching verification and note it.
2. **Run as-is first.** Passing only proves the old model held—not that current code is right.
3. **Inspect every commit touching covered code** since the confirmed commit, including renames, splits, and new callers. Classify each change:
   - no effect on modeled behavior (judged from code, not commit messages);
   - model no longer matches code (drift);
   - invariant changed intentionally (cite docs, tests, changelog, or commit);
   - invariant may be broken.
4. **Update the verification from the code before rerunning.** Change a property only for an intentional spec change, citing old wording, new wording, and source. Preserve bounds, or report any reduction explicitly.
5. **Rerun and validate:**
   - **If it passes:** inject a temporary bug violating the property, confirm the check catches it, and revert.
   - **If it fails:** replay the counterexample on real code step by step. Fix impossible steps as model errors and explain the gap. Report valid traces as real bugs with steps, user harm, and introducing commit.
6. **Update the `verify-<area>` skill** with new coverage, commands, bounds, assumptions, and confirmed commit. Leave the commit unmoved if blocked, then run through the skill once cold.
7. **Report clearly:** list outcome per check, commits reviewed, updates made, mutation check results, bugs in plain words, and gaps. Separate model drift from real bugs, and ship verification updates separately from product fixes.

Referenced skills: `research-this` (`../research-this/SKILL.md`), `show-the-states` (`../show-the-states/SKILL.md`). Read any cited skill file before acting when its trigger applies.

<!-- Adapts pstack's create-formal-verification-skill and maintain-formal-verification-skill skills (MIT, Copyright (c) 2026 Lauren Tan). See NOTICE.md. -->
