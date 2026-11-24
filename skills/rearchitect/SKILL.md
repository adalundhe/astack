---
name: rearchitect
description: "Find where a codebase's structure makes it hard to change or test, propose ranked restructurings with before-and-after diagrams, and start on the strongest. Use when code keeps getting harder to change, when one area keeps breaking, or when asked to improve a codebase's architecture."
---

# Rearchitect

Find where a codebase's structure gets in the way, show how to fix it, and start on the best fix.

1. **Pick where to look.** Start where the person points. Otherwise start where the code changes most: walk back through the git history, and follow the files and areas that keep coming up. Read the architecture decisions and domain docs for that area first (**rtfm**).
2. **Look for friction,** with a fresh subagent reading the code (**how-it-works**):
   - one idea spread across many small modules you have to jump between;
   - shallow modules, whose interface is nearly as complex as what they hide;
   - logic pulled into separate functions only to test it, while the bugs live in how it's called;
   - modules that reach into each other's internals;
   - code that's hard to test through its interface, or not tested at all.
3. **Apply the deletion test** to anything that looks shallow: would deleting it gather the complexity into one place, or just move it around? Gathering it is the signal.
4. **Write up each candidate:** the files involved; the problem, as the friction it causes; the fix, in plain words; what it gains (related code in one place, fewer places to change per feature, tests through a smaller interface); a before-and-after diagram (**show-the-states** when it's about behaviour); and how strongly you recommend it: strong, worth exploring, or speculative.
5. **Check each fix** against **no-bolt-ons**, **yagni** and **minimize-state-stores**. An interface earns its place with a second real implementation or a real boundary, not a guess about the future. Measure any claim about speed (**benchmarking**).
6. **Respect earlier decisions.** If a candidate goes against a recorded architecture decision, raise it only when the friction is serious enough to reopen that decision, and say so on its card.
7. **Present the report** without waiting to be asked: a page outside the repository, in a cache folder, with the candidates ranked and your top pick and why (**play-with-me**).
8. **Start on the top pick,** on its own branch, and keep going unless the person redirects. Record it as the project's next architecture decision (**create-adc**), with the candidates you passed over and why, so a later review doesn't suggest them again.
9. **Change it safely:** pin today's behaviour with tests first (**tests-assert-behaviour**), plan the moves (**dagify**), and restructure in small steps that each pass (**modularize** for splits). When the right interface isn't clear, build two and compare them (**ab-test**).
10. **Use the project's own words** for what you name, and add new terms to its glossary if it keeps one.

<!-- Adapts the improve-codebase-architecture skill of mattpocock/skills (MIT, Copyright (c) 2026 Matt Pocock). See NOTICE.md. -->
