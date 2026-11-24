---
name: astack-review
description: "Run adversarial reviewer subagents in separate worktrees against a change or PR, rerun every finding to filter false positives, deduplicate by root cause, and report blockers first. Use before merging or when asked to review a change."
---

# Review

Send reviewer subagents to break the change, and keep only findings confirmed by rerunning their reproductions.

1. **Define scope:** review what the person specified; otherwise review all changes on the current branch since its base (including uncommitted edits).
2. **State the intent** (**run-it-back**): summarize what the change must do for users, based on the request, briefs, acceptance criteria, commits, and PR description.
3. **Dispatch reviewers:** Spawn each reviewer with `spawn_agent`: `agent_type: "astack-reviewer"` (installed to `$CODEX_HOME/agents/` by `$astack-setup` with configured model/provider/effort), `fork_turns: "none"`, a `task_name`, and a brief naming its worktree/diff scope, stated intent, reproduction folder, and astack `skills/` path (`..` from this skill), applying `roles.reviewer` from `~/.config/astack/settings.json` when set (using the host subagent tool on the same provider, or the configured provider's CLI such as `claude`, `codex`, `agy`, `cursor`, `gemini`, `devin` when cross-provider and installed). Launch one reviewer per independent change—or for a single change, one per applicable lens, each seeing the full diff:
   - user-facing paths and acceptance criteria;
   - failure modes, load, and concurrency;
   - coding rules: **data-structures-first**, **no-implicit-states**, **no-hidden-flow-control**, **no-hidden-config**, **minimize-state-stores**, **check-your-boundaries**, **no-shared-writes**, **safe-to-rerun**, **no-bolt-ons**, **yagni**, **comment-cop**, **delight-users**, **no-picked-constants**, **event-driven**, **never-trade-functionality**.

   Give each reviewer its own worktree (with uncommitted edits copied in) and the path to the astack `skills/` directory so it can read **adversarial-review** and every applicable coding rule directly. Run `astack-check-gates <base>..<head>` across the full branch/PR range as a structural tripwire for deleted/renamed tests, skips, lint suppressions, downgraded assertions, loosened tolerances, or CI/lint config edits, and still audit test diffs semantically.
4. **Verify every finding.** Rerun each reproduction. Keep a finding only if the failure reproduces and violates the intent or an applicable rule; drop the rest, tallying each reviewer's dropped count and reasons.
5. **Merge duplicates by root cause,** crediting every reviewer that surfaced it. Keep all distinct verified findings across reviewers.
6. **Rank internally** (**adversarial-review**) and report blockers first, then suggestions, then nits—each leading with user impact, reproduction, and evidence. Follow with what was confirmed, what held, what couldn't be tested, and what was dropped.

Never modify the code under review. Hand findings back to the author (or, in an astack program, the lead turns them into lanes).

Referenced skills: `run-it-back` (`../run-it-back/SKILL.md`), `data-structures-first` (`../data-structures-first/SKILL.md`), `no-implicit-states` (`../no-implicit-states/SKILL.md`), `no-hidden-flow-control` (`../no-hidden-flow-control/SKILL.md`), `no-hidden-config` (`../no-hidden-config/SKILL.md`), `minimize-state-stores` (`../minimize-state-stores/SKILL.md`), `check-your-boundaries` (`../check-your-boundaries/SKILL.md`), `no-shared-writes` (`../no-shared-writes/SKILL.md`), `safe-to-rerun` (`../safe-to-rerun/SKILL.md`), `no-bolt-ons` (`../no-bolt-ons/SKILL.md`), `yagni` (`../yagni/SKILL.md`), `comment-cop` (`../comment-cop/SKILL.md`), `delight-users` (`../delight-users/SKILL.md`), `no-picked-constants` (`../no-picked-constants/SKILL.md`), `event-driven` (`../event-driven/SKILL.md`), `never-trade-functionality` (`../never-trade-functionality/SKILL.md`), `adversarial-review` (`../adversarial-review/SKILL.md`). Read any cited skill file before acting when its trigger applies.

<!-- Adapts pstack's interrogate skill (MIT, Copyright (c) 2026 Lauren Tan). See NOTICE.md. -->
