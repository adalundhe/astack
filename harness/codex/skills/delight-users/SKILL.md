---
name: delight-users
description: "Design consumer-facing work for clear feedback, actionable errors, complete states, and good defaults. Use when designing, building, or reviewing user-facing work."
---

# Delight users

Prioritize the consumer's experience over implementation convenience, because rough defaults and silent failures cost every caller time.

## Start with

1. **Identify the consumer:** name who uses the output—end user, API caller, operator, or maintainer. Evaluate impact in their terms.
2. **Deliver the full request cleanly:** ship it polished and complete without unrequested extras.
3. **Sweat the details:** show visible feedback for every action, and write errors that state what failed and what to do next. Cover empty, loading, and failure states explicitly, pick sensible defaults, and keep copy and layout clean.
4. **Prototype early:** build a quick throwaway demo or harness before full implementation and share it proactively (**play-with-me**).
5. **Tighten the core loop:** make the most frequent user action the fastest and clearest path. Step complexity across tiers without cliff jumps (**stepped-complexity**, **next-step**).

## Watch for

- inaccessible UIs (missing keyboard navigation, semantic labels/ARIA, visible focus states, or readable contrast);
- actions with no feedback, or errors that hide what failed or how to fix it;
- missing empty, loading, or failure states;
- defaults that force manual setup, or options nobody asked for;
- error-prone APIs (vague names, long positional argument lists, surprising behavior);
- unnecessary steps in the most common workflow;
- inconsistent wording, alignment, or spacing.

**The test:** would someone encountering this cold know what happened and what to do next?

## When it doesn't fit

- matching platform or project conventions even when another style looks nicer;
- internal details no consumer encounters;
- an explicit recorded choice by the person;
- an alternative backed by measurements (**ab-test**), with the reasoning noted.

**Showing it:** walk the primary, empty, and error flows cold and show any dead-end error, missing feedback, or guessed default.

Referenced skills: `play-with-me` (`../play-with-me/SKILL.md`), `stepped-complexity` (`../stepped-complexity/SKILL.md`), `next-step` (`../next-step/SKILL.md`), `ab-test` (`../ab-test/SKILL.md`). Read any cited skill file before acting when its trigger applies.

<!-- Adapts pstack's experience-first principle (MIT, Copyright (c) 2026 Lauren Tan). See NOTICE.md. -->
