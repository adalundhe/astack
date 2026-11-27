---
type: llm
---

Evaluate the research notes, explanation, Mermaid diagram, and local demo against `idk/SKILL.md`.

PASS if all of these hold:
- Saves structured research notes under `program/astack_home/rate-demo/research/` comparing token-bucket and leaky-bucket rate limiting grounded in `repo/src/limiter.py`.
- Delivers a first-read plain explanation (in `final_text` or `program/EXPLAINER.md`) with bottom-line recommendation, a Mermaid diagram, a grounded analogy plus where the analogy breaks down, and a walkthrough.
- Builds and verifies a runnable demo script under `program/demo/` that imports and runs `repo/src/limiter.py` directly without mutating `./repo`.
- Leaves `./repo` untouched and emits zero internal jargon.

FAIL otherwise.
