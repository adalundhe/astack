# Eval Ablation Results

Measured live `with` vs. `without` plugin ablation runs produced by `scripts/eval.py --ablation with-without`.

> **Reading ablations honestly:** Compare `with` vs. `without` on **outcome graders only** (`workspace-verify`, `judged`). Process graders (`bugbash-read`, `reviewers-spawned`, `worker-spawned`) check whether astack's workflow ran; the `without` arm fails them by construction because no astack plugin is installed there.

## 2026-11-25 — `bugbash-investigates-and-proves-fix` (`codex`, `--runs 1`)

**Headline:** **Same outcome (`0.50` vs. `0.50` on outcome graders)**; astack's process ran (`3/3` process graders vs. `0/3` by construction); **single trial (`--runs 1`)**.

- **Version / tree:** `v0.10.2` working tree (no `Stop` hook, prompt-matched non-anchoring lesson recall)
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

### Outcome vs. process summary

| Metric | `with` (astack) | `without` (plain Codex) | Delta (`with - without`) |
|---|---:|---:|---:|
| **Outcome score** (`workspace-verify`, `judged`) | **0.50** (1 / 2) | **0.50** (1 / 2) | **0.00 (tie)** |
| Process graders (`bugbash-read`, `reviewers-spawned`, `worker-spawned`) | 3 / 3 | 0 / 3 *(impossible without plugin)* | +3 *(compliance only)* |
| Runtime & hygiene (`harness-run`, `no-general-purpose`, `no-internal-leak`) | 3 / 3 | 3 / 3 | 0 |
| Combined grader ratio | 0.88 (7 / 8) | 0.50 (4 / 8) | +0.38 *(driven solely by process graders)* |
| Duration | 637.6s | 729.3s | −91.6s |
| Stream events | 195 | 54 | +141 |
| Token cost | *not captured in this run* | *not captured in this run* | *(token parsing added in `scripts/eval.py`)* |

### Per-grader breakdown

| Kind | Grader | `with` | `without` | Detail (`with` vs. `without`) |
|---|---|---:|---:|---|
| Outcome | `workspace-verify` (`command`) | PASS | PASS | Both arms fixed both planted bugs, passed red-first tests, and wrote PR proof |
| Outcome | `judged` (`llm`) | **FAIL** | **FAIL** | Both replies left root-cause details implicit (`with` omitted explicit confirmation of same-tenant dedup; `without` left both root causes implicit) |
| Hygiene | `harness-run` (`runtime`) | PASS | PASS | Exit `0` on both arms |
| Hygiene | `no-general-purpose` (`tool_used`) | PASS | PASS | `0x` on both arms |
| Hygiene | `no-internal-leak` (`regex`) | PASS | PASS | Zero internal ledger/pool/coverage-map leaks (`with` no longer leaked model names when unavailable) |
| Process | `bugbash-read` (`tool_used`) | PASS | FAIL | Read matched `2x` vs. `0x` |
| Process | `reviewers-spawned` (`tool_used`) | PASS | FAIL | Agent matched `4x` vs. `0x` (expected `>=3`) |
| Process | `worker-spawned` (`tool_used`) | PASS | FAIL | Agent matched `1x` vs. `0x` (expected `>=1`) |

### What a real usefulness benchmark still needs

1. **Outcome-only ablation scoring:** now emitted separately as `outcome_score` vs. `process_score` in `scripts/eval.py`.
2. **Multi-trial runs (`--runs 3+`):** this run used `--runs 1` (single trial per arm, no confidence interval).
3. **Token cost reporting:** `scripts/eval.py` now extracts `usage` token totals from harness JSONL events for future runs.
4. **Harder discriminative tasks:** plain Codex already passed `workspace-verify` on `bugbash-investigates-and-proves-fix`; measuring real usefulness requires harder tasks where the plain baseline fails a meaningful fraction of the time.
5. **`redteam-breaks-and-hardens`:** cancelled early to avoid multi-wave token burn and kept opt-in via manual `workflow_dispatch` in `.github/workflows/evals.yml`.
