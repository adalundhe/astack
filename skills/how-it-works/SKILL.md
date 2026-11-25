---
name: how-it-works
description: "Give a read-only, file-and-line-cited walkthrough of part of a codebase (mental model, components, flow, state, gotchas), marking claims as run vs. read. Use before editing unfamiliar code or answering 'how does X work' / 'where should this live'."
disable-model-invocation: true
---

# How it works

Explain how part of a system works with every claim cited to exact files and lines.

If the question is ambiguous, state which interpretation you're answering and proceed.

1. **Check existing docs first** (**rtfm**): READMEs, docs, and architecture decisions.
2. **Explore read-only**—use a subagent for large areas so raw file dumps stay out of the main context.
3. **Verify critical claims by running code** (a test, trace, log line, or scratch command) and label each claim as **run** or **read** (**prove-it**).
4. **Write for an engineer new to this area:** cover user-visible purpose, main components, end-to-end flow, where state lives, and surprising gotchas. Cite `file:line` for each claim, define unfamiliar terms inline, and add a diagram (**talk-to-me**, **show-the-states**) plus one concrete end-to-end example.
5. **For "where should this live":** show where analogous code already lives and which way dependencies point, then give a clear recommendation.

<!-- Adapts pstack's how skill (MIT, Copyright (c) 2026 Lauren Tan). See NOTICE.md. -->
