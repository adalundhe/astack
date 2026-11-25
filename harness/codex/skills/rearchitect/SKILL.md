---
name: rearchitect
description: "Find high-churn structural friction, rank restructurings with diagrams, and plan execution via dagify. Use when code gets harder to change or test, or when improving architecture."
---

# Rearchitect

Find where codebase structure slows changes or testing, rank concrete restructurings, and execute the strongest fix cleanly.

## Discovery (Steps 1–7, read-only Researcher or Lead)

Read-only Researchers stop at Step 7 and hand ranked cards in `~/.cache/astack/<program>/` to Lead.

1. **Scope by churn.** Start where the person points; otherwise walk git history for the highest-churn areas. Run **lookup** and **rtfm** first to read prior lessons, ADRs, and domain docs.
2. **Hunt for structural friction** using a fresh read-only researcher (**how-it-works**):
   - one concept scattered across many small modules you must jump between;
   - shallow modules whose public interface rivals their implementation complexity;
   - logic extracted only for unit tests while bugs hide in caller wiring;
   - modules reaching into each other's internals;
   - code hard to test through its public interface, or untested.
3. **Apply the deletion test** to shallow layers. Keep a removal only if it consolidates complexity into one place rather than shifting it.
4. **Write a card per candidate.** List touched files, concrete friction, the plain fix, and expected payoff. Add a before-and-after diagram (**show-the-states** when behavior changes) and rate strength (`strong`, `worth exploring`, `speculative`).
5. **Sanity-check each proposal** against `no-bolt-ons`, `yagni`, and `minimize-state-stores`. Add an interface only for a second real implementation or system boundary, not speculative reuse. Benchmark any performance claim (`benchmarking`).
6. **Respect recorded decisions**. Reopen an existing architecture decision only when friction is severe, and flag that conflict explicitly on the card.
7. **Publish ranked cards** to `~/.cache/astack/<program>/` outside the repo, naming the top pick and why. Researchers stop here and return the report to Lead.

## Execution (Steps 8–10, Lead only)

Lead never codes before recording the decision and planning the DAG.

8. **Record the decision (**create-adc**):** start the top pick on its own branch unless redirected. Log rejected candidates and why so future reviews don't re-suggest them.
9. **Plan before coding (**dagify**):** break the restructure into small reviewed tasks with acceptance criteria and parallel lanes. Pin existing behavior with tests first (`tests-assert-behaviour`) and end in review.
10. **Dispatch workers in small passing steps:** split modules via `modularize` and compare close interface shapes with `ab-test`. Name new modules using existing domain vocabulary, updating the glossary if present.

**Done when:** ranked cards exist in `~/.cache/astack/<program>/`; for execution, the AD is recorded, the `dagify` plan passes review, and workers land green steps.

Referenced skills: `lookup` (`../lookup/SKILL.md`), `rtfm` (`../rtfm/SKILL.md`), `how-it-works` (`../how-it-works/SKILL.md`), `show-the-states` (`../show-the-states/SKILL.md`), `create-adc` (`../create-adc/SKILL.md`), `dagify` (`../dagify/SKILL.md`). Read any cited skill file before acting when its trigger applies.

<!-- Adapts the improve-codebase-architecture skill of mattpocock/skills (MIT, Copyright (c) 2026 Matt Pocock). See NOTICE.md. -->
