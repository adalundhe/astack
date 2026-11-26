---
name: rtfm
description: "Check prompt, ~/.astack lessons, PR/issue threads, repo docs, local tools, and official docs first. Use before asking the person anything or claiming to be blocked."
disable-model-invocation: true
---

# RTFM

Read existing sources before asking the person anything. Drive-by questions waste human time on settled facts.

Before asking a question, declaring a blocker, or calling requirements unclear, check in order:

1. **Prompt, brief, and saved memories:** read the thread, brief, `RULES.md`, `astack-decisions`, and saved `~/.astack` records via **lookup**. Check `lessons/`, `architecture/AD_<N>.md`, `research/`, `docs/`, `reviews/<date_time>/`, `repros/`, `automations/`, and `logging/` via `astack-tools <bucket> list`.
2. **PR, issue, and linked context:** read descriptions, comments, inline threads, commits, and linked ADRs or specs. Run `gh pr view --comments`, `gh issue view --comments`, `git log`, and `git blame`. Follow links instead of guessing. (Lead/Worker: run **lookback** if deep history isn't captured; read-only roles flag the gap to Lead.)
3. **The repository:** read READMEs, docs, repo ADRs, `AGENTS.md`, `CLAUDE.md`, and `CONTRIBUTING.md`. Inspect relevant source, callers, tests, and git history.
4. **Local environment (`analyze-environment`):** inspect configs, CI workflows, CLIs, MCP servers, env-var names, and reachable services. Run safe read-only probes.
5. **Official docs:** check primary documentation and examples for the tools and libraries involved.

Verify what you read by running the command, inspecting source, or calling the API. Never trust docs alone, because docs drift from code.

Never ask a question already answered above. Escalate only when nothing resolves it (**decisions-in-plain-words**). State what you checked, what conflicts, and the exact decision needed.

**Done when:** all five tiers are checked and verified, or an escalation cites the exact conflict.

Referenced skills: `lookup` (`../lookup/SKILL.md`), `lookback` (`../lookback/SKILL.md`), `decisions-in-plain-words` (`../decisions-in-plain-words/SKILL.md`). Read any cited skill file before acting when its trigger applies.
