---
name: squish
description: "Consolidate noisy workflow commits and PRs while keeping behavior, authorship, and deploy safety intact. Use before PR handoff or merge."
disable-model-invocation: true
---

# Squish

Run this Lead-only consolidation pass after `dagify`, `treeify`, `redteam`, `sprint`, or **lead** finishes. Inspect generated commits and PRs. Rebase, squash, or combine them only when it eliminates real noise or fragmentation.

## 1. Audit commits, PRs, and boundaries first

1. **Inspect history and open PRs:** run `git log --oneline --stat <base>..<head>` and `astack-watch-pr <pr> --once --stack --format json`. Check `~/.config/astack/settings.json` `autonomy` (`feature_branch_rebase_force_with_lease`, `open_and_update_pr`, and denied actions like `push_protected_branch`, `close_or_delete_others_pr`, `merge_pr`).
2. **Squish when:**
   - lanes or review rounds left fixup churn, revert/reapply noise, or tiny mechanical commits;
   - a single-repo `dagify` or `treeify` run split one tightly coupled feature across fragmented PRs.
3. **Keep separate (do not combine) when:**
   - **Staged deploy gates (**safe-to-deploy**):** expand/contract migrations or `cross-repo` steps must roll out separately.
   - **Unrelated fixes:** preexisting CI or infra fixes belong in their own PR (`leave-it-better`).
   - **Distinct ownership or review:** separate CODEOWNERS domains, external review threads, or PRs owned by others (`close_or_delete_others_pr` is denied).
   - **Bisectable perf steps:** keep measured `clamber` optimization commits distinct; squash only inner fixup churn.
   - **Protected or merged branches:** never rewrite `main`, release branches, or shared branches (`push_protected_branch` is denied).
4. **Skip if clean:** if history and PRs already read cleanly, do nothing. Log `decided: squish -> no consolidation needed` in `LANES.md` and stop.

## 2. Consolidate safely in an isolated workspace

Work in an isolated **slates** volume or git worktree (per **lead**). Never rewrite history on a dirty or shared checkout.

1. **Record the baseline:** save `<old_base>..<old_head>` and verified tree SHAs for every branch or PR before rewriting, so nothing can vanish silently.
2. **Rebase, squash, or combine cleanly:** group into logical commits and keep test or benchmark numbers. Preserve every contributor's `--author` or `Co-authored-by` trailer, because squashing strips attribution needed for blame, ownership, and credit. Verify mechanically:
   ```bash
   astack-watch-pr authorship-check --before <old_base>..<old_head> --after <new_base>..HEAD --json
   ```
3. **Prove zero dropped behavior and zero gamed gates:**
   - **Same-base squashes or combined PRs:** confirm `git diff <pre_squish_tip>..HEAD` is empty. Run `astack-check-gates <new_base>..HEAD` and the full test suite.
   - **Moved-base rebases:** skip the empty-diff check (upstream changed). Verify instead with `astack-watch-pr patch-id-check --before <old_base>..<old_head> --after <new_base>..HEAD --json` (`git range-diff`), `astack-check-gates <new_base>..HEAD`, and tests.
   - **Content changed during merge/conflict resolution:** run vectored **review** (`astack-review-ledger`) on the delta before pushing.
4. **Push and unify PRs:** push feature branches only with `git push --force-with-lease`. Update or open the unified PR with scope, diagrams, updated docs, and runnable proof. For superseded PRs **created by this workflow only**, post a pointer (audited via **leave-feedback** if human-facing), close them, and delete stale remote branches. Hand the unified PR to **watch-pr**.

## 3. Log and hand off

Log old-to-new SHAs, PR links, and verification results as `decided:` in `LANES.md`. Remove scratch workspaces (**cleanup**).

**Reply:** state old vs. new commit/PR structure, verification checks passed, and whether any PRs were kept separate.
