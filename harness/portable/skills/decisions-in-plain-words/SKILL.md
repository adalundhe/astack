---
name: decisions-in-plain-words
description: "Resolve what you can yourself, honor the autonomy grant, and escalate only real choices in plain words. Use before asking the person anything or writing a report."
disable-model-invocation: true
---

# Decisions in plain words

Settle what you can on your own, record every decision, and ask the person only what nothing else can resolve.

Explore, research, prototype (**play-with-me**), and benchmark (**ab-test**) to settle technical questions from prior decisions, the repo, docs, or data. Escalate only what none of those settles—in plain words, with your recommendation.

**Escalate to the person:**

- actions only they can take (interactive login/SSO/MFA, `sudo`, spending money). Finish **analyze-environment**, user-space installs, `TOOLS.md`, and all unblocked work first so only the single human command remains;
- trade-offs of functionality, durability, cost, or schedule;
- mutating or irreversible external actions outside `autonomy.allow`;
- product or taste calls not settled by earlier decisions.

**Handle yourself (always allowed—supervised and unattended):**

- **read-only and dry-run external probes:** `--dry-run`, `plan`/`diff`, `auth status`, read-only `GET`, log/trace/metric reads, and **analyze-environment** checks;
- confirmation of what you are about to do, or re-asking approval already given;
- anything an A/B test or prototype can settle;
- retries, flakes, machine issues, merge mechanics, or asking whether to keep going;
- pure improvements that keep behavior identical—ship them and report the numbers.

## Autonomy grant (`settings.json` `autonomy`, configured in `setup`)

Read `autonomy` (`mode`, `allow`, `deny`) from `~/.config/astack/settings.json`. Per-task instructions may narrow or extend the grant. Anything in `autonomy.deny` always requires explicit per-action approval.

- **`"supervised"`:** run read-only checks, local research, and scoped work freely, but ask before mutating external state, pushing branches, opening PRs, or installing tools.
- **`"unattended"`:** execute every action in `autonomy.allow` (not in `deny`) without asking, log `decided:`, and report what you did.

- **Allowed under `"unattended"` without pausing:**
  - `local_worktrees_and_experiments`: read, research, prototype, benchmark, edit scoped files, run tests/linters, use `slates` volumes or worktrees, and log `decided:` choices.
  - `out_of_dir_work`: manage scratch, cache, program, tool, and sibling checkouts outside the active repo without touching unrelated user data.
  - `user_space_tool_install`: install non-root CLIs and packages into user-owned paths (`~/.local/bin`, `uv` venv, Homebrew—never `sudo` or paid accounts) and catalog them in `TOOLS.md`.
  - `feature_branch_push`: commit and push verified changes to your own feature branch.
  - `feature_branch_rebase_force_with_lease`: rebase your feature branch, verify with `git range-diff` and `astack-watch-pr patch-id-check`, and push with `--force-with-lease`.
  - `open_and_update_pr`: open or update the PR/MR once review clears.
  - `watch_pr_and_fix_ci`: run `astack-watch-pr`, fix CI and review feedback, and re-verify via vectored `review`.
  - `post_audited_pr_replies`: post PR replies after an independent `leave-feedback` audit returns `CLEAR` (`astack-watch-pr reply`).
- **Denied unless explicitly authorized for that specific action:**
  - `merge_pr`: never self-merge, never auto-merge on approval, never enable forge auto-merge on gated PRs, and never merge with unmet holds (`watch-pr`, `cross-repo`).
  - `push_protected_branch`: pushing or force-pushing directly to shared/protected branches (`main`, release branches).
  - `close_or_delete_others_pr`: closing or deleting another person's PR, branch, or uncommitted work.
  - `prod_deploy_or_destructive_migration`: production deploys, destructive migrations, or IAM/credential changes.
  - `spend_money_or_billing_changes`: spending money, paid resources, or billing changes.
  - `publish_external_release`: publishing packages, tags/releases, public posts, or external customer comms.
  - `weaken_verification_gates`: skipping tests, relaxing assertions, muting lints, trading requested functionality, or landing non-saturated risky changes without sign-off.

## Guidelines

- Log every decision (choice, options, evidence) in your report or `LANES.md`.
- Ask one self-contained question as soon as it arises: what is needed, why, what you tried, trade-offs, and your pick. Keep working on unblocked tasks.
- Lead with impact and omit internal IDs or harness state, because internal plumbing buries the decision the person needs to make. **Never list internal astack/harness state** (single-model reviewer pool, `reviewer_pool` size, model rosters, `settings.json` defaults, coverage maps, or worktree paths) as an `"Open Item"` or `"Waiting on you"` item.
- Never re-ask answered questions. Execute direct orders without offering to undo them.
- In reports, lead with the bottom line first, then losses/gaps, then verified work. Mark claims as measured, inferred, or guessed.

Referenced skills: `play-with-me` (`../play-with-me/SKILL.md`), `ab-test` (`../ab-test/SKILL.md`), `analyze-environment` (`../analyze-environment/SKILL.md`). Read any cited skill file before acting when its trigger applies.

<!-- Adapts pstack's poteto-mode skill (MIT, Copyright (c) 2026 Lauren Tan). See NOTICE.md. -->
