---
name: leave-feedback
description: "Draft, second-agent audit, and post concise, actionable human-facing PR comments with verified context. Use when drafting or posting any PR review comment or reply."
disable-model-invocation: true
---

# Leave feedback

Turn raw review findings into clear, concise, actionable PR comments for humans. Never post a PR comment until a second independent reviewer audits the draft, because authors miss their own ambiguity and jargon.

## 1. Check all surrounding context first (**rtfm**)

Before drafting, inspect:

- the PR title, description, and diff;
- every existing PR comment and inline thread (open and resolved, human and bot);
- every linked issue, PR, discussion, ADR, RFC, or doc;
- surrounding callers, `README`, docs, contributor guides, and relevant git history.

Verify claims locally (**prove-it**). Drop any point already answered by the PR, comments, linked issues, docs, or code.

## 2. Draft plain, direct, actionable feedback (**wat**)

Every **review finding** must answer **five things** so the author never has to guess:

1. **What the issue is:** state it plainly in everyday words, naming **both sides** of any contradiction:
   - NOT: `"69a34f1 says tools-useast1-prod was bootstrapped"`
   - YES: `"README.md says tools-useast1-prod is not bootstrapped, but infra/clusters.json shows it was."`
2. **What the impact is:** state what breaks, drifts, or misleads users or callers.
3. **Who/when/how often it hits:** name affected paths, frequency, or a concrete scenario.
4. **How to reproduce it:** give exact input, command, or file/line citations.
5. **Recommended fix:** name what to change and where—never vague hedging like *"worth considering"*.

For **answers, fix confirmations, and rebuttals** (`address-feedback`, `worrywart`), state the direct answer, verified fix, or disputed claim, back it with concrete evidence or citations, and state the resulting decision or closure (never invent a code fix when none is needed).

Keep the prose tight and human:

- Never wrap a real bug or contradiction inside a polite rhetorical question.
- Use short sentences, everyday words, one point per bullet, and zero repetition across threads.
- Strip all internal bookkeeping: no self-talk, agent/lane IDs, internal filenames (`LANES.md`, `RULES.md`, `coverage-map.md`), or bracketed rule tags.
- Also omit `P0`–`P5` labels, reviewer counts, model names, pool-exhaustion labels, and statistical jargon.

## 3. Require a second-agent pre-post audit (Lead only)

Reviewers and workers return drafts to the lead for audit; subagents never spawn auditors. The lead spawns a fresh **reviewer** distinct from the drafter under `lead` timers. Pass the draft plus links to the PR, comments, linked issues, diff, code, and docs.

The auditor returns **`REVISE`** (blocking posting) if **any** check fails:

- **Context verified:** rejects already-answered questions, duplicate threads, or ignored linked context.
- **Complete structure by comment kind:** for review findings, reject any missing issue, impact, scenario, repro/citation, or concrete fix; for answers, fix confirmations, or rebuttals, reject any missing direct answer/verdict, concrete evidence/citation, or clear closure.
- **No bare internal references:** rejects uncontextualized SHAs, internal filenames, lane IDs, or unexplained symbols.
- **Prose quality:** rejects awkward, stilted, repetitive, or rambling walls of text.
- **Actionability / closure:** rejects findings without a concrete change or decision, and replies/rebuttals that leave the thread ambiguous.
- **Zero internal leaks:** rejects internal narration, model rosters, stopping math, or `P0`–`P5` codes.
- **Plain directness:** rejects hedged questions hiding real defects; requires both sides of any contradiction.

Revise flagged lines and re-audit until the auditor returns **`CLEAR`**.

## 4. Post cleanly and return only the finalized comment

Once `CLEAR`, post the exact audited body via `astack-watch-pr reply --body-file <file> --audit-receipt <receipt>` (or the PR command outside `watch-pr`). Return only the finalized comment plus a one-line confirmation if needed. Never prepend a changelog quoting stripped terms (`coverage-map.md`, `POOL EXHAUSTED`, `jackknife`, `P0`–`P5`) or narrate audit rounds.

**Done when:** the independent auditor returned `CLEAR`, the exact audited comment was posted, and the reply contains zero internal bookkeeping.

Referenced skills: `rtfm` (`../rtfm/SKILL.md`), `prove-it` (`../prove-it/SKILL.md`), `wat` (`../wat/SKILL.md`). Read any cited skill file before acting when its trigger applies.
