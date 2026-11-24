---
name: delight-users
description: "Choose the user's experience over the builder's convenience, where the user is whoever consumes the work: end user, API caller, operator, next maintainer. Use when designing, writing or reviewing anything someone will use."
---

# Delight users

Put the user's experience ahead of the builder's convenience.

## Start with

1. **Know who the user is:** whoever consumes the work, whether the person using the product, the engineer calling the API, the operator running it, or the next maintainer. Judge from their side, and state impact in their terms.
2. **Build everything the person asked for, polished, and nothing they didn't** (**never-trade-functionality**).
3. **Get the details right:** feedback for every action, errors that say what to do next, empty, loading and failure states, sensible defaults, transitions, alignment, spacing.
4. **Prototype first:** a throwaway mockup or a small lab before the real build, presented to the person as you go (**play-with-me**).
5. **Tighten the core loop:** what users do most is the fastest, clearest thing in the product.

## Watch for

- actions with no feedback; errors that don't say what happened or what to do next; missing empty, loading or failure states;
- defaults that make most users configure what they never needed to; options nobody asked for;
- APIs that are easy to call wrong: unclear names, long lists of positional arguments, surprising behaviour;
- the most common task taking more steps than it needs;
- inconsistent wording, alignment and spacing.

**The test:** would a user meeting this for the first time know what happened, and what to do next?

## When it doesn't fit

- following the platform's or the project's design conventions, even where another choice looks nicer;
- a detail no user ever meets;
- a choice the person made, on record;
- an approach the evidence here favours: when unsure, try both and measure (**ab-test**), and say why you chose it.

<!-- Adapts pstack's experience-first principle (MIT, Copyright (c) 2026 Lauren Tan). See NOTICE.md. -->
