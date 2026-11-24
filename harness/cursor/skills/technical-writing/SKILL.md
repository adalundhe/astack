---
name: technical-writing
description: "Write clear, concrete, verified technical documentation (READMEs, guides, API refs, ADs, runbooks) with real examples and zero fluff. Use when writing or revising docs."
disable-model-invocation: true
---

# Technical writing

Write documentation that helps an engineer use, debug, or change the system accurately on the first read.

1. **Start with who reads this and what they need to do:** state what the thing is and what problem it solves in the first two sentences. Put setup and common tasks near the top; push history and background to the bottom (or leave them out).
2. **Be concrete, never vague:**
   - Replace slogans, marketing copy, and bare adjectives ("blazing fast", "seamless", "robust", "battle-tested") with specific behavior, constraints, defaults, and numbers.
   - Show exact commands, file paths, flags, inputs, and expected outputs.
   - Document failure modes, prerequisites, and platform differences explicitly.
3. **Verify every claim against the real code** (**prove-it**): confirm every command, flag, default value, file path, and example actually matches the current repository and runs as written.
4. **Write for scanning:**
   - Short sentences, active voice, direct imperatives ("Run X", not "You might want to consider running X").
   - Headings that state the topic plainly; bullets for parallel items; tables only for structured multi-column comparisons; Mermaid diagrams (**show-the-states**) when state or data flow is clearer visually.
   - Define domain terms inline where they first appear, and keep internal jargon out of user-facing docs (**wat**).
5. **Keep docs synchronized with code:** update or delete stale docs in the same change as the code (**yagni**, **no-hidden-config**). Don't leave parallel docs describing removed behavior.

Referenced skills: `prove-it` (`../prove-it/SKILL.md`), `show-the-states` (`../show-the-states/SKILL.md`), `wat` (`../wat/SKILL.md`), `yagni` (`../yagni/SKILL.md`), `no-hidden-config` (`../no-hidden-config/SKILL.md`). Read any cited skill file before acting when its trigger applies.
