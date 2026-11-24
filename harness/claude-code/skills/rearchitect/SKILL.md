---
name: rearchitect
description: "Identify structural friction in a codebase (starting where code changes most), propose ranked restructurings with before-and-after diagrams, and execute the top pick via dagify. Use when code is getting harder to change or test, or when improving architecture."
disable-model-invocation: true
---

# Rearchitect

Find where the codebase's structure slows down changes or testing, rank concrete restructurings, and start executing the strongest fix.

1. **Scope by churn.** Start where the person points; otherwise walk git history to find the files and areas that change most often. Read existing architecture decisions and domain docs for that area first (**rtfm**).
2. **Hunt for structural friction** using a fresh read-only subagent (**how-it-works**):
   - one concept scattered across many small modules you have to jump between;
   - shallow modules whose public interface is nearly as complex as their implementation;
   - logic extracted solely to make it unit-testable while real bugs live in how callers wire it up;
   - modules reaching into each other's internals;
   - code that is hard to test through its public interface, or untested.
3. **Apply the deletion test** to anything that looks shallow: would removing that layer consolidate complexity into one clear place, or merely push it around? Consolidation is the signal.
4. **Write a card for each candidate:** files touched; concrete friction caused; plain description of the fix; expected payoff (related code together, fewer files edited per feature, testable through a smaller interface); before-and-after diagram (**show-the-states** when behavior changes); and recommendation strength (`strong`, `worth exploring`, or `speculative`).
5. **Sanity-check each proposal** against **no-bolt-ons**, **yagni**, and **minimize-state-stores**. Only add an abstraction/interface for a second real implementation or real system boundary—not speculative reuse. Benchmark any performance claim (**benchmarking**).
6. **Respect recorded decisions.** If a candidate contradicts an existing architecture decision, include it only when the friction is severe enough to reopen that decision, and flag it explicitly on the card.
7. **Present the report proactively** as a page in a cache folder outside the repository, with candidates ranked, your top pick, and why (**play-with-me**).
8. **Start the top pick** on its own branch and keep moving unless the person redirects. Record it as the next architecture decision (**create-adc**), including rejected candidates and why so future reviews don't re-suggest them.
9. **Plan the move with dagify** (**dagify**): break the restructure into small reviewed tasks with acceptance criteria and tests—pinning current behavior first (**tests-assert-behaviour**) and ending in review—ordered so independent moves run in parallel.
10. **Land in small passing steps** (**modularize** for splits). When two interface shapes look close, prototype and compare both (**ab-test**).
11. **Match domain terminology:** name new modules using the project's existing vocabulary, updating its glossary if it maintains one.

Referenced skills: `rtfm` (`${CLAUDE_SKILL_DIR}/../rtfm/SKILL.md`), `how-it-works` (`${CLAUDE_SKILL_DIR}/../how-it-works/SKILL.md`), `show-the-states` (`${CLAUDE_SKILL_DIR}/../show-the-states/SKILL.md`), `no-bolt-ons` (`${CLAUDE_SKILL_DIR}/../no-bolt-ons/SKILL.md`), `yagni` (`${CLAUDE_SKILL_DIR}/../yagni/SKILL.md`), `minimize-state-stores` (`${CLAUDE_SKILL_DIR}/../minimize-state-stores/SKILL.md`), `benchmarking` (`${CLAUDE_SKILL_DIR}/../benchmarking/SKILL.md`), `play-with-me` (`${CLAUDE_SKILL_DIR}/../play-with-me/SKILL.md`), `create-adc` (`${CLAUDE_SKILL_DIR}/../create-adc/SKILL.md`), `dagify` (`${CLAUDE_SKILL_DIR}/../dagify/SKILL.md`), `tests-assert-behaviour` (`${CLAUDE_SKILL_DIR}/../tests-assert-behaviour/SKILL.md`), `modularize` (`${CLAUDE_SKILL_DIR}/../modularize/SKILL.md`), `ab-test` (`${CLAUDE_SKILL_DIR}/../ab-test/SKILL.md`). Read any cited skill file before acting when its trigger applies.

<!-- Adapts the improve-codebase-architecture skill of mattpocock/skills (MIT, Copyright (c) 2026 Matt Pocock). See NOTICE.md. -->
