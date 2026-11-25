---
name: show-the-states
description: "Diagram system states, triggers, failure paths, and observed probabilities in Mermaid stateDiagram-v2. Use for debugging, onboarding, design, planning, or reviews."
disable-model-invocation: true
---

# Show the states

Diagram how a system moves between states so readers see triggers, guards, and failures at a glance.

## Run `astack-statechart` for TLA+ models and DOT graphs

Use the bundled `astack-statechart` CLI instead of transcribing traces by hand. Run it from `PATH` or the plugin's `bin/` (see `--help` for all flags):

- **Model-check with TLC and draw the chart:**
  `astack-statechart check MODEL.tla [--cfg MODEL.cfg] [--mermaid out.mmd] [--json]`
  Emits collision-safe Mermaid `stateDiagram-v2` and preserves TLC exit codes (`0` clean, `1` violation/deadlock, `2` tool/spec error).
- **Render existing TLC DOT or trace output offline:**
  `astack-statechart render states.dot [--trace tlc.out] [--mermaid out.mmd] [--json]`
  Emits shortest violation paths and keeps failure states visible even when `--max-states` trims large graphs.

Use the verified graph as ground truth. Translate raw variable names into domain words for human readers.

## Authoring and reviewing state charts

1. **State the context first:** name the system, the question answered, and the scope. Cite where states come from (code `file:line`, formal model, logs, or design).
2. **Use domain words, not variable names,** because internal flags confuse operators and reviewers. Name states after outcomes (`"Paying"`, `"Lease held"`) and label transitions with event plus bracketed guard (`"click play [loading]"`).
3. **Include structure:** show start/end states, nested substates for phases, and parallel regions for independent components.
4. **Add probabilities only from data:** cite source, window, and count. Without data, run a seeded simulation or use **research-this** for published rates—never guess (`no-picked-constants`).
5. **Highlight failures:** mark invariant-violating states and shortest failure paths. While debugging, attach log/trace evidence per step and flag the bad or missing transition (`find-it`).
6. **Keep it scannable:** collapse equivalent states and note omissions, without hiding distinct rule violations or stranding states.
7. **Render inline—never leave a diagram stranded**. Put `stateDiagram-v2` inline in your report (`DIAGRAMS` section) so Lead presents it, because hidden files go unread. Copy behavioral, cutover, or failure diagrams into the PR (`watch-pr`) and repo docs or runbooks (**technical-writing**).

During planning, map which task builds which states and check code against the chart during review.

**Done when:** diagrams use domain names, render inline in reports/PRs/docs, and trace back to verified code, logs, or TLC output.

<!-- Adapts pstack's statechart skill and TLC statechart tool (MIT, Copyright (c) 2026 Lauren Tan). See NOTICE.md. -->
