---
name: bap
description: "Immediate mid-session course correction when the person has to repeat a reminder, rule, or correction: drop apologies, audit why it slipped, repair live state and drifted workers, and lock in a structural guard."
disable-model-invocation: true
---

# Bap

Stop immediately when the person has to repeat themselves. Don't apologize, patch the symptom, and forget again two turns later—fix **why** it slipped right now.

1. **Full stop, zero fluff (**wat**):** skip apologies and defensive explanations. State the missed rule in one plain sentence.
2. **Audit why it slipped, not just what slipped:** run **lookup** first to see if a saved `~/.astack/<project_name>/lessons/<lesson_name>/LESSON.md` or `LANES.md` entry already warned about this trap. Trace the real cause:
   - skipped or unloaded skill (`astack-tools skills list` / `skills get`) or skipped **lookup**;
   - dropped role (lead solo-coding, solo-debugging, or drifting out of Go mode);
   - ignored directive (`LANES.md`, `RULES.md`, or repo docs via **rtfm**);
   - stale or drifted subagent that never received the directive;
   - missing mechanical check, hook, test, or brief constraint.
3. **Repair the miss and live session state now:**
   - load any skipped skill in full before acting;
   - fix the immediate mistake (delegating code edits to a fresh worker if you are Lead) and run any skipped **review**;
   - pin the rule verbatim in `RULES.md` and `LANES.md`, and steer or replace any drifted subagent (**lead**).
4. **Prevent repeat #3 (**lookback** + **make-it-stick**):** run **lookback** on the failure trail to write or update `~/.astack/<project_name>/lessons/<lesson_name>/LESSON.md`. Then climb **make-it-stick**'s fix ladder (architecture -> types -> lint/hook -> test -> docs last), proposing source-repo rule edits with evidence only when stronger rungs cannot catch it.
5. **Report in 3 bullets:** what slipped and why, what you just fixed (with proof), and the guard preventing a repeat.

Referenced skills: `wat` (`../wat/SKILL.md`), `lookup` (`../lookup/SKILL.md`), `rtfm` (`../rtfm/SKILL.md`), `review` (`../astack-review/SKILL.md`), `lead` (`../astack-lead/SKILL.md`), `lookback` (`../lookback/SKILL.md`), `make-it-stick` (`../make-it-stick/SKILL.md`). Read any cited skill file before acting when its trigger applies.
