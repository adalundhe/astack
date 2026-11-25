# Eval Ablation Results

Measured live `with` vs. `without` plugin ablation runs produced by `scripts/eval.py --ablation with-without`.

> **Single-trial note:** Runs recorded with `--runs 1` execute one trial per arm (useful as a directional smoke check, not a variance-controlled statistical estimate; rerun with `--runs 3+` for confidence intervals).

## 2026-11-25 — `bugbash-investigates-and-proves-fix` (`codex`, `--runs 1`)

- **Version / tree:** `v0.10.2` working tree (post-clarity overhaul, no `Stop` hook, prompt-matched non-anchoring lesson recall)
- **Harness:** `codex`
- **Command:**
  ```bash
  python3 -u -B scripts/eval.py \
    --harness codex \
    --case bugbash-investigates-and-proves-fix \
    --ablation with-without \
    --reviewer-pool '[{"provider":"openai","model":"gpt-5.4","effort":"medium","harness":"codex"},{"provider":"openai","model":"gpt-5.4-mini","effort":"medium","harness":"codex"}]' \
    --worker-model '{"provider":"openai","model":"gpt-5.4-mini","effort":"medium","harness":"codex"}' \
    --timeout 600 --json
  ```

### Summary

| Arm | Trials (`--runs`) | Score | Graders passed | Duration | Events |
|---|---:|---:|---:|---:|---:|
| `with` (astack plugin) | 1 | **0.88** | 7 / 8 | 637.6s | 195 |
| `without` (no plugin) | 1 | **0.50** | 4 / 8 | 729.3s | 54 |
| **Delta (`with - without`)** | — | **+0.38** | **+3** | −91.6s | +141 |

### Per-grader breakdown

| Grader | Type | `with` | `without` | Detail (`with` vs. `without`) |
|---|---|---:|---:|---|
| `harness-run` | runtime | PASS | PASS | exit 0 on both arms |
| `bugbash-read` | tool_used | PASS | FAIL | Read matched `2x` vs. `0x` |
| `reviewers-spawned` | tool_used | PASS | FAIL | Agent matched `4x` vs. `0x` (expected `>=3`) |
| `worker-spawned` | tool_used | PASS | FAIL | Agent matched `1x` vs. `0x` (expected `>=1`) |
| `no-general-purpose` | tool_used | PASS | PASS | `0x` on both arms |
| `no-internal-leak` | regex | PASS | PASS | Zero internal ledger/pool/coverage-map leaks on both arms |
| `workspace-verify` | command | PASS | PASS | Both arms fixed both planted bugs, passed red-first tests, and wrote PR proof |
| `judged` | llm | **FAIL** | **FAIL** | See losses below |

### Losses & caveats

- **`with` arm failed `judged` (LLM grader):** the `codex` judge failed the final reply because it implied both root causes rather than stating explicitly that same-tenant duplicate submissions were still deduplicated. Notice the earlier `v0.10.0` leakage bug (naming configured reviewer models when unavailable) did **not** recur: `with` stayed clean on `no-internal-leak` and avoided naming models.
- **`without` arm passed `workspace-verify`:** Codex fixed the code bugs on its own without astack, but skipped structured multi-reviewer investigation (`0` reviewers, `0` workers) and also failed `judged` (leaving both root causes implicit).
- **`redteam-breaks-and-hardens` not run here:** cancelled early to avoid multi-wave audit-fix-rereview token burn; kept opt-in via manual `workflow_dispatch` in `.github/workflows/evals.yml`.
