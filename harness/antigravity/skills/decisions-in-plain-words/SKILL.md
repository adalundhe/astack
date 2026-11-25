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

## Autonomy grant (`settings.json` `autonomy`, configured in **setup**)

Read `autonomy` (`mode`: `"supervised"` default vs `"unattended"`, plus explicit `allow` and `deny` lists) from `~/.config/astack/settings.json` (or `$XDG_CONFIG_HOME/astack/settings.json`). Explicit per-task instructions from the person may narrow or extend the grant for that run; anything in `autonomy.deny` always requires explicit per-action approval.

- **What an `"unattended"` ("go ahead unattended") grant permits without pausing:**
  - `local_worktrees_and_experiments`: read, research, prototype, benchmark, edit scoped files, run builds/tests/linters, create worktrees and feature branches, and settle technical decisions with evidence (`decided:`).
  - `feature_branch_push`: commit and push verified changes to your own feature/PR branch.
  - `feature_branch_rebase_force_with_lease`: fetch target, rebase your feature branch, verify with `git range-diff` + `astack-watch-pr patch-id-check`, and push with `--force-with-lease` on the feature branch only.
  - `open_and_update_pr`: open or update the PR/MR once review clears.
  - `watch_pr_and_fix_ci`: run `astack-watch-pr`, dispatch remediation workers for CI failures and review feedback, and re-verify via vectored **review**.
  - `post_audited_pr_replies`: post PR replies only after an independent second-agent **leave-feedback** audit returns `CLEAR` (enforced by `astack-watch-pr reply`).
- **What an unattended grant NEVER permits unless explicitly authorized for that specific action:**
  - `merge_pr`: merging a PR/MR into the target branch.
  - `push_protected_branch`: pushing directly or force-pushing to shared/protected branches (`main`, `master`, release branches).
  - `close_or_delete_others_pr`: closing/deleting another person's PR or branch, or discarding uncommitted changes you did not create.
  - `prod_deploy_or_destructive_migration`: production deploys, destructive schema/data migrations, or IAM/credential changes.
  - `spend_money_or_billing_changes`: spending money, provisioning paid resources, or changing billing/subscriptions.
  - `publish_external_release`: publishing packages, tags/releases, public posts, emails, or external customer comms.
  - `weaken_verification_gates`: skipping tests, relaxing assertions, muting linters, lowering review/security bars, trading away requested functionality/durability, or landing non-saturated risky changes without sign-off.

Guidelines:
- Log every decision where the person can see it (in your report or the lane log): what you chose, the options considered, and what settled it.
- Ask one self-contained question as soon as it arises: what's needed and why, what you already tried, trade-offs, and your recommendation. Keep working on unblocked tasks.
- Lead with impact; keep internal IDs and task numbers out of the message.
- Don't re-ask answered questions. When given a direct order, execute it without offering to undo it.
- In reports, answer their question first, then losses/gaps, then completed work with evidence. Mark each claim as measured, inferred, or guessed.

Referenced skills: `play-with-me` (`../play-with-me/SKILL.md`), `ab-test` (`../ab-test/SKILL.md`), `setup` (`../astack-setup/SKILL.md`), `review` (`../astack-review/SKILL.md`), `leave-feedback` (`../leave-feedback/SKILL.md`). Read any cited skill file before acting when its trigger applies.

<!-- Adapts pstack's poteto-mode skill (MIT, Copyright (c) 2026 Lauren Tan). See NOTICE.md. -->
