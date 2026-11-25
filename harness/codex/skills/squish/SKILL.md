---
name: squish
description: "Examine commits and generated PRs at the end of a DAG workflow, component tree, redteam loop, or multi-lane program to determine whether they can be cleanly rebased, squashed, or combined into fewer, cohesive commits/PRs without losing behavior, authorship, or deploy-ordering safety—and have the lead execute the consolidation cleanly. Use at the end of a workflow or tree before final PR handoff/merge, or whenever commits/PRs look fragmented or noisy."
---

# Squish

Lead-only post-workflow consolidation pass: examine the commits and generated PRs at the end of a **dagify** DAG, **treeify** component tree, **redteam** loop, **sprint** ticket, or multi-lane **lead** run, decide whether they should be rebased, squashed, or combined to eliminate fragmented or noisy history/PRs, and perform that consolidation safely when justified.

## 1. Audit commits, PRs, and safety boundaries before touching history

1. **Inspect what the workflow produced:**
   - Review commit history and diffs across the completed branch(es) (`git log --oneline --stat <base>..<head>`) and all open workflow PRs/MRs (`astack-watch-pr <pr> --once --stack --format json`).
   - Check `~/.config/astack/settings.json` `autonomy` (`feature_branch_rebase_force_with_lease`, `open_and_update_pr`, and `deny` entries such as `push_protected_branch`, `close_or_delete_others_pr`, `merge_pr`).
2. **Decide what SHOULD be squished vs. kept separate:**
   - **Rebase / squash commits when:** lanes or review rounds produced noisy fixups, intermediate leaf scaffolding, revert/reapply churn, or tiny mechanical steps that read far cleaner as one (or a few) coherent logical commits.
   - **Combine PRs when:** a single-repo DAG or **treeify** wave generated multiple small, fragmented, or tightly coupled PRs representing one cohesive feature/fix that reviewers would rather review and merge together.
   - **Keep separate (DO NOT combine) when:**
     - **Staged deploy gates (**safe-to-deploy**, **cross-repo**):** never merge expand and contract phases, cross-repo release steps, or migrations that must roll out in separate releases into one PR.
     - **Unrelated fixes (**leave-it-better**):** preexisting CI/test/infra fixes stay in their own PR.
     - **Distinct ownership or active external review:** do not combine PRs with separate CODEOWNERS approval domains, external human commits/reviews that would lose inline thread context, or PRs owned by other people (`close_or_delete_others_pr` is denied).
     - **Bisectable optimization steps (**clamber**):** preserve distinct measured optimization commits when per-step bisection matters (squash only fixup churn inside a step).
     - **Protected or already-merged branches:** never rewrite history on `main`, release branches, or any shared/protected branch (`push_protected_branch` is denied).
   - If the commits and PRs are already clean, minimal, and appropriately separated, **do nothing**, log `decided: squish -> no consolidation needed` in `LANES.md` with reason, and stop.

## 2. Perform the rebase, squash, and PR combination safely

Execute consolidation in an isolated **slates** in-memory VFS volume (`https://github.com/hyper-light/slates`, preferred when available) or dedicated **git worktree**—never on a dirty or shared branch:

1. **Record the pre-squish baseline:** capture exact `<old_base>..<old_head>` SHAs (and pre-squish verified tree SHA(s)) for every branch/PR being consolidated so zero behavior or credit can silently vanish.
2. **Rebase, squash, and/or combine branches cleanly:**
   - Rebase onto the latest target branch and squash/group commits into logical, self-contained units with clear commit messages (preserving verification commands and benchmark/test numbers).
   - **Preserve all contributor credit:** keep original commit authorship (`--author`) or include `Co-authored-by: Name <email>` trailers for every combined contributor, and verify mechanically:
     ```bash
     astack-watch-pr authorship-check --before <old_base>..<old_head> --after <new_base>..HEAD --json
     ```
3. **Prove zero dropped behavior, zero resurrected regressions, and zero gamed gates:**
   - For pure rebases (same commit count): run `astack-watch-pr patch-id-check --before <old_base>..<old_head> --after <new_base>..HEAD --json` (`git patch-id` + `git range-diff`).
   - For squashes or combined PR branches: verify the consolidated tree strictly against the pre-squish verified tip (`git diff <pre_squish_tip>..HEAD`—must be empty for pure history consolidation) **and** run `astack-check-gates <new_base>..HEAD` plus the test suite on the squished branch.
   - **Re-review any non-empty delta:** if rebasing onto moved target or combining branches required conflict resolution or altered **any** file content relative to the verified pre-squish tree, run vectored **review** (`astack-review-ledger`) on the changed delta before pushing.
4. **Push feature branches and consolidate PRs cleanly:**
   - Push only the consolidated feature branch(es) with `git push --force-with-lease` (never bare `--force`, never to a protected branch).
   - Update or open the unified PR with a single clear description covering all combined deliverables, Mermaid state/architecture diagrams (**show-the-states**), updated repo docs (**technical-writing**), and runnable **prove-it** evidence.
   - For superseded PRs **created by this workflow only** (never another person's PR), post a concise pointer to the combined PR (audited via **leave-feedback** if human-facing), close the superseded PRs, and delete stale superseded remote feature branches when safe.
   - Hand the consolidated PR to **watch-pr** (`astack-watch-pr`)—respecting `autonomy` (`merge_pr` policy; never self-merge unless explicitly permitted).

## 3. Log and hand off

Record the consolidation (old SHAs/PRs -> new squished SHAs/PRs, tree-equivalence / `authorship-check` / `astack-check-gates` verification, or why kept separate) as a `decided:` entry in `LANES.md`, clean up ephemeral consolidation workspaces (**cleanup**), and report the resulting clean commit/PR structure plainly (**wat**).

Referenced skills: `dagify` (`../dagify/SKILL.md`), `treeify` (`../treeify/SKILL.md`), `redteam` (`../redteam/SKILL.md`), `sprint` (`../sprint/SKILL.md`), `lead` (`../astack-lead/SKILL.md`), `safe-to-deploy` (`../safe-to-deploy/SKILL.md`), `cross-repo` (`../cross-repo/SKILL.md`), `leave-it-better` (`../leave-it-better/SKILL.md`), `clamber` (`../clamber/SKILL.md`), `slates` (`../slates/SKILL.md`), `review` (`../astack-review/SKILL.md`), `show-the-states` (`../show-the-states/SKILL.md`), `technical-writing` (`../technical-writing/SKILL.md`), `prove-it` (`../prove-it/SKILL.md`), `leave-feedback` (`../leave-feedback/SKILL.md`), `watch-pr` (`../watch-pr/SKILL.md`), `cleanup` (`../cleanup/SKILL.md`), `wat` (`../wat/SKILL.md`). Read any cited skill file before acting when its trigger applies.
