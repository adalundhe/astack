---
name: rtfm
description: "Check the prompt, saved ~/.astack memories, PR/issue threads, repo docs/code/history, local environment, and official tool docs before asking questions or claiming to be blocked. Use before asking the person anything."
disable-model-invocation: true
---

# RTFM

Read what is already available before asking the person anything, because drive-by questions waste human time on settled facts.

Before asking a question, declaring yourself blocked, or calling a requirement unclear, check in order:

1. **Prompt, brief, and saved memories (**lookup**):** read the thread, brief, `RULES.md`, `astack-decisions`, and saved `~/.astack/<project_name>/lessons/<lesson_name>/LESSON.md` memories (including related repos on cross-repo work).
2. **PR, issue, and linked context:** read the PR description, every PR comment and inline thread, commit messages, and every linked issue, PR, discussion, ADR, or spec (`gh pr view --comments`, `gh issue view --comments`, `git log`, `git blame`). Follow links instead of guessing. If critical history sits uncaptured in raw chats, tickets, or deploy logs, run **lookback** to distill durable `~/.astack` lessons.
3. **The repository:** read READMEs, docs, ADRs, contributor guides (`AGENTS.md`, `CLAUDE.md`, `CONTRIBUTING.md`), relevant source, callers, tests, and git history.
4. **Local environment (**analyze-environment**):** inspect configs, CI workflows, CLIs, MCP servers, env-var names, reachable services, and safe read-only or dry-run probes.
5. **Official docs:** check primary documentation and examples for the tools and libraries involved.

Then test what you read—run the command, inspect the source, or call the API.

Never ask a question already answered above. Escalate only if nothing resolves it, stating what you checked, what conflicts, and the exact decision needed (**decisions-in-plain-words**).

Referenced skills: `lookup` (`${CLAUDE_SKILL_DIR}/../lookup/SKILL.md`), `lookback` (`${CLAUDE_SKILL_DIR}/../lookback/SKILL.md`), `analyze-environment` (`${CLAUDE_SKILL_DIR}/../analyze-environment/SKILL.md`), `decisions-in-plain-words` (`${CLAUDE_SKILL_DIR}/../decisions-in-plain-words/SKILL.md`). Read any cited skill file before acting when its trigger applies.
