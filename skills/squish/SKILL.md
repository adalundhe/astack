---
name: squish
description: "Examine commits and generated PRs at the end of a DAG, component tree, redteam loop, or sprint ticket to decide whether to rebase, squash, or combine them into cleaner commits/PRs without losing behavior, authorship, or deploy-ordering safety. Use before final PR handoff or merge."
disable-model-invocation: true
---

# Squish

Lead-only post-workflow consolidation pass. Inspect the commits and PRs produced by **dagify**, **treeify**, **redteam**, **sprint**, or **lead**, decide whether consolidating eliminates noisy or fragmented history, and execute safely when justified.

## 1. Audit commits, PRs, and boundaries before touching history

1. **Inspect what landed:** check branch history (`git log --oneline --stat <base>..<head>`) and open workflow PRs (`astack-watch-pr <pr> --once --stack --format json`). Read `~/.config/astack/settings.json` `autonomy` (`feature_branch_rebase_force_with_lease`, `open_and_update_pr`, and denied actions like `push_protected_branch`, `close_or_delete_others_pr`, `merge_pr`).
2. **Squish when:**
   - lanes or review rounds produced noisy fixups, revert/reapply churn, or tiny mechanical commits that read cleaner as coherent logical commits;
   - a single-repo DAG or **treeify** run generated fragmented, tightly coupled PRs for one feature that reviewers would prefer together.
3. **Keep separate (do not combine) when:**
   - **Staged deploy gates (**safe-to-deploy**, **cross-repo**):** expand and contract phases or cross-repo release steps must roll out separately.
   - **Unrelated fixes (**leave-it-better**):** preexisting CI or infra fixes belong in their own PR.
   - **Distinct ownership or external review:** separate CODEOWNERS domains, external review threads that would be lost, or PRs owned by other people (`close_or_delete_others_pr` is denied).
   - **Bisectable perf steps (**clamber**):** preserve distinct measured optimization commits; squash only inner fixup churn.
   - **Protected or merged branches:** never rewrite `main`, release branches, or shared branches (`push_protected_branch` is denied).
4. If history and PRs are already clean, do nothing, log `decided: squish -> no consolidation needed` in `LANES.md`, and stop.

## 2. Consolidate safely in an isolated workspace

Work in an isolated **slates** volume or dedicated git worktree (per **lead**)—never on a dirty or shared branch:

1. **Record the baseline:** save `<old_base>..<old_head>` and verified tree SHAs for every branch/PR before rewriting, so nothing can vanish silently.
2. **Rebase, squash, or combine cleanly:** rebase onto target and group into logical commits preserving test/benchmark commands and numbers. Keep original authorship (`--author`) or `Co-authored-by` trailers for every contributor, and verify mechanically:
   ```bash
   astack-watch-pr authorship-check --before <old_base>..<old_head> --after <new_base>..HEAD --json
   ```
3. **Prove zero dropped behavior and zero gamed gates:**
   - Pure rebases: run `astack-watch-pr patch-id-check --before <old_base>..<old_head> --after <new_base>..HEAD --json`.
   - Squashes or combined PRs: confirm `git diff <pre_squish_tip>..HEAD` is empty for pure history rewrites, and run `astack-check-gates <new_base>..HEAD` plus tests.
   - If conflict resolution or branch merging altered **any** file content relative to the verified pre-squish tree, run vectored **review** (`astack-review-ledger`) on the delta before pushing.
4. **Push and unify PRs:** push feature branches only with `git push --force-with-lease`. Update or open the combined PR with unified scope, Mermaid diagrams (**show-the-states**), updated docs (**technical-writing**), and runnable **prove-it** evidence. For superseded PRs **created by this workflow only**, post a pointer (audited via **leave-feedback** if human-facing), close them, and remove stale remote branches. Hand the unified PR to **watch-pr**.

## 3. Log and hand off

Log the consolidation (old SHAs/PRs -> new SHAs/PRs and verification results) as `decided:` in `LANES.md`, remove scratch workspaces (**cleanup**), and report the clean commit/PR structure plainly (**wat**).
