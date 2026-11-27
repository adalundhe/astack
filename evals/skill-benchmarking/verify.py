#!/usr/bin/env python3
"""Executable verifier for `skill-benchmarking`."""
from __future__ import annotations

import json
import os
import shutil
import statistics
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _eval_kit


def _extract_number(data: dict[str, Any], *keys: str) -> float | None:
    for key in keys:
        val = data.get(key)
        if isinstance(val, (int, float)) and not isinstance(val, bool):
            return float(val)
    stats = data.get("stats") or data.get("metrics") or {}
    if isinstance(stats, dict):
        for key in keys:
            val = stats.get(key)
            if isinstance(val, (int, float)) and not isinstance(val, bool):
                return float(val)
    return None


def _validate_results_payload(data: Any) -> tuple[bool, str, int]:
    if not isinstance(data, dict):
        return False, "results JSON is not an object", 0

    dataset_size = data.get("dataset_size")
    if not isinstance(dataset_size, int) or isinstance(dataset_size, bool) or dataset_size < 100:
        return False, f"invalid dataset_size: {dataset_size!r} (expected int >= 100)", 0

    warmup = data.get("warmup_runs", data.get("warmup"))
    if not isinstance(warmup, int) or isinstance(warmup, bool) or warmup < 1:
        return False, f"invalid warmup_runs: {warmup!r} (expected int >= 1)", dataset_size

    trials_raw = data.get("trials_ms", data.get("samples_ms"))
    trial_count = data.get("trials", data.get("num_trials"))
    if isinstance(trials_raw, list):
        valid_samples = [
            float(x) for x in trials_raw
            if isinstance(x, (int, float)) and not isinstance(x, bool) and float(x) > 0
        ]
        if len(valid_samples) < 5 or len(valid_samples) != len(trials_raw):
            return False, f"trials_ms must have >= 5 positive numbers, got {len(valid_samples)}", dataset_size
        if isinstance(trial_count, int) and trial_count != len(valid_samples):
            return False, f"trials ({trial_count}) != len(trials_ms) ({len(valid_samples)})", dataset_size
        eff_trials = len(valid_samples)
    elif isinstance(trial_count, int) and not isinstance(trial_count, bool) and trial_count >= 5:
        valid_samples = []
        eff_trials = trial_count
    else:
        return False, f"expected >= 5 trials, got trials={trial_count!r}, trials_ms={type(trials_raw).__name__}", dataset_size

    median_ms = _extract_number(data, "median_ms", "p50_ms")
    p95_ms = _extract_number(data, "p95_ms")
    mean_ms = _extract_number(data, "mean_ms")
    if median_ms is None or p95_ms is None or mean_ms is None:
        return False, f"missing required stats: median_ms={median_ms}, p95_ms={p95_ms}, mean_ms={mean_ms}", dataset_size
    if not (median_ms > 0 and p95_ms > 0 and mean_ms > 0):
        return False, f"non-positive timings: median={median_ms}, p95={p95_ms}, mean={mean_ms}", dataset_size
    if p95_ms + 1e-6 < median_ms:
        return False, f"p95_ms ({p95_ms}) < median_ms ({median_ms})", dataset_size

    if valid_samples:
        expected_mean = statistics.fmean(valid_samples)
        expected_median = statistics.median(valid_samples)
        if abs(mean_ms - expected_mean) > max(0.05, expected_mean * 0.05):
            return False, f"mean_ms ({mean_ms}) disagrees with trials_ms mean ({expected_mean:.4f})", dataset_size
        if abs(median_ms - expected_median) > max(0.05, expected_median * 0.05):
            return False, f"median_ms ({median_ms}) disagrees with trials_ms median ({expected_median:.4f})", dataset_size

    plat = data.get("platform") or data.get("environment")
    if not isinstance(plat, dict) or len(plat) < 2:
        return False, f"missing platform metadata dict (got {plat!r})", dataset_size

    return True, (
        f"dataset_size={dataset_size}, warmup={warmup}, trials={eff_trials}, "
        f"median={median_ms:.3f}ms, p95={p95_ms:.3f}ms, mean={mean_ms:.3f}ms"
    ), dataset_size


