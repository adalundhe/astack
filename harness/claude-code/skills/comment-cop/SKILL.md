---
name: comment-cop
description: "Strip comments that narrate or excuse the code, keeping only what code can't express (API contracts, external constraints, legal headers, issue links). Use when writing, reviewing, or cleaning up comments."
disable-model-invocation: true
---

# Comment cop

Remove comments that the code already explains (or should explain), and keep only what code can't express.

## Start with

1. **Make the code self-explanatory** through clearer names, smaller functions, and tighter types.
2. **Delete workarounds** instead of excusing them in comments (**yagni**), or fix the underlying cause.
3. **Fix surprising code** until it reads naturally, rather than leaving a comment apologizing for it.

## Watch for

- comments narrating what the next lines obviously do;
- ASCII banners, section dividers, and commented-out code;
- change history ("changed for X", "used to be Y")—that belongs in git;
- comments justifying avoidable workarounds;
- comments that contradict the code (treat as a bug and find out which is right).

**The test:** could a better name, smaller function, or stronger type say this instead?

## When it doesn't fit

- license and legal headers;
- public API contracts and docstrings;
- external constraints (vendor bugs, protocol quirks, OS limitations) with a link to the source;
- links to issues, specs, or ADs explaining a non-obvious decision;
- lint suppressions explaining why the rule doesn't apply to that line.

Referenced skills: `yagni` (`${CLAUDE_SKILL_DIR}/../yagni/SKILL.md`). Read any cited skill file before acting when its trigger applies.

<!-- Adapts pstack's comment-sicko agent and no-comments skill (MIT, Copyright (c) 2026 Lauren Tan). See NOTICE.md. -->
