---
description: "Explain unfamiliar rate-limiting algorithms in ./repo/src/limiter.py (token bucket vs leaky bucket), persist structured research under ASTACK_HOME, include a Mermaid diagram and plain guide, and build a runnable local demo in program/demo/ while keeping ./repo clean."
expected_outcome: "Reads idk/SKILL.md, saves structured research notes under program/astack_home/rate-demo/research/, builds a runnable Python demo under program/demo/ that imports and exercises repo/src/limiter.py non-interactively, provides a Mermaid diagram and plain explanation with analogy and walkthrough in final_text or program/EXPLAINER.md, and leaves ./repo clean."
allowed_tools: [Read, Glob, Grep, Bash, Write, Edit]
---

`/astack:go` I am unfamiliar with the two rate limiters implemented in `./repo/src/limiter.py` (`TokenBucket` vs `LeakyBucket`) for project `rate-demo` (`ASTACK_HOME=./program/astack_home`).

Please help me understand when each fits our API gateway, save structured research notes under `$ASTACK_HOME/rate-demo/research/`, give a plain explanation with a Mermaid diagram and concrete analogy (in your final response or `./program/EXPLAINER.md`), and build a runnable local demo script in `./program/demo/` that exercises `./repo/src/limiter.py` (running a default comparison when invoked directly so I can try it in one command and tweak parameters). Leave `./repo` untouched.
