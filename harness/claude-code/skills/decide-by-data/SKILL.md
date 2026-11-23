---
name: decide-by-data
description: "Choose between two designs by building both and measuring them at the extremes, never by argument. Use when picking one approach over another, when asked which is better, or before putting a design question to the person."
---

# Decide by data

Build both designs, A/B them at the extremes, force their failure modes, and let the data choose.

**Why:** argument is not evidence, and a design that wins in the middle of the range often loses at an edge.

- Write down the deciding metric and the result that picks each side before you run. Decided afterwards, the rule bends to the numbers.
- Put both behind one switch in one build, with counters that show why each wins. Separate builds differ in more than the design.
- Test the extremes the claim covers: smallest to largest machine, one client to the most, idle to overloaded. Failure modes hide in the middle.
- Keep machine, client, data and warm state the same. Alternate A and B, and repeat until you know the noise. A gap inside the noise is no gap.
- Delete the loser and its switch in the same change. Two paths cost upkeep and hide which one runs.
- Put the command and the numbers in the commit message, so anyone can rerun them.

<!-- Adapts pstack's explain-the-number and benchmark-checklist skills (MIT, Copyright (c) 2026 Lauren Tan). See NOTICE.md. -->
