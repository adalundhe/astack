---
name: rtfm
description: "Check the user's message, repo docs/code/history, local environment, and official tool docs before asking questions or claiming to be blocked. Use before asking the person anything."
disable-model-invocation: true
---

# RTFM

Read what's already available before asking the person anything.

Before asking a question, declaring yourself blocked, calling a requirement unclear, or claiming you lack context, check in order:

1. **What you were already given & saved memories (**lookup**):** the prompt and thread, your brief, `RULES.md`, earlier decisions in the lane log (`astack-decisions`), and saved per-project `~/.astack/<project_name>/lessons/<lesson_name>/LESSON.md` memories (**lookup**—checking related repos/projects too on cross-repo work) so you start with known patterns, environment quirks, and dead ends already mapped.
2. **PR, issue, discussion, and linked context:** the PR description, **every PR comment and inline review thread** (human and bot, open and resolved), commit messages, **linked issues, parent/child PRs, discussions, ADRs, RFCs, design docs, tickets, and cited URLs** (e.g., `gh pr view --comments`, `gh issue view --comments`, `gh api` for inline review threads, `git log` / `git blame`, and reading every referenced file or spec). Follow links instead of guessing what they say. When critical context only exists across raw past chats, tickets, bugs, or deploy/failure logs that haven't been captured yet, run **lookback** to dig through them and distill durable `~/.astack/<project_name>/lessons/<lesson_name>/LESSON.md` records.
3. **The repository:** README, docs, architecture decisions, contributor/agent guides (`AGENTS.md`, `CLAUDE.md`, `CONTRIBUTING.md`), relevant source, callers/callees, tests, and git history for the area.
4. **The local environment & available tooling (**analyze-environment**):** configs, scripts, CI workflows, installed CLIs, MCP servers, env-var names, running/reachable services, safe read-only/dry-run and auth-status probes, and existing logs or outputs.
5. **Official references:** documentation and examples for the tools and libraries involved.

Then actually test what you read—run the command, inspect the source, call the API.

Never ask a question that the repo, git history, PR/issue comments, linked context, local execution, or official docs already answer. Only ask if nothing above resolves it, and state plainly what you checked, what conflicts or is missing, and why a human decision is required (**decisions-in-plain-words**).
