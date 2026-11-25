---
name: wat
description: "Rewrite the last message so it leads with the bottom line and cuts jargon, internal state, and meta-commentary while preserving facts and numbers. Use when someone says /wat."
---

# Wat

Rewrite your last message so it's short, direct, and immediately understandable.

1. **Lead with what matters:** user impact, the decision needed and what it rests on, or the key finding. Put losses, contradictions, and risks first.
2. **Cut jargon, internal state, and meta-references:** drop task IDs, internal filenames/identifiers, uncontextualized commit hashes, process narration, comments about the conversation itself, and unintroduced context. Never surface internal harness/astack state (single-model reviewer pool, model rosters, `settings.json` defaults, ledger/coverage-map status, worktree paths) as `"Open Items"` or items for user review. Refer to things by what they do.
3. **State contradictions and issues plainly with both sides and the action:** never drop a cryptic fragment like `"69a34f1 says tools-useast1-prod was bootstrapped"`—say `"The README says tools-useast1-prod is not bootstrapped, but commit 69a34f1 says it was. Update README.md or verify the cluster state so they match."` Never hide a defect or contradiction inside a hedged question.
4. **Define or drop specialized terms** inline in a few words where first used.
5. **Write plainly:** short sentences, everyday words, one point per sentence.
6. **Keep all facts intact:** preserve every number, decision, and whether each claim was measured, inferred, or guessed.

Reply with only the rewritten message. If another agent's message is unclear, send it back with `/wat`.
