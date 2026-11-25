---
name: deeper
description: "Tighten a task brief to require primary sources, domain tools, and external proof without adding scope. Use before briefing or starting work."
disable-model-invocation: true
---

# Deeper

Rewrite a task so it executes at expert quality without adding scope, because weak briefs invite proxy shortcuts and rework.

Answer four questions, then rewrite the brief:

1. **Expert bar:** what checks, edge cases, and standards would a top domain practitioner include?
2. **Primary material:** what raw source should this start from (raw data, primary docs, spec, or real system) instead of a summary or wrapper?
3. **Domain methods and tools:** which established techniques and tools apply, by name?
4. **External proof:** what outside the implementation proves it right (**prove-it**)? Name a reference implementation, conformance suite, spec, dataset, or real workflow instead of agent say-so.

Keep the original deliverable and done-when without growing scope. Flag testable unknowns for the execution phase instead of running experiments pre-brief. For untestable calls (product direction or taste), follow prior decisions and escalate only when none apply.

**Done when:** the rewritten brief names primary sources, domain tools, external proof, and flagged unknowns without expanding scope.

Referenced skills: `prove-it` (`${CLAUDE_SKILL_DIR}/../prove-it/SKILL.md`). Read any cited skill file before acting when its trigger applies.

<!-- Adapts pstack's sharpen skill (MIT, Copyright (c) 2026 Lauren Tan). See NOTICE.md. -->
