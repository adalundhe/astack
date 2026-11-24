---
name: every-case
description: "Formally verify a promise where bugs cost most and tests reach least (concurrency, retries, state machines, protocols, parsers, unsafe code), and keep the verification true as the code changes. Use when tests can't reach the ordering, input or size that breaks a promise, or after verified code changes."
---

# Every case

Formally verify that code keeps a promise in every case, and keep the verification in step with the code.

Find the project's verify skills: project skills that run a model checker, prover or verifier on named code. None for this area: create one. One: keep it true.

## Create

1. **Pick the target from the code,** starting where the person pointed: a promise whose break harms users, in cases tests rarely reach. The strongest target, not the easiest.
2. **Let the question pick the tool** (**research** what others use):
   - Can steps happen in a bad order? A model checker on a small model of the design; TLA+ is a common choice in any language.
   - Does the code hold for every input (memory safety, overflow, a data structure's invariant)? A verifier that runs on the code.
   - No verifier for this language? Generated inputs against the real code, rather than a hand-written model, which would prove the model instead of the code.
   - Must it hold at every size? A proof.

   Prefer what the project's developers can install and run, and say why you chose it.
3. **Hold it to these:**
   - **True to the code:** every part maps to code a reviewer can open; one atomic step in the code is one step in the model; names come from the repo.
   - **Able to fail:** each property is shown failing on a broken variant, such as a removed check or a reordered step.
   - **Findings stay findings:** report the counterexample; never weaken the property or the model to pass. The fix is its own change, starting from a failing test.
   - **Honest about scope:** what's verified, under which bounds and assumptions, and what's left out.
   - **Readable without the tool:** each property, and the harm of breaking it, in one plain sentence; each counterexample as a short list of steps in the code's words.
   - **Cheap to rerun:** one command, a pinned tool version, fast enough for every relevant change.
4. **Show the behaviour** when someone must judge it (**show-the-states**), from the checker's state graph (TLC writes one as DOT), with each bug as the shortest path to it.
5. **Replay each counterexample on the real code,** as a test or live reproduction, one step per model step. If it doesn't reproduce, the model is wrong until shown otherwise.
6. **Write the verify skill,** `verify-<area>`, in your tool's project skills folder. From it alone, the next agent can tell whether a change touches verified code, run the check, tell a real bug from a modelling error, and update the verification for an intended change. Record the code each check covers and the commit it was last confirmed against.
7. **Prove it:** follow the skill as the next agent would, on a scratch change that breaks the property in the real code. It must catch the break. Drop the change and confirm the check is back where it started.

## Keep it true

After changes that touched verified code without rechecking it. Edit only the verification (models, harnesses, properties, the verify skill), never product code. Each check ends **in sync**, **updated**, **bug** (the verification matches the code, and the code breaks the property) or **blocked**; it can be both updated and bug.

1. **Collect each check:** property, covered code, bounds, assumptions, command, and last confirmed commit. If none is recorded, use the last commit that changed the verification, and say so.
2. **Run it as it is.** A pass means the old description still holds, not that the code is right.
3. **Read every change to covered code** since then, including renamed, split or moved code, and new code touching guarded state. Classify each: no effect on what the model describes (judged against the model, not the commit message); the model no longer matches the code; the promise changed on purpose (cite the docs, tests, changelog or commit that says so); or the promise may be broken.
4. **Update from the code, not from the result.** Write the update before rerunning. Change a property only for a promise changed on purpose, recording old wording, new wording and evidence. Keep the bounds, and report any you had to reduce.
5. **Rerun and judge.** A pass: break the new code the way the property guards against, confirm the check catches it, drop the break. A failure: replay it on the real code step by step. A step that can't happen means the verification is wrong: fix it, and say what was wrong. If every step can happen, it's a bug: give the steps, the harm in one sentence, and the commit that introduced it.
6. **Update the verify skill:** coverage, commands, bounds, assumptions, and the confirmed commit, unmoved for a blocked check. Then follow it once as the next agent would.
7. **Report each check:** outcome, commits read, what changed and why, the rerun and the break that proved it can still fail, each bug in plain words, and what's still uncovered. Say which failures were drift and which were bugs; a check that passed before the update and fails after was passing on a stale description. Ship verification updates apart from any fix.

<!-- Adapts pstack's create-formal-verification-skill and maintain-formal-verification-skill skills (MIT, Copyright (c) 2026 Lauren Tan). See NOTICE.md. -->
