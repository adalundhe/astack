---
name: show-the-states
description: "Diagram a system's states, triggers, conditions, failure paths, and observed probabilities in Mermaid stateDiagram-v2 (backed by astack-statechart for TLA+ models and DOT graphs). Use for debugging, onboarding, design, planning, or reviews."
disable-model-invocation: true
---

# Show the states

Diagram how a system moves between states so readers can see what happens, what triggers it, and how failures unfold at a glance.

## Run `astack-statechart` for TLA+ models and DOT graphs

Use the bundled `astack-statechart` CLI (`PATH` or `${CLAUDE_SKILL_DIR}/../../bin/astack-statechart`) instead of transcribing traces by hand (see `--help` for all flags):

- **Model-check with TLC and draw the chart:**
  `astack-statechart check MODEL.tla [--cfg MODEL.cfg] [--mermaid out.mmd] [--json]`
  Runs TLC in `-tool` mode with single-worker minimum-depth BFS (`--workers 1`) and `-continue` so every broken invariant is captured. Follows TLC's exit status strictly (`0` clean, `1` violation/deadlock, `2` tool/spec error) and emits collision-safe Mermaid `stateDiagram-v2`.
- **Render existing TLC DOT or trace output offline:**
  `astack-statechart render states.dot [--trace tlc.out] [--mermaid out.mmd] [--json]`
  Computes minimum-hop BFS paths to violations and pins initial and failure-path states even when `--max-states` trims large graphs.

Use the tool's verified graph as ground truth, then translate raw variable names into domain words for human readers.

## Authoring and reviewing state charts

1. **State the context first:** name the system, the question the chart answers, its scope, and where states come from (code `file:line`, formal model, logs, or design).
2. **Use domain words, not variable names:** name states after what users or operators care about (`"Paying"`, `"Lease held"`). Label transitions with the event or failure and bracket guards (`"user clicks play [while loading]"`).
3. **Include structure:** show start/end states, nested substates for phases, and parallel regions for independent components.
4. **Add probabilities only from data:** cite source, window, and count. Without data, run a seeded simulation or use **research-this** for published rates—never guess (**no-picked-constants**).
5. **Highlight failures:** mark invariant-violating states and shortest failure paths. While debugging, attach log/trace evidence per step and flag the bad or missing transition (**find-it**).
6. **Keep it scannable:** collapse equivalent states and note what you omitted, without hiding distinct rule violations or stranding states.
7. **Render inline and hand off—never leave a diagram stranded:** put the `stateDiagram-v2` block inline in your report (`DIAGRAMS` section for researchers/workers) so the lead presents it. Carry diagrams that explain system behavior, cutovers, or failures into the PR description (**watch-pr**) and matching repo docs or runbooks (**technical-writing**).

During planning, annotate which task builds which states and check code against the chart during review.

<!-- Adapts pstack's statechart skill and TLC statechart tool (MIT, Copyright (c) 2026 Lauren Tan). See NOTICE.md. -->
