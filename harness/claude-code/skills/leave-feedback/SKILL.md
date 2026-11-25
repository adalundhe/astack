---
name: leave-feedback
description: "Draft, independently audit via a second reviewer agent, and post clear, concise, actionable human-facing PR comments (e.g. GitHub): verifies surrounding PR/issue/doc context was inspected and blocks cryptic SHAs, awkward/stilted/rambling prose, missing actions, or leaked internal thinking before posting. Use before posting any PR review comment or human review feedback."
disable-model-invocation: true
---

# Leave feedback

Turn raw review findings or drafts into clear, concise, actionable PR comments for humans—and never post them until a second independent agent audits the draft against the PR and surrounding context.

1. **Check all surrounding context first (**rtfm**).** Before drafting or finalizing a comment, inspect:
   - the PR title, description, and diff;
   - **every existing PR comment and inline review thread** (open and resolved, human and bot);
   - **every attached or mentioned issue, linked PR, discussion, ADR, RFC, or design doc**;
   - surrounding callers/code, `README`, docs, `RULES.md` / `AGENTS.md` / `CLAUDE.md` / `CONTRIBUTING.md`, and relevant git history.
   - Verify factual claims locally (**prove-it**). Drop any question or comment already answered by the PR, comments, linked issues, docs, or code.
2. **Draft plain, direct, actionable feedback (**wat**).**
   - **Every review comment must answer five things cleanly** so the author never has to guess what goes wrong, how to trigger it, or how to fix it:
     1. **What the issue is** — stated plainly in everyday words (for contradictions, name **both sides**: e.g. NOT `"69a34f1 says tools-useast1-prod was bootstrapped"`; YES: `"The README says tools-useast1-prod is not bootstrapped, but an earlier commit bootstrapped it in infra/clusters.json."`).
     2. **What the impact is** — what actually breaks, drifts, or misleads users, operators, or callers.
     3. **Who/when/how often it hits (concrete scenario)** — affected users/paths, frequency if relevant, or a short concrete example scenario.
     4. **How to reproduce it** — exact input, command, or file/line citations proving it (so the author can trigger and verify it immediately).
     5. **Recommended fix** — a specific, concrete solution naming what to change and where (never vague hand-waving like *"this feels concerning"* or *"worth considering"*).
   - **State defects and contradictions plainly:** never hide a real bug, spec violation, or contradiction inside a hedged rhetorical question (*"Could we check whether...?"*).
   - **Keep prose natural, tight, and non-repetitive:** short sentences, everyday words, one point per bullet, no awkward or stilted phrasing, no rambling explanations, no repeating the same issue across multiple threads.
   - **Strip all internal thinking and bookkeeping:** zero chain-of-thought narration, self-talk, agent/task/lane IDs, internal filenames (`LANES.md`, `RULES.md`, `coverage-map.md`), bracketed internal rule/skill tags (like `[rule: no-picked-constants]`—explain the problem in plain English instead), P0–P5 labels, reviewer counts, model names, pool-exhaustion labels, or capture–recapture/jackknife jargon.
3. **Require a second-agent pre-post audit (spun up by the lead).**
   - **Never post a PR comment without an independent review of the comment itself.** The lead/orchestrator spawns a fresh dedicated **reviewer** agent (via the host's native reviewer subagent or `astack-dispatch run`, distinct from whoever drafted the comment, time-boxed per `reviewer_minutes` / `wind_down_minutes` / `check_in_minutes` from `settings.json`) with the draft comment(s) plus paths/links to the PR, PR comments, linked issues, diff, surrounding code, docs, and `README`.
   - The auditing agent checks every draft comment against this mandatory gate and returns **`REVISE`** (blocking posting) if ANY item fails:
     - **Context verification:** confirms the poster actually checked the PR, existing PR comments, attached/mentioned issues, linked docs/ADRs, surrounding code, and `README`—rejects any comment that asks an already-answered question, duplicates an existing thread, or ignores linked context.
     - **Complete 5-part structure:** rejects any comment that leaves the reader guessing **what the issue is**, **its impact**, **who/when/how often it happens (or an example scenario)**, **how to reproduce it**, or **the recommended fix**.
     - **No bare internal references:** rejects uncontextualized commit hashes/SHAs, internal filenames, lane/task IDs, or unintroduced symbols that a human reading the PR can't understand at a glance.
     - **Prose quality:** rejects awkward phrasing, stilted phrasing, dense walls of text, repetitive language, and rambling explanations.
     - **Actionability:** rejects any point lacking a concrete, actionable recommendation (what to change, where, or the exact choice needed).
     - **Zero leaky internal thinking:** rejects internal thought narration, review-orchestration status, model rosters, stopping-rule math, or internal severity codes (`P0`–`P5`).
     - **Plain directness:** rejects hedged questions disguising real bugs or contradictions; requires both sides of every contradiction to be spelled out clearly.
   - Revise every flagged line and re-audit until the auditing agent returns **`CLEAR`**.
4. **Post cleanly and return only the finalized comment.** Once the auditing agent returns `CLEAR`, post the exact audited comment(s) (e.g., via `gh pr review` / `gh pr comment`, or write to the requested output path when preparing offline) without tacking on extra unaudited preamble or sign-off chatter. In your reply to the user, return only the finalized comment (plus a one-line posted/saved path confirmation if needed)—never prepend a "what changed from the draft" changelog that quotes back stripped internal terms (`coverage-map.md`, `POOL EXHAUSTED`, `jackknife`, `P0`–`P5`, model rosters) or narrates how many audit rounds or reviewer agents ran.

Referenced skills: `rtfm` (`${CLAUDE_SKILL_DIR}/../rtfm/SKILL.md`), `prove-it` (`${CLAUDE_SKILL_DIR}/../prove-it/SKILL.md`), `wat` (`${CLAUDE_SKILL_DIR}/../wat/SKILL.md`). Read any cited skill file before acting when its trigger applies.