def _run_instrumented_bench(ws: Path, expected_dataset_size: int) -> tuple[bool, str]:
    """Run program/bench.py in a scratch copy with aggregate_transactions instrumented to prove real work."""
    with tempfile.TemporaryDirectory(prefix="astack-bench-verify-") as td:
        scratch = Path(td) / "ws"
        shutil.copytree(ws / "repo", scratch / "repo")
        shutil.copytree(ws / "program", scratch / "program")
        res_file = scratch / "program" / "bench_results.json"
        if res_file.exists():
            res_file.unlink()

        call_log = Path(td) / "calls.log"
        agg_path = scratch / "repo" / "src" / "aggregate.py"
        orig_src = agg_path.read_text(encoding="utf-8")
        wrapper = (
            "\n\n# --- verifier instrumentation ---\n"
            "import os as _v_os\n"
            "import time as _v_time\n"
            "_orig_aggregate_transactions = aggregate_transactions\n"
            "def aggregate_transactions(records):\n"
            "    log_path = _v_os.environ.get('ASTACK_BENCH_CALL_LOG')\n"
            "    if log_path:\n"
            "        with open(log_path, 'a', encoding='utf-8') as fh:\n"
            "            fh.write(f'{len(records)}\\n')\n"
            "    delay_ms = float(_v_os.environ.get('ASTACK_BENCH_DELAY_MS', '0'))\n"
            "    if delay_ms > 0:\n"
            "        _v_time.sleep(delay_ms / 1000.0)\n"
            "    return _orig_aggregate_transactions(records)\n"
        )
        agg_path.write_text(orig_src + wrapper, encoding="utf-8")

        env_base = {
            **os.environ,
            "PYTHONDONTWRITEBYTECODE": "1",
            "ASTACK_BENCH_CALL_LOG": str(call_log),
            "ASTACK_BENCH_DELAY_MS": "0",
        }
        proc = subprocess.run(
            [sys.executable, "-B", str(scratch / "program" / "bench.py")],
            cwd=scratch,
            env=env_base,
            capture_output=True,
            text=True,
            timeout=25,
        )
        if proc.returncode != 0:
            err = (proc.stderr.strip() or proc.stdout.strip())[:240]
            return False, f"bench.py failed offline (exit {proc.returncode}): {err}"

        if not res_file.is_file():
            return False, "running bench.py did not produce program/bench_results.json"

        try:
            fresh_data = json.loads(res_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            return False, f"regenerated bench_results.json invalid JSON: {exc}"

        ok_fresh, fresh_detail, fresh_size = _validate_results_payload(fresh_data)
        if not ok_fresh:
            return False, f"regenerated bench_results.json invalid: {fresh_detail}"

        if not call_log.is_file():
            return False, "bench.py never invoked repo/src/aggregate.py:aggregate_transactions"
        logged_sizes = [int(x) for x in call_log.read_text(encoding="utf-8").splitlines() if x.strip()]
        if len(logged_sizes) < 6:
            return False, f"expected >= 6 calls (warmup + >=5 trials), observed {len(logged_sizes)}"
        if fresh_size not in logged_sizes and expected_dataset_size not in logged_sizes:
            return False, f"reported dataset_size ({fresh_size}) never matched invoked record counts ({set(logged_sizes)})"

        # Inject a small known delay (3ms) to verify the harness measures real execution time rather than fake numbers.
        base_median = _extract_number(fresh_data, "median_ms", "p50_ms") or 0.0
        call_log.unlink()
        env_slow = {**env_base, "ASTACK_BENCH_DELAY_MS": "3.0"}
        slow_proc = subprocess.run(
            [sys.executable, "-B", str(scratch / "program" / "bench.py")],
            cwd=scratch,
            env=env_slow,
            capture_output=True,
            text=True,
            timeout=25,
        )
        if slow_proc.returncode != 0:
            return False, f"bench.py failed under delay check (exit {slow_proc.returncode})"
        slow_data = json.loads(res_file.read_text(encoding="utf-8"))
        slow_median = _extract_number(slow_data, "median_ms", "p50_ms") or 0.0
        if slow_median < base_median + 1.5 and slow_median < 2.5:
            return False, (
                f"bench.py did not reflect 3ms injected delay "
                f"(base_median={base_median:.3f}ms, delayed_median={slow_median:.3f}ms)"
            )

        return True, (
            f"invoked aggregate_transactions {len(logged_sizes)}x with size={logged_sizes[0]}; "
            f"delay sensitivity verified ({base_median:.2f}ms -> {slow_median:.2f}ms)"
        )


def main() -> int:
    ws = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd().resolve()
    repo = ws / "repo"
    bench_py = ws / "program" / "bench.py"
    results_json = ws / "program" / "bench_results.json"
    final_text = _eval_kit.final_text_from_env()
    checks: list[tuple[str, bool, str]] = []

    if not repo.is_dir():
        checks.append(("workspace-intact", False, "missing ./repo"))
        return _eval_kit.report_and_exit(checks)

    clean_ok, clean_detail = _eval_kit.check_git_clean(repo)
    checks.append(("repo-clean", clean_ok, clean_detail))

    ut_ok, ut_detail = _eval_kit.run_unittest(repo)
    checks.append(("repo-unittest", ut_ok, ut_detail))

    checks.append(("bench-script-exists", bench_py.is_file(), str(bench_py.name)))
    checks.append(("results-json-exists", results_json.is_file(), str(results_json.name)))

    dataset_size = 0
    raw_results_text = ""
    if results_json.is_file():
        raw_results_text = results_json.read_text(encoding="utf-8", errors="replace")
        try:
            payload = json.loads(raw_results_text)
        except json.JSONDecodeError as exc:
            checks.append(("results-schema-valid", False, f"invalid JSON: {exc}"))
        else:
            ok_schema, schema_detail, dataset_size = _validate_results_payload(payload)
            checks.append(("results-schema-valid", ok_schema, schema_detail))
    else:
        checks.append(("results-schema-valid", False, "missing program/bench_results.json"))

    if bench_py.is_file() and dataset_size >= 100:
        run_ok, run_detail = _run_instrumented_bench(ws, dataset_size)
        checks.append(("bench-runs-real-work", run_ok, run_detail))
    else:
        checks.append(("bench-runs-real-work", False, "skipped because bench.py or valid results missing"))

    texts = [final_text, raw_results_text]
    if bench_py.is_file():
        texts.append(bench_py.read_text(encoding="utf-8", errors="replace"))
    sec_hits = _eval_kit.check_no_secrets(texts)
    checks.append(("no-secrets", not sec_hits, "none" if not sec_hits else "; ".join(sec_hits)))

    leak_hits = _eval_kit.check_no_internal_leaks(texts)
    checks.append(("no-internal-leaks", not leak_hits, "none" if not leak_hits else "; ".join(leak_hits)))

    return _eval_kit.report_and_exit(checks)


if __name__ == "__main__":
    sys.exit(main())
