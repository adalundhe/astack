---
name: wat
description: "Rewrite the last message to lead with impact and cut jargon, internal state, and fluff while keeping facts. Use when someone says /astack:wat."
disable-model-invocation: true
---

# Wat

Rewrite your last message so it is short, direct, and clear on first read, because buried risks and jargon waste time.

1. **Lead with what matters.** State user impact, the decision needed and its basis, or the key finding first. Put losses, contradictions, and risks at the top.
2. **Cut jargon, internal state, and meta-references:**
   - Drop task IDs, internal filenames, bare commit hashes, process narration, and comments about the conversation. Name things by what they do.
   - Never surface internal harness state as `"Open Items"` or review items. Keep single-model reviewer pool, model rosters, `settings.json` defaults, ledger status, and worktree paths internal.
3. **State contradictions plainly with both sides and the action.** Never drop a cryptic fragment like `"69a34f1 says tools-useast1-prod was bootstrapped"`. Say: `"The README says tools-useast1-prod is not bootstrapped, but commit 69a34f1 says it was. Update README.md or verify the cluster state."` Never hide a defect inside a hedged question.
4. **Define or drop specialized terms.** Explain any necessary term inline in a few words on first use.
5. **Write plainly.** Use short sentences, everyday words, and one point per sentence.
6. **Keep every fact intact.** Preserve all numbers, decisions, and whether each claim was measured, inferred, or guessed.

**Reply:** output only the rewritten message. If another agent's message is unclear, send it back with `/astack:wat`.
