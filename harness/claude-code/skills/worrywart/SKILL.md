---
name: worrywart
description: "Push back with solid evidence on a review comment that is unproven, unreproducible, already handled by surrounding systems, or not worth its cost. Use before changing code for a questionable review point."
disable-model-invocation: true
---

# Worrywart

Push back on an incorrect or overstated review point with concrete evidence instead of debating it or blindly obeying it.

1. **Restate the claim** plainly: what the reviewer says breaks, for whom, and under what conditions.
2. **Test it first.** Run the reviewer's reproduction or construct the scenario they described. If it actually reproduces, it's real—fix it instead.
3. **Assemble concrete proof** that the claim doesn't hold:
   - logs, traces, or screenshots from running the real code;
   - a runnable demo or script the reviewer can execute to see it hold;
   - citations showing the surrounding system, config, or documented operational practice already handles it;
   - for design/architecture points, benchmarks or cited research (**research-this**, **prove-it**).
4. **Reply once,** impact first, with the evidence attached. The reviewer either withdraws the point or supplies a working reproduction.

If an agent reviewer repeatedly raises points that fail verification, replace it with a fresh reviewer.

Referenced skills: `research-this` (`${CLAUDE_SKILL_DIR}/../research-this/SKILL.md`), `prove-it` (`${CLAUDE_SKILL_DIR}/../prove-it/SKILL.md`). Read any cited skill file before acting when its trigger applies.
