---
name: show-the-states
description: "Compute checked Mermaid stateDiagram-v2 charts from TLC graphs using view modules. Use for debugging, onboarding, design, planning, or reviews."
disable-model-invocation: true
---

# Show the states

Diagram how a system moves between states so readers see triggers, guards, and rule breaks at a glance.

## Compute charts from checked graphs with `astack-statechart`

Use `astack-statechart` (for TLA+/TLC) instead of hand-editing raw traces. Never rename a checked graph by hand, because hand-edited charts drift from the model.

- **Install TLC automatically:** `astack-statechart check` installs pinned SHA-256-verified `tla2tools.jar` into user space automatically when Java is present. Run `astack-statechart install-tlc` explicitly to pre-install or verify TLC.
- **Check a TLA+ model and compute a reader chart:**
  `astack-statechart check MODEL.tla [--cfg MODEL.cfg] --view VIEW.py [--mermaid out.mmd] [--json]`
  Maps TLC exit codes strictly (`0` clean, `1` for violation exits `10–14`, `2` for tool/spec/view errors). Model intentional end states with a self-looping end action (`Done == pc = "done" /\ UNCHANGED vars`) instead of blindly skipping deadlock checks.
- **Render existing TLC DOT or trace files offline:**
  `astack-statechart render states.dot [--trace tlc.out] --view VIEW.py [--mermaid out.mmd] [--json]`
  Preserves shortest violation paths and pins failure states even under `--max-states`.

## Write a small view module (`VIEW.py` or `VIEW.json`)

Review any `.py` view module before executing it, because it is code. Use a declarative `.json` view spec when simple mapping suffices.

A Python view module maps each parsed state dict `s` into the reader's words:

- **Flat or nested states:** `state(s)` returns `"Idle"` or a composite path `("Checkout", "Retrying")`, or `{"label": "Closed", "end": True}`.
- **Parallel regions:** export `regions = {"Payment": ..., "Inventory": ...}` or return `{"parent": "Active", "parallel": {"Payment": ..., "Inventory": ...}}`. Synchronized multi-region transitions get explicit `[sync ...]` tags.
- **Transitions & guards:** define `action_labels = {...}` or `transition(src, action, dst)` returning `"retry [attempts < max]"` (or `None` to hide an internal step, counted transparently).
- **Rule marking:** define `rule_labels = {"InvNoDoublePay": "Never charge twice"}` and optional `rules = {"Rule": lambda s: ...}`. Clean and violating concrete states that share a label split automatically, and cross-region breaks render as red violation states.

## Authoring and reviewing state charts

1. **State the context first:** name the system, the question answered, and the scope. Cite where states come from (code `file:line`, model + view module, logs, or design).
2. **Use domain words, not variable names:** name states after outcomes (`"Paying"`, `"Lease held"`) and label edges with event plus bracketed guard (`"click play [loading]"`).
3. **Include structure:** show start/end states, nested substates for phases, and parallel regions for independent components.
4. **Add probabilities only from data:** cite source, window, and count. Without data, run a seeded simulation or use **research-this** for published rates—never guess (`no-picked-constants`).
5. **Highlight failures:** mark rule-breaking states and shortest failure paths. While debugging, attach log/trace evidence per step and flag the bad or missing transition (`find-it`).
6. **Keep it scannable:** collapse equivalent states through the view module and note omissions, without hiding distinct rule breaks or stranding states.
7. **Render inline—never leave a diagram stranded.** Put `stateDiagram-v2` inline in your report (`DIAGRAMS` section) so Lead presents it. Copy behavioral, cutover, or failure diagrams into the PR (`watch-pr`) and repo docs (**technical-writing**).

During planning, map which task builds which states and check code against the chart during review.

**Done when:** the diagram uses domain names, computes directly from a checked model/view (or verified code/logs), highlights rule breaks, and renders inline in reports/PRs/docs.

Referenced skills: `research-this` (`${CLAUDE_SKILL_DIR}/../research-this/SKILL.md`), `technical-writing` (`${CLAUDE_SKILL_DIR}/../technical-writing/SKILL.md`). Read any cited skill file before acting when its trigger applies.

<!-- Adapts pstack's statechart skill and TLC statechart tool (MIT, Copyright (c) 2026 Lauren Tan). See NOTICE.md. -->
