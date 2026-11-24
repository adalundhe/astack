---
name: decisions-in-plain-words
description: "Resolve what you can yourself, log every decision, and only escalate genuine human choices as plain options with a recommendation. Use before asking the person anything or writing a report."
disable-model-invocation: true
---

# Decisions in plain words

Settle what you can on your own, record every decision, and ask the person only what nothing else can resolve.

Explore, research, prototype (**play-with-me**), and benchmark (**ab-test**) to answer technical questions from earlier decisions, the repo, docs, or data. Escalate only what none of those can settle—directly, in plain words, with your recommendation.

**Escalate to the person:**
- actions only they can take (signing in, installing as root, spending money);
- trade-offs of functionality, durability, cost, or schedule;
- irreversible or external actions they haven't authorized;
- product or taste calls not covered by earlier decisions.

**Handle yourself:**
- asking for confirmation of what you're about to do, or re-asking approval already given;
- anything an A/B test or prototype can answer;
- retries, flakes, machine issues, merge mechanics, or asking whether to continue;
- pure improvements that preserve behavior—ship them and report the numbers.

Guidelines:
- Log every decision where the person can see it (in your report or the lane log): what you chose, the options considered, and what settled it.
- Ask one self-contained question as soon as it arises: what's needed and why, what you already tried, trade-offs, and your recommendation. Keep working on unblocked tasks.
- Lead with impact; keep internal IDs and task numbers out of the message.
- Don't re-ask answered questions. When given a direct order, execute it without offering to undo it.
- In reports, answer their question first, then losses/gaps, then completed work with evidence. Mark each claim as measured, inferred, or guessed.

Referenced skills: `play-with-me` (`${CLAUDE_SKILL_DIR}/../play-with-me/SKILL.md`), `ab-test` (`${CLAUDE_SKILL_DIR}/../ab-test/SKILL.md`). Read any cited skill file before acting when its trigger applies.

<!-- Adapts pstack's poteto-mode skill (MIT, Copyright (c) 2026 Lauren Tan). See NOTICE.md. -->
