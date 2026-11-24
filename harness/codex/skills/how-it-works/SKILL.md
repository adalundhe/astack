---
name: how-it-works
description: "Give a read-only, file-and-line-cited walkthrough of part of a codebase (mental model, components, flow, state, gotchas), marking claims as run vs. read. Use before editing unfamiliar code or answering 'how does X work' / 'where should this live'."
---

# How it works

Explain how part of a system works with every claim cited to exact files and lines.

If the question is ambiguous, state which interpretation you're answering and proceed.

1. **Check existing docs first** (**rtfm**): READMEs, docs, and architecture decisions.
2. **Explore read-only**—use a subagent for large areas so raw file dumps stay out of the main context.
3. **Verify critical claims by running code** (a test, trace, log line, or scratch command) and label each claim as **run** or **read** (**prove-it**).
4. **Write for an engineer new to this area:** what it does for users; main components and what each owns; end-to-end request/event flow; where state lives and what mutates it; and surprising behavior or gotchas. Cite `file:line` for each claim, define unfamiliar terms inline, and include a diagram (**talk-to-me**, **show-the-states**) plus one concrete end-to-end example.
5. **For "where should this live":** show where analogous code already lives and which way dependencies point, then give a clear recommendation.

Referenced skills: `rtfm` (`../rtfm/SKILL.md`), `prove-it` (`../prove-it/SKILL.md`), `talk-to-me` (`../talk-to-me/SKILL.md`), `show-the-states` (`../show-the-states/SKILL.md`). Read any cited skill file before acting when its trigger applies.

<!-- Adapts pstack's how skill (MIT, Copyright (c) 2026 Lauren Tan). See NOTICE.md. -->
