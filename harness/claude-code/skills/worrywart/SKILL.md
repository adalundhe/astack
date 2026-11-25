---
name: worrywart
description: "Push back on unproven or overstated review comments with concrete runnable evidence instead of debate. Use before changing code for a questionable point."
disable-model-invocation: true
---

# Worrywart

Push back on an incorrect or overstated code-review finding or PR comment (human or agent) with concrete evidence, because debating opinions wastes rounds and blindly obeying adds dead complexity. For peer-to-peer interrogation of hypotheses, diagnoses, designs, or plans, use `challenge` instead.

1. **Restate the claim plainly:** state what the reviewer says breaks, for whom, and under what conditions.
2. **Test it first:** run the reviewer's reproduction or build the exact scenario they described. If it reproduces, the point is real—fix it instead of pushing back.
3. **Assemble concrete proof** that the claim does not hold:
   - logs, traces, or screenshots from running the real code;
   - a runnable command or script the reviewer can execute to verify;
   - citations showing the surrounding system, config, or documented ops practice already handles it;
   - benchmarks or graded prior art for architecture points (**research-this**, **prove-it**).
4. **Reply once, impact first, with proof attached:**
   - **Human-facing PR replies:** clear an independent second-agent **leave-feedback** audit (`CLEAR`) before posting.
   - **Workers:** draft the evidence-backed rebuttal in your report for the Lead to audit and post.
   - The reviewer either withdraws the point or supplies a working reproduction.

**Lead only:** if an agent reviewer repeatedly raises points that fail verification, replace it with a fresh reviewer.

**Done when:** the claim is either reproduced and routed to a fix, or rebutted once with runnable proof (and audited via **leave-feedback** if human-facing).

Referenced skills: `research-this` (`${CLAUDE_SKILL_DIR}/../research-this/SKILL.md`), `prove-it` (`${CLAUDE_SKILL_DIR}/../prove-it/SKILL.md`), `leave-feedback` (`${CLAUDE_SKILL_DIR}/../leave-feedback/SKILL.md`). Read any cited skill file before acting when its trigger applies.
