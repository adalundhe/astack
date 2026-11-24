---
name: delight-users
description: "Design and audit work from the consumer's side (end user, API caller, operator, or maintainer): clear feedback, actionable errors, complete states, good defaults, and ergonomic APIs. Use when designing, building, or reviewing user-facing work."
---

# Delight users

Prioritize the consumer's experience over implementation convenience.

## Start with

1. **Identify the consumer:** whoever uses the output—end user, API caller, operator, or next maintainer. Evaluate from their perspective and describe impact in their terms.
2. **Deliver the full request cleanly**—polished, complete, and without unrequested extras (**never-trade-functionality**).
3. **Sweat the details:** visible feedback for every action, errors that explain what failed and what to do next, explicit empty/loading/failure states, sensible defaults, and clean layout/copy.
4. **Prototype early:** build a quick throwaway demo or harness before the full implementation and share it proactively (**play-with-me**).
5. **Tighten the core loop:** make the most frequent user action the fastest and clearest path.

## Watch for

- actions with no feedback, or errors that don't say what went wrong or how to fix it;
- missing empty, loading, or failure states;
- defaults that force most users to configure things manually, or options nobody asked for;
- error-prone APIs (vague names, long positional argument lists, surprising behavior);
- unnecessary steps in the most common workflow;
- inconsistent wording, alignment, or spacing.

**The test:** would someone encountering this for the first time know what happened and what to do next?

## When it doesn't fit

- matching platform or project conventions even when another style looks nicer;
- internal details no consumer encounters;
- an explicit recorded choice by the person;
- an alternative backed by measurements (**ab-test**), with the reasoning noted.

<!-- Adapts pstack's experience-first principle (MIT, Copyright (c) 2026 Lauren Tan). See NOTICE.md. -->
