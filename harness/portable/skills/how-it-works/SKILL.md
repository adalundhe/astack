---
name: how-it-works
description: "Give a read-only, file-and-line-cited walkthrough of a codebase area, marking claims as ran vs. read. Use before editing unfamiliar code or answering 'how does X work' / 'where should this live'."
disable-model-invocation: true
---

# How it works

Explain how part of a system works with every claim cited to exact files and lines, because memory rots faster than code.

If the question is ambiguous, state which interpretation you're answering and proceed.

1. **Check existing docs first** (**rtfm**): read READMEs, docs, and architecture decisions.
2. **Explore read-only.** Lead only: delegate large areas to `astack-researcher`—subagents never spawn subagents.
3. **Verify critical claims by running code:** run a test, trace, log, or scratch command (**prove-it**). Label each claim as **ran** or **read**.
4. **Write for a new engineer:** cover user-visible purpose, main components, end-to-end flow, state, and gotchas. Cite `file:line`, define unfamiliar terms inline, add a diagram (**show-the-states**), and walk one concrete example.
5. **For "where should this live":** show analogous code and dependency direction, then give one clear recommendation.
6. **Persist durable notes outside the repo:** when saving project walkthroughs or reference docs (not research, architecture, reviews, or repros), write them under `$HOME/.astack/<project_name>/docs/` (`%USERPROFILE%\.astack\...` on Windows) via `astack-tools docs path`. Read-only roles return the draft and target path for the lead.

**Done when:** every claim cites `file:line`, marks **ran** vs. **read**, and includes a diagram plus one concrete end-to-end example.

Referenced skills: `rtfm` (`../rtfm/SKILL.md`), `prove-it` (`../prove-it/SKILL.md`), `show-the-states` (`../show-the-states/SKILL.md`). Read any cited skill file before acting when its trigger applies.

<!-- Adapts pstack's how skill (MIT, Copyright (c) 2026 Lauren Tan). See NOTICE.md. -->
