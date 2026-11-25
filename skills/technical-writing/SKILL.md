---
name: technical-writing
description: "Audit impacted docs on every change and write clear, concrete, code-verified technical docs. Use whenever changes affect interfaces, config, or ops."
disable-model-invocation: true
---

# Technical writing

Keep docs accurate on every change. Write so an engineer can use, debug, or modify the system on the first read.

1. **Discover and audit impacted docs on every change:** inspect every doc set the repo maintains (guides, references, config docs, runbooks, ADRs, diagrams—never assume one layout). Update or delete anything rendered stale in the same change (**yagni**, **no-hidden-config**), or flag out-of-scope docs for the lead, because stale docs mislead worse than missing docs. If nothing needs updating, verify that explicitly.
2. **Start with the reader's task:** state what the system is and what problem it solves in the first two sentences. Put setup and common tasks near the top. Push history and background to the bottom, or cut them.
3. **Be concrete, never vague:**
   - Replace marketing copy and bare adjectives ("blazing fast", "seamless", "robust") with exact behavior, limits, defaults, and numbers.
   - Show exact commands, file paths, flags, inputs, and expected outputs.
   - Document failure modes, prerequisites, and platform differences explicitly.
4. **Verify every claim against real code (`prove-it`):** confirm every command, flag, default, path, and example matches the repo and runs as written.
5. **Write for scanning:**
   - Use short sentences, active voice, and direct imperatives ("Run X", not "You might consider running X").
   - Use plain topic headings, bullets for parallel items, and tables only for multi-column comparisons.
   - Add Mermaid diagrams (**show-the-states**) when state or data flow is clearer visually.
   - Define domain terms inline on first use and keep internal jargon out of user-facing docs (**wat**). Remove parallel docs for deleted behavior.

**Done when:** every impacted in-scope doc is updated and verified against current code, out-of-scope docs are flagged for the lead, and zero stale claims remain.
