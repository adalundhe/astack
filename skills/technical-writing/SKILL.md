---
name: technical-writing
description: "Analyze documentation impact on every change and write clear, concrete, verified technical documentation with real examples and zero fluff. Use whenever a change affects behavior, interfaces, config, architecture, or operations, or when writing/revising docs."
disable-model-invocation: true
---

# Technical writing

Keep documentation accurate on every change, and write it so an engineer can use, debug, or change the system on the first read.

1. **Discover and audit impacted docs on every change:** inspect what documentation the repository actually maintains (guides, references, config/flag docs, runbooks, ADRs, inline diagrams—whatever exists in the repo, never assuming one fixed layout), identify everything rendered stale, incomplete, or contradicted by the change, and update or delete it in the same change (**yagni**, **no-hidden-config**). If nothing needs updating, verify that explicitly rather than skipping the check.
2. **Start with who reads this and what they need to do:** state what the thing is and what problem it solves in the first two sentences. Put setup and common tasks near the top; push history and background to the bottom (or leave them out).
3. **Be concrete, never vague:**
   - Replace slogans, marketing copy, and bare adjectives ("blazing fast", "seamless", "robust", "battle-tested") with specific behavior, constraints, defaults, and numbers.
   - Show exact commands, file paths, flags, inputs, and expected outputs.
   - Document failure modes, prerequisites, and platform differences explicitly.
4. **Verify every claim against the real code** (**prove-it**): confirm every command, flag, default value, file path, and example actually matches the current repository and runs as written.
5. **Write for scanning:**
   - Short sentences, active voice, direct imperatives ("Run X", not "You might want to consider running X").
   - Headings that state the topic plainly; bullets for parallel items; tables only for structured multi-column comparisons; Mermaid diagrams (**show-the-states**) when state or data flow is clearer visually.
   - Define domain terms inline where they first appear, and keep internal jargon out of user-facing docs (**wat**). Don't leave parallel docs describing removed behavior.
