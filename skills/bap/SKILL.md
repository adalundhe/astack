---
name: bap
description: "Immediate mid-session course correction when the person has to repeat a reminder, rule, or correction: stop hollow apologies, audit why the miss happened, repair live session state and drifted workers, and lock in a structural guard so they never have to repeat it. Use on /astack:bap or whenever corrected on something already established."
disable-model-invocation: true
---

# Bap

Stop immediately when the person has to repeat themselves. Don't apologize, patch the symptom, and forget again two turns later—fix **why** it slipped right now.

1. **Full stop, zero fluff (**wat**):** drop sycophantic apologies and defensive explanations. State the missed rule or instruction in one plain sentence.
2. **Audit why it slipped (not just what slipped):** trace the real breakdown across the session—
   - skipped or unloaded skill (`astack-tools skills list --role <role>` / `skills get <name>`);
   - dropped role (lead solo-coding or solo-debugging instead of delegating, or drifting out of Go mode);
   - ignored prior decision or directive (`LANES.md` `person:` / `decided:`, `RULES.md`, repo docs via **rtfm**);
   - drifted or stale worker/subagent that never received the directive;
   - missing mechanical check, hook, test, or brief constraint letting the mistake slip through.
3. **Repair both the immediate miss and live session state now:**
   - load any skipped skill in full before touching anything else;
   - undo or fix the immediate mistake cleanly (delegating code edits to a fresh worker if you are Lead, and re-running any skipped verification or **review**);
   - pin the person's rule verbatim where live work sees it (`RULES.md` + `LANES.md` `person:` if in a program), and steer or replace any drifted subagent (**lead**).
4. **Prevent repeat #3 (**make-it-stick**):** climb the structural fix ladder in order—architecture -> types -> lint/hook -> automated test -> scoped `LESSONS.md` or rule/skill update (only proposing rule/skill edits to the source repo with evidence when stronger rungs can't catch it).
5. **Report cleanly in 3 bullets:** what slipped and why, what you just fixed (with verification), and the guard preventing it from recurring.
