---
name: risk-modeling
description: "Gather repo fault evidence, build finders and features, and read scored [0, 1) vector risk envelopes. Use before vectored reviews or when sizing review budgets."
disable-model-invocation: true
---

# Risk modeling

Size review vectors in `[0, 1)` from real repository history. Agents gather evidence, inspect diffs in the repo's language, and build repo-native features outside `repo/` (`ASTACK_HOME`). All scoring math lives once inside `astack-review-ledger score`.

## 1. Cut vectors as faces over atoms

Cut vectors freely along real failure faces (concurrency, persistence, auth, query logic, resource budgets, seams). Each vector maps to a set of **atoms** in the change.

- **Default atom:** one `(commit, file)` touched in the diff. Use finer atoms (symbol, seam, endpoint) when repository tools provide them.
- **Fault-kind faces:** restrict by fault kind only when history carries kind tags. Otherwise assign the scope's full mass and set `kind_scope_upper_bound: true`.

## 2. Start from the additive git baseline (authorizes shares)

Run `astack-review-ledger score --repo <repo> --base <base> --head <head> --json` on any git repository.

- **Codebase-agnostic baseline:** trains strictly on pre-`base` history using an additive Bayesian logistic model. It tracks `lines_changed`, `files_in_commit`, `is_new_file`, `is_fix_commit`, `recent_touches`, `file_prior_faults`, `dir_prior_faults`, and `prior_touches`, plus blame-traced fixes.
- **No feature starvation:** additive log-odds weights let every informative feature contribute without Cartesian cell explosion. Read `feature_effects` and `feature_contributions` to see what drove each score.
- **Epistemic gap mass:** every candidate atom carries exact `epistemic_var` and `gap_mass`. Check `gap_atoms` to spotlight unfamiliar or high-uncertainty edits.
- **Unverified absolute level:** baseline runs authorize relative **shares** only and stay `level_status: "unverified"`.

## 3. Add repo-native meaning features and finders (agent-led)

Commit size cannot see when a small edit changed a contract. Investigate the repo's real failure signals (**rtfm**, **analyze-environment**): diffs, PR labels, issues, CI failures, traces, alerts, and logs.

- **Meaning-change features:** inspect diffs in the repo's own language for changed public signatures, error variants, ordering or lock edits, test-assertion changes, or review-fix rework. Pass them per-atom (`"sha:file": {...}`) or per-file via `extra_features`, or set vector `gap_mass`.
- **Repo-native finder:** write a small script under `ASTACK_HOME` (`astack-tools automations path`) emitting `(introducing_commit, fix_commit)` pairs. Pass it via `--pairs <pairs.json>`.
- **Inspect diagnostics:** read raw `finder_checks` numbers directly instead of inventing binary cutoffs.

## 4. Feed `astack-review-ledger` and close the loop

Pass scored vectors (with `gap_mass`), `catch_table`, and `--outcomes ~/.astack/<project>/reviews/scorer_outcomes.jsonl` into `astack-review-ledger`.

- **Dynamic learned gap share:** the ledger blends `hist`, `gap`, and `unif` experts via detection-debiased switching Bayes (`scorer_calibration`). On a new repo or when bugs hit low-score areas (`miscalibrated_on_gaps: true`), the gap share grows automatically. When real bugs match the historical scorer, the gap share shrinks automatically.
- **Greedy risk-scaled Wave 1 & recharge:** Wave 1 scales greedily with risk concentration (never capped at two). Completed clean vectors return their slots (`returned_slots`). Verified blockers (`D > 0`) expand Wave 2 in parallel from capture-recapture and recharge budget automatically (bounded by optional `max_budget_minutes`).
- **Per-reviewer gap briefs and failover:** the ledger assigns `brief_mode` per model and rotates `gap_brief` across non-worker models. Multi-reviewer gap vectors assign one `gap_brief` infielder while other models run standard sweeps. One-reviewer gap vectors use `standard_with_gap_focus` so normal coverage never drops. Pass `--receipts <review_dir>` and log blocked or failed runs in `failed_reviews` (plus `unreachable_models` when global) so lost slots transfer automatically.
- **Record real outcomes:** after blockers settle, append `outcome_record` as one JSON line to `~/.astack/<project>/reviews/scorer_outcomes.jsonl`.
- **Sharp exchangeable brackets:** for `prior` and `anchored` catch tables, off-anchor `residual_risk` is `null` and `residual_risk_bracket` reports exact bounds. If anchored reading miss sits near `0.80`, invest in native property tests, concurrency harnesses, fuzzers, or TLC models (`astack-statechart`).

**Done when:** baseline or repo-native scoring ran, meaning-change signals informed `extra_features` or gap briefs, `astack-review-ledger` allocated reviewers with `--outcomes`, and verified outcomes updated `scorer_outcomes.jsonl`.

Referenced skills: `rtfm` (`${CLAUDE_SKILL_DIR}/../rtfm/SKILL.md`), `analyze-environment` (`${CLAUDE_SKILL_DIR}/../analyze-environment/SKILL.md`). Read any cited skill file before acting when its trigger applies.
