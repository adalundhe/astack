---
name: leave-feedback
description: "Draft, independently audit via a second reviewer agent, and post clear, concise, actionable human-facing PR comments. Verifies linked context and blocks cryptic SHAs, stilted prose, missing actions, or leaked internal thinking before posting."
disable-model-invocation: true
---

# Leave feedback

Turn raw review findings into clear, concise, actionable PR comments for humans. Never post a human-facing PR comment until a second independent reviewer audits the draft, because authors miss their own ambiguity and internal jargon.

## 1. Check all surrounding context first (**rtfm**)

Before drafting, inspect:

- the PR title, description, and diff;
- every existing PR comment and inline thread (open and resolved, human and bot);
- every linked issue, PR, discussion, ADR, RFC, or doc;
- surrounding callers, `README`, docs, contributor guides, and relevant git history.

Verify claims locally (**prove-it**). Drop any question or point already answered by the PR, comments, linked issues, docs, or code.

## 2. Draft plain, direct, actionable feedback (**wat**)

Every review comment must answer **five things** so the author never has to guess:

1. **What the issue is:** state it plainly in everyday words. For contradictions, name **both sides** (NOT `"69a34f1 says tools-useast1-prod was bootstrapped"`; YES: `"README.md says tools-useast1-prod is not bootstrapped, but infra/clusters.json shows it was."`).
2. **What the impact is:** state what breaks, drifts, or misleads users or callers.
3. **Who/when/how often it hits:** name affected paths, frequency, or a concrete scenario.
4. **How to reproduce it:** give exact input, command, or file/line citations.
5. **Recommended fix:** name what to change and where—never vague hedging like *"worth considering"*.

Keep the prose tight and human:

- Never wrap a real bug or contradiction inside a polite rhetorical question.
- Use short sentences, everyday words, one point per bullet, and zero repetition across threads.
- Strip all internal bookkeeping: no self-talk, agent/lane IDs, internal filenames (`LANES.md`, `RULES.md`, `coverage-map.md`), bracketed rule tags (`[rule: ...]`), P0–P5 labels, reviewer counts, model names, pool-exhaustion labels, or statistical jargon.

## 3. Require a second-agent pre-post audit

Spawn a fresh dedicated **reviewer** agent (distinct from whoever drafted the comment, under **lead**'s timers) with the draft comment(s) plus paths/links to the PR, comments, linked issues, diff, code, and docs.

The auditor returns **`REVISE`** (blocking posting) if **any** check fails:

- **Context verified:** rejects already-answered questions, duplicate threads, or ignored linked context.
- **Complete 5-part structure:** rejects any comment missing issue, impact, scenario, repro/citation, or concrete fix.
- **No bare internal references:** rejects uncontextualized SHAs, internal filenames, lane IDs, or unexplained symbols.
- **Prose quality:** rejects awkward, stilted, repetitive, or rambling walls of text.
- **Actionability:** rejects comments without a concrete change or decision.
- **Zero internal leaks:** rejects internal narration, model rosters, stopping math, or `P0`–`P5` codes.
- **Plain directness:** rejects hedged questions hiding real defects; requires both sides of any contradiction.

Revise flagged lines and re-audit until the auditor returns **`CLEAR`**.

## 4. Post cleanly and return only the finalized comment

Once `CLEAR`, post the exact audited comment without extra preamble. In your reply to the user, return only the finalized comment (plus a one-line posted/saved confirmation if needed). Never prepend a changelog that quotes stripped internal terms (`coverage-map.md`, `POOL EXHAUSTED`, `jackknife`, `P0`–`P5`) or narrates audit rounds.

Referenced skills: `rtfm` (`${CLAUDE_SKILL_DIR}/../rtfm/SKILL.md`), `prove-it` (`${CLAUDE_SKILL_DIR}/../prove-it/SKILL.md`), `wat` (`${CLAUDE_SKILL_DIR}/../wat/SKILL.md`), `lead` (`${CLAUDE_SKILL_DIR}/../lead/SKILL.md`). Read any cited skill file before acting when its trigger applies.
