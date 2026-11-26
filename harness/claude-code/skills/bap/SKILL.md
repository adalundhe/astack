---
name: bap
description: "Stop mid-session when the person repeats a rule, audit why it slipped, repair state, and add a guard. Use immediately when corrected on a repeated rule."
disable-model-invocation: true
---

# Bap

Stop immediately when the person has to repeat themselves. Don't apologize, patch the symptom, and forget two turns later—fix **why** it slipped right now.

1. **Full stop, zero fluff:** skip apologies and defensive explanations, because excuses waste turns without fixing the miss. State the missed rule in one plain sentence.
2. **Audit why it slipped, not just what slipped:** run **lookup** first to check whether a saved `~/.astack/<project_name>/lessons/<lesson_name>/LESSON.md`, review bundle (`~/.astack/<project_name>/reviews/<date_time>/`), or `LANES.md` entry already warned about this trap. Trace the real cause:
   - skipped or unloaded skill (`astack-tools skills list --role <role>` / `skills get <name>`) or skipped **lookup**;
   - dropped role (Lead solo-coding, solo-debugging, or drifting out of Go mode);
   - ignored directive (`LANES.md`, `RULES.md`, or repo docs via `rtfm`);
   - stale or drifted subagent that never received the directive;
   - missing mechanical check, hook, test, or brief constraint.
3. **Repair the miss and live state now (by role):**
   - Load any skipped skill in full before acting.
   - **Lead:** delegate code edits to a fresh worker, run any skipped **review**, update `RULES.md` and `rules rev:` in `LANES.md` via `astack-stamp --add`, and steer or replace drifted subagents.
   - **Non-Lead:** fix only within your writable scope, never spawn subagents, and return a draft lesson plus structural guard to Lead.
4. **Prevent repeat #3 (`lookback`, `make-it-stick`):** Lead runs **lookback** on the failure trail to write or update `~/.astack/<project_name>/lessons/<lesson_name>/LESSON.md`. Then climb **make-it-stick**'s structural fix ladder from strongest rung down, proposing source-repo rule edits only when mechanical guards cannot catch it.

**Reply (3 bullets):**
- what slipped and why;
- what you just fixed (with proof);
- the guard preventing a repeat.

Referenced skills: `lookup` (`${CLAUDE_SKILL_DIR}/../lookup/SKILL.md`), `review` (`${CLAUDE_SKILL_DIR}/../review/SKILL.md`), `lookback` (`${CLAUDE_SKILL_DIR}/../lookback/SKILL.md`), `make-it-stick` (`${CLAUDE_SKILL_DIR}/../make-it-stick/SKILL.md`). Read any cited skill file before acting when its trigger applies.
